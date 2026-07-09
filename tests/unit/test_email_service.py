"""Unit tests for EmailService — send_mail is mocked at the module level."""
import pytest
from unittest.mock import MagicMock, patch

EMAIL = 'accounts.services.email_service'


class TestSendOtp:
    def test_success_on_first_attempt(self):
        with patch(f'{EMAIL}.send_mail') as sm:
            from accounts.services.email_service import EmailService
            EmailService.send_otp('a@b.com', '1234')
            sm.assert_called_once()

    def test_message_contains_code(self):
        with patch(f'{EMAIL}.send_mail') as sm:
            from accounts.services.email_service import EmailService
            EmailService.send_otp('a@b.com', '9999')
            _, kwargs = sm.call_args
            assert '9999' in kwargs.get('message', sm.call_args[0][1] if sm.call_args[0] else '')

    def test_retries_on_failure_then_succeeds(self):
        with patch(f'{EMAIL}.send_mail') as sm, patch(f'{EMAIL}.time') as t:
            sm.side_effect = [Exception('fail'), None]
            from accounts.services.email_service import EmailService
            EmailService.send_otp('a@b.com', '0000')
            assert sm.call_count == 2
            # exponential backoff: attempt 0 → delay * 2^0 = delay
            t.sleep.assert_called_once_with(0.5 * (2 ** 0))

    def test_raises_after_all_retries_exhausted(self, settings):
        settings.EMAIL_MAX_RETRIES = 2
        settings.EMAIL_RETRY_DELAY = 0.5
        with patch(f'{EMAIL}.send_mail', side_effect=Exception('boom')), \
             patch(f'{EMAIL}.time'):
            from accounts.services.email_service import EmailService
            with pytest.raises(RuntimeError, match='Failed to send OTP'):
                EmailService.send_otp('a@b.com', '1111')

    def test_no_sleep_after_last_attempt(self, settings):
        settings.EMAIL_MAX_RETRIES = 3
        settings.EMAIL_RETRY_DELAY = 0.5
        with patch(f'{EMAIL}.send_mail', side_effect=Exception('boom')), \
             patch(f'{EMAIL}.time') as t:
            from accounts.services.email_service import EmailService
            with pytest.raises(RuntimeError):
                EmailService.send_otp('a@b.com', '2222')
            # sleep is called max_retries-1 times (not after the last attempt)
            assert t.sleep.call_count == 2

    def test_backoff_doubles_each_attempt(self, settings):
        settings.EMAIL_MAX_RETRIES = 3
        settings.EMAIL_RETRY_DELAY = 0.5
        with patch(f'{EMAIL}.send_mail', side_effect=Exception('boom')), \
             patch(f'{EMAIL}.time') as t:
            from accounts.services.email_service import EmailService
            with pytest.raises(RuntimeError):
                EmailService.send_otp('a@b.com', '3333')
            # attempt 0 → 0.5s, attempt 1 → 1.0s
            calls = [c.args[0] for c in t.sleep.call_args_list]
            assert calls == [0.5, 1.0]


class TestSendOtpAsync:
    def test_submits_to_executor(self):
        with patch(f'{EMAIL}._get_executor') as ge:
            mock_executor = MagicMock()
            ge.return_value = mock_executor
            from accounts.services.email_service import EmailService
            EmailService.send_otp_async('a@b.com', '5678')
            mock_executor.submit.assert_called_once()
            # send_otp_async now submits a language-aware _run wrapper, not send_otp directly
            args = mock_executor.submit.call_args[0]
            assert callable(args[0])
