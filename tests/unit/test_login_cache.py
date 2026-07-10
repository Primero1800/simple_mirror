"""Unit tests for LoginCacheService — real LocMemCache via settings_test CACHES."""

import pytest
from unittest.mock import patch

from django.core.cache import caches
from redis.exceptions import RedisError

from accounts.services.login_cache import LoginCacheService

CACHE = "accounts.services.login_cache"


@pytest.fixture(autouse=True)
def clear_login_cache():
    """Ensure the 'otp' LocMemCache alias starts empty for every test."""
    caches["otp"].clear()
    yield
    caches["otp"].clear()


class TestIsBlocked:
    def test_false_when_no_attempts_recorded(self):
        assert LoginCacheService.is_blocked("user@example.com") is False

    def test_true_when_attempts_reach_max(self, settings):
        settings.LOGIN_MAX_ATTEMPTS = 3
        for _ in range(3):
            LoginCacheService.record_failed_attempt("user@example.com")
        assert LoginCacheService.is_blocked("user@example.com") is True

    def test_false_when_max_attempts_disabled(self, settings):
        settings.LOGIN_MAX_ATTEMPTS = 0
        for _ in range(5):
            LoginCacheService.record_failed_attempt("user@example.com")
        assert LoginCacheService.is_blocked("user@example.com") is False

    def test_false_on_redis_error(self, settings):
        settings.LOGIN_MAX_ATTEMPTS = 5
        with patch(f"{CACHE}.caches") as mock_caches:
            mock_caches.__getitem__.side_effect = RedisError("down")
            assert LoginCacheService.is_blocked("user@example.com") is False


class TestRecordFailedAttempt:
    def test_increments_across_calls(self):
        first = LoginCacheService.record_failed_attempt("user@example.com")
        second = LoginCacheService.record_failed_attempt("user@example.com")
        assert first == 1
        assert second == 2

    def test_returns_zero_on_redis_error(self):
        with patch(f"{CACHE}.caches") as mock_caches:
            mock_caches.__getitem__.side_effect = RedisError("down")
            assert LoginCacheService.record_failed_attempt("user@example.com") == 0


class TestResetAttempts:
    def test_clears_counter(self, settings):
        settings.LOGIN_MAX_ATTEMPTS = 1
        LoginCacheService.record_failed_attempt("user@example.com")
        LoginCacheService.reset_attempts("user@example.com")
        assert LoginCacheService.is_blocked("user@example.com") is False

    def test_swallows_redis_error(self):
        with patch(f"{CACHE}.caches") as mock_caches:
            mock_caches.__getitem__.side_effect = RedisError("down")
            LoginCacheService.reset_attempts("user@example.com")  # must not raise
