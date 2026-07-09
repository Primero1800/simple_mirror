from django.conf import settings
from django.core.cache import caches

_ALIAS = 'otp'
_SEP: str = settings.OTP_CACHE_KEY_SEPARATOR
_ATTEMPTS_PREFIX: str = settings.OTP_ATTEMPTS_KEY_PREFIX
_COOLDOWN_PREFIX: str = settings.OTP_COOLDOWN_KEY_PREFIX


class OTPCacheService:
    """Cache adapter for OTP rate-limiting data.

    Wraps the 'otp' Django cache alias (Redis db=1). TTLs for attempt counters
    come from the CACHES config default; cooldown TTL is read from settings.
    """

    @staticmethod
    def is_blocked(email: str) -> bool:
        """Return True if the email has reached the maximum OTP attempt limit.

        Args:
            email: User email address.

        Returns:
            True when the attempt counter exists and equals or exceeds
            OTP_MAX_ATTEMPTS; False otherwise.
        """
        attempts = caches[_ALIAS].get(f"{_ATTEMPTS_PREFIX}{_SEP}{email}")
        max_attempts: int = settings.OTP_MAX_ATTEMPTS
        return attempts is not None and attempts >= max_attempts

    @staticmethod
    def record_failed_attempt(email: str) -> int:
        """Increment the failed OTP attempt counter for an email address.

        The key is created with the default TTL from the 'otp' cache alias
        (24 h) on the first call. Subsequent calls only increment the counter
        without resetting the TTL, so the block window is anchored to the
        first failed attempt.

        Args:
            email: User email address.

        Returns:
            Updated attempt count after increment.
        """
        key = f"{_ATTEMPTS_PREFIX}{_SEP}{email}"
        caches[_ALIAS].add(key, 0)   # no-op if key already exists
        return caches[_ALIAS].incr(key)

    @staticmethod
    def reset_attempts(email: str) -> None:
        """Delete the attempt counter after a successful OTP verification.

        Args:
            email: User email address.
        """
        caches[_ALIAS].delete(f"{_ATTEMPTS_PREFIX}{_SEP}{email}")

    @staticmethod
    def set_resend_cooldown(email: str) -> None:
        """Start the resend cooldown window for an email address.

        TTL is read from OTP_RESEND_COOLDOWN_SECONDS in settings.

        Args:
            email: User email address.
        """
        cooldown: int = settings.OTP_RESEND_COOLDOWN_SECONDS
        caches[_ALIAS].set(f"{_COOLDOWN_PREFIX}{_SEP}{email}", 1, timeout=cooldown)

    @staticmethod
    def get_resend_cooldown_ttl(email: str) -> int:
        """Return seconds remaining on the resend cooldown, or 0 if inactive.

        Args:
            email: User email address.

        Returns:
            Remaining seconds; 0 means the cooldown has expired or was never set.
        """
        ttl = caches[_ALIAS].ttl(f"{_COOLDOWN_PREFIX}{_SEP}{email}")
        return max(0, ttl or 0)
