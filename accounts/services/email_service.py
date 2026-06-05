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
        max_workers: int = getattr(settings, 'EMAIL_OTP_THREAD_POOL_SIZE', 4)
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
        max_retries: int = getattr(settings, 'EMAIL_OTP_MAX_RETRIES', 3)
        retry_delay: float = getattr(settings, 'EMAIL_OTP_RETRY_DELAY', 1.0)
        lifetime: int = getattr(settings, 'OTP_LIFETIME_SECONDS', 60)

        subject = 'Mirror — код подтверждения'
        message = (
            f'Ваш код подтверждения: {code}\n\n'
            f'Код действителен {lifetime} секунд.\n\n'
            f'Если вы не запрашивали код — просто проигнорируйте это письмо.'
        )

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

        The request is not blocked; delivery errors are logged by the worker.

        Args:
            email: Recipient address.
            code: 4-digit OTP string.
        """
        _get_executor().submit(EmailService.send_otp, email, code)
