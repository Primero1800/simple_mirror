import atexit
import logging
import time
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

_executor: ThreadPoolExecutor | None = None


def _get_executor() -> ThreadPoolExecutor:
    """Return the shared thread-pool, creating it lazily on first use."""
    global _executor
    if _executor is None:
        max_workers: int = settings.EMAIL_THREAD_POOL_SIZE
        _executor = ThreadPoolExecutor(max_workers=max_workers)
    return _executor


def _shutdown_executor() -> None:
    """Gracefully drain the pool on process exit (registered via atexit)."""
    if _executor is not None:
        _executor.shutdown(wait=False)


atexit.register(_shutdown_executor)


class EmailService:
    """Infrastructure service for sending OTP emails."""

    @staticmethod
    def send_otp(email: str, code: str) -> None:
        """Send an OTP verification email, retrying on transient failures.

        Retry count and delay are read from Django settings so they can be
        tuned per environment without code changes.

        Args:
            email: Recipient address.
            code: 4-digit OTP string.

        Raises:
            RuntimeError: When all retry attempts are exhausted.
        """
        max_retries: int = settings.EMAIL_MAX_RETRIES
        retry_delay: float = settings.EMAIL_RETRY_DELAY
        lifetime: int = settings.OTP_LIFETIME_SECONDS

        from django.utils.translation import gettext as _
        subject = _('Mirror — код подтверждения')
        message = _(
            'Ваш код подтверждения: %(code)s\n\n'
            'Код действителен %(lifetime)s секунд.\n\n'
            'Если вы не запрашивали код — просто проигнорируйте это письмо.'
        ) % {'code': code, 'lifetime': lifetime}

        last_exc: Exception | None = None
        for attempt in range(max_retries):
            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
                return
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    'OTP email to %s failed (attempt %d/%d): %s',
                    email, attempt + 1, max_retries, exc,
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))

        raise RuntimeError(
            f'Failed to send OTP email after {max_retries} attempts'
        ) from last_exc

    @staticmethod
    def send_otp_async(email: str, code: str) -> None:
        """Submit *send_otp* to the thread-pool (fire-and-forget).

        Captures the active language from the request thread and activates it
        in the worker thread so translated subject/body are used.

        Args:
            email: Recipient address.
            code: 4-digit OTP string.
        """
        from django.utils.translation import get_language, activate

        lang = get_language() or 'ru'

        def _run() -> None:
            activate(lang)
            EmailService.send_otp(email, code)

        _get_executor().submit(_run)
