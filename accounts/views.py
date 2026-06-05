from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.views import PasswordResetView as DjangoPasswordResetView
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

import threading

from accounts.forms import LoginForm, RegisterForm
from accounts.services.auth_service import AuthService


def register(request: HttpRequest) -> HttpResponse:
    """Render the registration form and create a new inactive user on valid POST.

    On success, stores the pending user id in the session and redirects to OTP
    verification. On duplicate active email or email delivery failure, re-renders
    the form with an error.

    Args:
        request: Incoming HTTP request.

    Returns:
        Rendered form page or redirect to verify.
    """
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            user = AuthService.register(
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
            )
        except ValueError as exc:
            form.add_error('email', str(exc))
        except RuntimeError:
            form.add_error(None, 'Could not send verification code. Please try again.')
        else:
            request.session['pending_user_id'] = user.pk
            request.session['otp_purpose'] = 'register'
            return redirect('accounts:verify')

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request: HttpRequest) -> HttpResponse:
    """Authenticate credentials and initiate OTP second-factor flow.

    Verifies email/password, sends an OTP to the user's email, and stores the
    pending user id in the session for the subsequent verify step.

    Args:
        request: Incoming HTTP request.

    Returns:
        Rendered login page or redirect to verify.
    """
    error: str | None = None
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = AuthService.authenticate(
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
            )
            if user:
                try:
                    AuthService.send_otp(user)
                except RuntimeError:
                    error = 'Could not send verification code. Please try again.'
                else:
                    request.session['pending_user_id'] = user.pk
                    request.session['otp_purpose'] = 'login'
                    return redirect('accounts:verify')
            else:
                error = 'Invalid email or password'
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form, 'error': error})


def verify_otp(request: HttpRequest) -> HttpResponse:
    """Render the OTP entry form and complete login or registration on valid POST.

    Args:
        request: Incoming HTTP request.

    Returns:
        Rendered verify page or redirect to the mirror index after success.
    """
    # 1. Resolve the pending user from session; redirect if session is missing or stale
    user_id = request.session.get('pending_user_id')
    if not user_id:
        return redirect('accounts:login')

    user = AuthService.get_user_by_id(user_id)
    if not user:
        return redirect('accounts:login')

    # 2. Calculate seconds remaining so the template can show a countdown
    seconds_remaining = AuthService.get_seconds_remaining(user)
    error: str | None = None

    if request.method == 'POST':
        # 3. Validate the submitted code against the stored OTP record
        code: str = request.POST.get('code', '')
        if not AuthService.verify_otp(user, code):
            error = 'Invalid or expired code'
        else:
            # 4. Activate account on first registration, then log the user in
            purpose = request.session.pop('otp_purpose', 'login')
            request.session.pop('pending_user_id', None)
            if purpose == 'register':
                AuthService.activate(user)
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('mirror:index')

    return render(request, 'accounts/verify.html', {
        'email': user.email,
        'seconds_remaining': seconds_remaining,
        'error': error,
    })


@require_POST
def resend_otp(request: HttpRequest) -> JsonResponse:
    """Generate and send a fresh OTP for the user currently in the verify flow.

    Args:
        request: Incoming HTTP POST request.

    Returns:
        JSON with ``ok: true`` and remaining seconds on success, or
        ``ok: false`` with an error message on failure.
    """
    user_id = request.session.get('pending_user_id')
    if not user_id:
        return JsonResponse({'ok': False, 'error': 'Session expired'})

    user = AuthService.get_user_by_id(user_id)
    if not user:
        return JsonResponse({'ok': False, 'error': 'User not found'})

    try:
        AuthService.send_otp(user)
    except RuntimeError:
        return JsonResponse({'ok': False, 'error': 'Could not send code'})

    lifetime: int = getattr(settings, 'OTP_LIFETIME_SECONDS', 60)
    return JsonResponse({'ok': True, 'seconds': lifetime})


def logout_view(request: HttpRequest) -> HttpResponse:
    """Terminate the current session and redirect to the login page.

    Args:
        request: Incoming HTTP request.

    Returns:
        Redirect to the login page.
    """
    logout(request)
    return redirect('accounts:login')


class AsyncPasswordResetView(DjangoPasswordResetView):
    """PasswordResetView that sends the reset email in a background thread."""

    def form_valid(self, form: PasswordResetForm) -> HttpResponseRedirect:  # type: ignore[override]
        opts = {
            'use_https': self.request.is_secure(),
            'token_generator': self.token_generator,
            'from_email': self.from_email,
            'email_template_name': self.email_template_name,
            'subject_template_name': self.subject_template_name,
            'request': self.request,
            'html_email_template_name': self.html_email_template_name,
            'extra_email_context': self.extra_email_context,
        }
        threading.Thread(target=form.save, kwargs=opts, daemon=True).start()
        return HttpResponseRedirect(self.get_success_url())
