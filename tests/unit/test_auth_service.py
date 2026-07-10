"""Unit tests for AuthService — repositories and email are mocked."""

import pytest
from unittest.mock import MagicMock, patch


AUTH = "accounts.services.auth_service"


class TestRegister:
    def test_creates_inactive_user_and_sends_otp(self, mock_user, mock_otp):
        with (
            patch(f"{AUTH}.transaction.atomic"),
            patch(f"{AUTH}.UserRepository") as ur,
            patch(f"{AUTH}.OTPRepository") as otr,
            patch(f"{AUTH}.EmailService") as es,
        ):
            ur.get_by_email.return_value = None
            ur.create.return_value = mock_user
            otr.delete_for_user.return_value = None
            otr.create.return_value = mock_otp

            from accounts.services.auth_service import AuthService

            result = AuthService.register("test@example.com", "password")

            ur.create.assert_called_once_with(
                email="test@example.com", password="password", is_active=False
            )
            es.send_otp_async.assert_called_once_with(
                email=mock_user.email, code=mock_otp.code
            )
            assert result is mock_user

    def test_raises_if_active_email_exists(self, mock_user):
        with patch(f"{AUTH}.transaction.atomic"), patch(f"{AUTH}.UserRepository") as ur:
            mock_user.is_active = True
            ur.get_by_email.return_value = mock_user

            from accounts.services.auth_service import AuthService
            from accounts.exceptions import UserAlreadyExistsError

            with pytest.raises(UserAlreadyExistsError):
                AuthService.register("test@example.com", "password")

    def test_reuses_inactive_user_with_new_password(self, mock_user, mock_otp):
        inactive = MagicMock()
        inactive.is_active = False
        with (
            patch(f"{AUTH}.transaction.atomic"),
            patch(f"{AUTH}.UserRepository") as ur,
            patch(f"{AUTH}.OTPRepository") as otr,
            patch(f"{AUTH}.EmailService"),
        ):
            ur.get_by_email.return_value = inactive
            ur.update_password.return_value = mock_user
            otr.create.return_value = mock_otp

            from accounts.services.auth_service import AuthService

            result = AuthService.register("test@example.com", "password")

            ur.update_password.assert_called_once_with(inactive, "password")
            ur.create.assert_not_called()
            assert result is mock_user


class TestSendOtp:
    def test_creates_otp_and_dispatches_email(self, mock_user, mock_otp):
        with (
            patch(f"{AUTH}.transaction.atomic"),
            patch(f"{AUTH}.OTPRepository") as otr,
            patch(f"{AUTH}.EmailService") as es,
            patch(f"{AUTH}.OTPCacheService") as cache,
        ):
            cache.get_resend_cooldown_ttl.return_value = 0
            otr.delete_for_user.return_value = None
            otr.create.return_value = mock_otp

            from accounts.services.auth_service import AuthService

            AuthService.send_otp(mock_user)

            otr.delete_for_user.assert_called_once_with(mock_user)
            es.send_otp_async.assert_called_once_with(
                email=mock_user.email, code=mock_otp.code
            )
            cache.set_resend_cooldown.assert_called_once_with(mock_user.email)

    def test_raises_cooldown_error_when_active(self, mock_user):
        with (
            patch(f"{AUTH}.OTPCacheService") as cache,
            patch(f"{AUTH}.OTPRepository") as otr,
            patch(f"{AUTH}.EmailService") as es,
        ):
            cache.get_resend_cooldown_ttl.return_value = 15

            from accounts.services.auth_service import AuthService
            from accounts.exceptions import OTPCooldownError

            with pytest.raises(OTPCooldownError) as exc_info:
                AuthService.send_otp(mock_user)

            assert exc_info.value.seconds_remaining == 15
            otr.create.assert_not_called()
            es.send_otp_async.assert_not_called()


class TestVerifyOtp:
    def test_valid_code_returns_true_and_deletes(self, mock_user, mock_otp):
        with (
            patch(f"{AUTH}.OTPRepository") as otr,
            patch(f"{AUTH}.OTPCacheService") as cache,
        ):
            cache.is_blocked.return_value = False
            otr.get_latest.return_value = mock_otp
            mock_otp.code = "1234"

            from accounts.services.auth_service import AuthService

            result = AuthService.verify_otp(mock_user, "1234")

            assert result is True
            otr.delete.assert_called_once_with(mock_otp)
            cache.reset_attempts.assert_called_once_with(mock_user.email)

    def test_wrong_code_returns_false(self, mock_user, mock_otp):
        with (
            patch(f"{AUTH}.OTPRepository") as otr,
            patch(f"{AUTH}.OTPCacheService") as cache,
        ):
            cache.is_blocked.return_value = False
            cache.record_failed_attempt.return_value = 1
            otr.get_latest.return_value = mock_otp
            mock_otp.code = "1234"

            from accounts.services.auth_service import AuthService

            assert AuthService.verify_otp(mock_user, "0000") is False
            cache.record_failed_attempt.assert_called_once_with(mock_user.email)

    def test_expired_otp_raises_expired_error(self, mock_user, expired_otp):
        with (
            patch(f"{AUTH}.OTPRepository") as otr,
            patch(f"{AUTH}.OTPCacheService") as cache,
        ):
            cache.is_blocked.return_value = False
            otr.get_latest.return_value = expired_otp

            from accounts.services.auth_service import AuthService
            from accounts.exceptions import OTPExpiredError

            with pytest.raises(OTPExpiredError):
                AuthService.verify_otp(mock_user, "1234")

    def test_no_otp_raises_expired_error(self, mock_user):
        with (
            patch(f"{AUTH}.OTPRepository") as otr,
            patch(f"{AUTH}.OTPCacheService") as cache,
        ):
            cache.is_blocked.return_value = False
            otr.get_latest.return_value = None

            from accounts.services.auth_service import AuthService
            from accounts.exceptions import OTPExpiredError

            with pytest.raises(OTPExpiredError):
                AuthService.verify_otp(mock_user, "1234")

    def test_blocked_email_raises_before_checking_code(self, mock_user):
        with (
            patch(f"{AUTH}.OTPCacheService") as cache,
            patch(f"{AUTH}.OTPRepository") as otr,
        ):
            cache.is_blocked.return_value = True

            from accounts.services.auth_service import AuthService
            from accounts.exceptions import OTPBlockedError

            with pytest.raises(OTPBlockedError):
                AuthService.verify_otp(mock_user, "1234")

            otr.get_latest.assert_not_called()

    def test_wrong_code_raises_blocked_error_at_max_attempts(self, mock_user, mock_otp):
        with (
            patch(f"{AUTH}.OTPRepository") as otr,
            patch(f"{AUTH}.OTPCacheService") as cache,
            patch(f"{AUTH}.settings") as mock_settings,
        ):
            cache.is_blocked.return_value = False
            cache.record_failed_attempt.return_value = 5
            mock_settings.OTP_MAX_ATTEMPTS = 5
            otr.get_latest.return_value = mock_otp
            mock_otp.code = "1234"

            from accounts.services.auth_service import AuthService
            from accounts.exceptions import OTPBlockedError

            with pytest.raises(OTPBlockedError):
                AuthService.verify_otp(mock_user, "0000")


class TestGetSecondsRemaining:
    def test_returns_zero_when_no_otp(self, mock_user):
        with patch(f"{AUTH}.OTPRepository") as otr:
            otr.get_latest.return_value = None

            from accounts.services.auth_service import AuthService

            assert AuthService.get_seconds_remaining(mock_user) == 0

    def test_returns_positive_seconds_when_otp_active(self, mock_user, mock_otp):
        with patch(f"{AUTH}.OTPRepository") as otr:
            otr.get_latest.return_value = mock_otp

            from accounts.services.auth_service import AuthService

            assert AuthService.get_seconds_remaining(mock_user) > 0


class TestAuthenticate:
    def test_valid_credentials_returns_user(self, mock_user):
        with (
            patch(f"{AUTH}.UserRepository") as ur,
            patch(f"{AUTH}.LoginCacheService") as cache,
        ):
            cache.is_blocked.return_value = False
            ur.get_by_email.return_value = mock_user

            from accounts.services.auth_service import AuthService

            result = AuthService.authenticate("test@example.com", "password")

            assert result is mock_user
            cache.reset_attempts.assert_called_once_with("test@example.com")
            cache.record_failed_attempt.assert_not_called()

    def test_wrong_password_returns_none_and_records_attempt(self, mock_user):
        mock_user.check_password = MagicMock(return_value=False)
        with (
            patch(f"{AUTH}.UserRepository") as ur,
            patch(f"{AUTH}.LoginCacheService") as cache,
        ):
            cache.is_blocked.return_value = False
            cache.record_failed_attempt.return_value = 1
            ur.get_by_email.return_value = mock_user

            from accounts.services.auth_service import AuthService

            assert AuthService.authenticate("test@example.com", "wrong") is None
            cache.record_failed_attempt.assert_called_once_with("test@example.com")

    def test_inactive_user_returns_none(self, mock_user):
        mock_user.is_active = False
        with (
            patch(f"{AUTH}.UserRepository") as ur,
            patch(f"{AUTH}.LoginCacheService") as cache,
        ):
            cache.is_blocked.return_value = False
            cache.record_failed_attempt.return_value = 1
            ur.get_by_email.return_value = mock_user

            from accounts.services.auth_service import AuthService

            assert AuthService.authenticate("test@example.com", "password") is None

    def test_unknown_email_returns_none(self):
        with (
            patch(f"{AUTH}.UserRepository") as ur,
            patch(f"{AUTH}.LoginCacheService") as cache,
        ):
            cache.is_blocked.return_value = False
            cache.record_failed_attempt.return_value = 1
            ur.get_by_email.return_value = None

            from accounts.services.auth_service import AuthService

            assert AuthService.authenticate("no@one.com", "password") is None

    def test_blocked_email_raises_before_checking_credentials(self, mock_user):
        with (
            patch(f"{AUTH}.UserRepository") as ur,
            patch(f"{AUTH}.LoginCacheService") as cache,
        ):
            cache.is_blocked.return_value = True

            from accounts.services.auth_service import AuthService
            from accounts.exceptions import LoginBlockedError

            with pytest.raises(LoginBlockedError):
                AuthService.authenticate("test@example.com", "password")

            ur.get_by_email.assert_not_called()

    def test_wrong_password_raises_blocked_error_at_max_attempts(self, mock_user):
        mock_user.check_password = MagicMock(return_value=False)
        with (
            patch(f"{AUTH}.UserRepository") as ur,
            patch(f"{AUTH}.LoginCacheService") as cache,
            patch(f"{AUTH}.settings") as mock_settings,
        ):
            cache.is_blocked.return_value = False
            cache.record_failed_attempt.return_value = 5
            mock_settings.LOGIN_MAX_ATTEMPTS = 5
            ur.get_by_email.return_value = mock_user

            from accounts.services.auth_service import AuthService
            from accounts.exceptions import LoginBlockedError

            with pytest.raises(LoginBlockedError):
                AuthService.authenticate("test@example.com", "wrong")
