"""Unit tests for OTPCacheService — real LocMemCache via settings_test CACHES."""

import pytest
from unittest.mock import patch

from django.core.cache import caches
from redis.exceptions import RedisError

from accounts.services.otp_cache import OTPCacheService

CACHE = "accounts.services.otp_cache"


@pytest.fixture(autouse=True)
def clear_otp_cache():
    """Ensure the 'otp' LocMemCache alias starts empty for every test."""
    caches["otp"].clear()
    yield
    caches["otp"].clear()


class TestIsBlocked:
    def test_false_when_no_attempts_recorded(self):
        assert OTPCacheService.is_blocked("user@example.com") is False

    def test_true_when_attempts_reach_max(self, settings):
        settings.OTP_MAX_ATTEMPTS = 3
        for _ in range(3):
            OTPCacheService.record_failed_attempt("user@example.com")
        assert OTPCacheService.is_blocked("user@example.com") is True

    def test_false_on_redis_error(self):
        with patch(f"{CACHE}.caches") as mock_caches:
            mock_caches.__getitem__.side_effect = RedisError("down")
            assert OTPCacheService.is_blocked("user@example.com") is False

    def test_false_when_max_attempts_disabled(self, settings):
        settings.OTP_MAX_ATTEMPTS = 0
        for _ in range(5):
            OTPCacheService.record_failed_attempt("user@example.com")
        assert OTPCacheService.is_blocked("user@example.com") is False


class TestRecordFailedAttempt:
    def test_increments_across_calls(self):
        first = OTPCacheService.record_failed_attempt("user@example.com")
        second = OTPCacheService.record_failed_attempt("user@example.com")
        assert first == 1
        assert second == 2

    def test_returns_zero_on_redis_error(self):
        with patch(f"{CACHE}.caches") as mock_caches:
            mock_caches.__getitem__.side_effect = RedisError("down")
            assert OTPCacheService.record_failed_attempt("user@example.com") == 0


class TestResetAttempts:
    def test_clears_counter(self, settings):
        settings.OTP_MAX_ATTEMPTS = 1
        OTPCacheService.record_failed_attempt("user@example.com")
        OTPCacheService.reset_attempts("user@example.com")
        assert OTPCacheService.is_blocked("user@example.com") is False

    def test_swallows_redis_error(self):
        with patch(f"{CACHE}.caches") as mock_caches:
            mock_caches.__getitem__.side_effect = RedisError("down")
            OTPCacheService.reset_attempts("user@example.com")  # must not raise


class TestResendCooldown:
    def test_ttl_zero_when_not_set(self):
        assert OTPCacheService.get_resend_cooldown_ttl("user@example.com") == 0

    def test_ttl_positive_after_set(self, settings):
        settings.OTP_RESEND_COOLDOWN_SECONDS = 30
        OTPCacheService.set_resend_cooldown("user@example.com")
        ttl = OTPCacheService.get_resend_cooldown_ttl("user@example.com")
        assert 0 < ttl <= 30

    def test_set_cooldown_swallows_redis_error(self):
        with patch(f"{CACHE}.caches") as mock_caches:
            mock_caches.__getitem__.side_effect = RedisError("down")
            OTPCacheService.set_resend_cooldown("user@example.com")  # must not raise

    def test_get_ttl_returns_zero_on_redis_error(self):
        with patch(f"{CACHE}.caches") as mock_caches:
            mock_caches.__getitem__.side_effect = RedisError("down")
            assert OTPCacheService.get_resend_cooldown_ttl("user@example.com") == 0
