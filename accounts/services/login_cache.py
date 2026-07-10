import logging

from django.conf import settings
from django.core.cache import caches
from django_redis.exceptions import ConnectionInterrupted
from redis.exceptions import RedisError

_ALIAS = "otp"
_SEP: str = settings.OTP_CACHE_KEY_SEPARATOR
_PREFIX: str = settings.LOGIN_ATTEMPTS_KEY_PREFIX

logger = logging.getLogger(__name__)


class LoginCacheService:
    """Cache adapter for login brute-force rate-limiting.

    Wraps the 'otp' Django cache alias (Redis db=1). All methods apply
    fail-open on Redis errors: infrastructure failures are logged but never
    counted as user actions.
    """

    @staticmethod
    def is_blocked(email: str) -> bool:
        """Return True if the email has reached the maximum failed login attempt limit.

        Args:
            email: User email address.

        Returns:
            True when the attempt counter equals or exceeds LOGIN_MAX_ATTEMPTS;
            False otherwise. Returns False on Redis errors (fail-open).
        """
        max_attempts: int = settings.LOGIN_MAX_ATTEMPTS
        if max_attempts == 0:
            return False
        try:
            attempts = caches[_ALIAS].get(f"{_PREFIX}{_SEP}{email}")
        except (ConnectionInterrupted, RedisError) as exc:
            logger.error(
                "Redis unavailable in login is_blocked: %s: %s", type(exc).__name__, exc
            )
            return False
        return attempts is not None and attempts >= max_attempts

    @staticmethod
    def record_failed_attempt(email: str) -> int:
        """Increment the failed login attempt counter for an email address.

        The key is created with the default TTL from the 'otp' cache alias
        (24 h) on the first call. Subsequent calls only increment without
        resetting the TTL, so the block window is anchored to the first failure.

        Args:
            email: User email address.

        Returns:
            Updated attempt count after increment, or 0 on Redis errors.
            A Redis error is not a user action — the caller must not treat
            a 0 return as a failed attempt.
        """
        key = f"{_PREFIX}{_SEP}{email}"
        try:
            caches[_ALIAS].add(key, 0)
            return caches[_ALIAS].incr(key)
        except (ConnectionInterrupted, RedisError) as exc:
            logger.error(
                "Redis unavailable in login record_failed_attempt: %s: %s",
                type(exc).__name__,
                exc,
            )
            return 0

    @staticmethod
    def reset_attempts(email: str) -> None:
        """Delete the attempt counter after a successful login.

        Args:
            email: User email address.
        """
        try:
            caches[_ALIAS].delete(f"{_PREFIX}{_SEP}{email}")
        except (ConnectionInterrupted, RedisError) as exc:
            logger.error(
                "Redis unavailable in login reset_attempts: %s: %s",
                type(exc).__name__,
                exc,
            )
