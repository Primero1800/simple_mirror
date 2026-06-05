"""Unit tests for AuthService — repositories and email are mocked."""
import pytest
from unittest.mock import MagicMock, patch


AUTH = 'accounts.services.auth_service'


@pytest.mark.django_db
class TestRegister:
    def test_creates_inactive_user_and_sends_otp(self, mock_user, mock_otp):
        with patch(f'{AUTH}.UserRepository') as ur, \
             patch(f'{AUTH}.OTPRepository') as otr, \
             patch(f'{AUTH}.EmailService') as es:
            ur.get_by_email.return_value = None
            ur.create.return_value = mock_user
            otr.delete_for_user.return_value = None
            otr.create.return_value = mock_otp

            from accounts.services.auth_service import AuthService
            result = AuthService.register('test@example.com', 'password')

            ur.create.assert_called_once_with(
                email='test@example.com', password='password', is_active=False
            )
            es.send_otp_async.assert_called_once_with(
                email=mock_user.email, code=mock_otp.code
            )
            assert result is mock_user

    def test_raises_if_active_email_exists(self, mock_user):
        with patch(f'{AUTH}.UserRepository') as ur:
            mock_user.is_active = True
            ur.get_by_email.return_value = mock_user

            from accounts.services.auth_service import AuthService
            with pytest.raises(ValueError, match='already exists'):
                AuthService.register('test@example.com', 'password')

    def test_replaces_inactive_user(self, mock_user, mock_otp):
        inactive = MagicMock()
        inactive.is_active = False
        with patch(f'{AUTH}.UserRepository') as ur, \
             patch(f'{AUTH}.OTPRepository') as otr, \
             patch(f'{AUTH}.EmailService'):
            ur.get_by_email.return_value = inactive
            ur.create.return_value = mock_user
            otr.create.return_value = mock_otp

            from accounts.services.auth_service import AuthService
            AuthService.register('test@example.com', 'password')

            inactive.delete.assert_called_once()


@pytest.mark.django_db
class TestSendOtp:
    def test_creates_otp_and_dispatches_email(self, mock_user, mock_otp):
        with patch(f'{AUTH}.OTPRepository') as otr, \
             patch(f'{AUTH}.EmailService') as es:
            otr.delete_for_user.return_value = None
            otr.create.return_value = mock_otp

            from accounts.services.auth_service import AuthService
            AuthService.send_otp(mock_user)

            otr.delete_for_user.assert_called_once_with(mock_user)
            es.send_otp_async.assert_called_once_with(
                email=mock_user.email, code=mock_otp.code
            )


class TestVerifyOtp:
    def test_valid_code_returns_true_and_deletes(self, mock_user, mock_otp):
        with patch(f'{AUTH}.OTPRepository') as otr:
            otr.get_latest.return_value = mock_otp
            mock_otp.code = '1234'

            from accounts.services.auth_service import AuthService
            result = AuthService.verify_otp(mock_user, '1234')

            assert result is True
            otr.delete.assert_called_once_with(mock_otp)

    def test_wrong_code_returns_false(self, mock_user, mock_otp):
        with patch(f'{AUTH}.OTPRepository') as otr:
            otr.get_latest.return_value = mock_otp
            mock_otp.code = '1234'

            from accounts.services.auth_service import AuthService
            assert AuthService.verify_otp(mock_user, '0000') is False

    def test_expired_otp_returns_false(self, mock_user, expired_otp):
        with patch(f'{AUTH}.OTPRepository') as otr:
            otr.get_latest.return_value = expired_otp

            from accounts.services.auth_service import AuthService
            assert AuthService.verify_otp(mock_user, '1234') is False

    def test_no_otp_returns_false(self, mock_user):
        with patch(f'{AUTH}.OTPRepository') as otr:
            otr.get_latest.return_value = None

            from accounts.services.auth_service import AuthService
            assert AuthService.verify_otp(mock_user, '1234') is False


class TestAuthenticate:
    def test_valid_credentials_returns_user(self, mock_user):
        with patch(f'{AUTH}.UserRepository') as ur:
            ur.get_by_email.return_value = mock_user

            from accounts.services.auth_service import AuthService
            result = AuthService.authenticate('test@example.com', 'password')
            assert result is mock_user

    def test_wrong_password_returns_none(self, mock_user):
        mock_user.check_password = MagicMock(return_value=False)
        with patch(f'{AUTH}.UserRepository') as ur:
            ur.get_by_email.return_value = mock_user

            from accounts.services.auth_service import AuthService
            assert AuthService.authenticate('test@example.com', 'wrong') is None

    def test_inactive_user_returns_none(self, mock_user):
        mock_user.is_active = False
        with patch(f'{AUTH}.UserRepository') as ur:
            ur.get_by_email.return_value = mock_user

            from accounts.services.auth_service import AuthService
            assert AuthService.authenticate('test@example.com', 'password') is None

    def test_unknown_email_returns_none(self):
        with patch(f'{AUTH}.UserRepository') as ur:
            ur.get_by_email.return_value = None

            from accounts.services.auth_service import AuthService
            assert AuthService.authenticate('no@one.com', 'password') is None
