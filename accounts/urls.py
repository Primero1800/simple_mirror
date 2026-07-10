from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from accounts import views
from accounts.views import AsyncPasswordResetView

app_name = "accounts"

_tpl = "accounts/{}.html"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("verify/", views.verify_otp, name="verify"),
    path("resend/", views.resend_otp, name="resend_otp"),
    path("logout/", views.logout_view, name="logout"),
    # ── password reset (стандартные Django-вью) ───────────────────────────────
    path(
        "password-reset/",
        AsyncPasswordResetView.as_view(
            template_name=_tpl.format("password_reset_form"),
            email_template_name=_tpl.format("password_reset_email"),
            subject_template_name="accounts/password_reset_subject.txt",
            success_url=reverse_lazy("accounts:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name=_tpl.format("password_reset_done"),
        ),
        name="password_reset_done",
    ),
    path(
        "password-reset/confirm/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name=_tpl.format("password_reset_confirm"),
            success_url=reverse_lazy("accounts:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "password-reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name=_tpl.format("password_reset_complete"),
        ),
        name="password_reset_complete",
    ),
]
