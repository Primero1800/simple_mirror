"""Root conftest: infra mocks and shared fixtures available to all tests."""
import pytest
from datetime import datetime, timedelta


@pytest.fixture(autouse=True)
def mock_send_mail(mocker):
    """Patch send_mail globally so no real emails are dispatched in any test."""
    return mocker.patch('accounts.services.email_service.send_mail')


@pytest.fixture
def user_payload() -> dict:
    """Valid registration payload."""
    return {'email': 'user@example.com', 'password': 'Str0ngPass!', 'password2': 'Str0ngPass!'}


@pytest.fixture
def active_user(db):
    """Persisted, active User instance."""
    from accounts.repositories.user_repo import UserRepository
    return UserRepository.create(email='active@example.com', password='Str0ngPass!', is_active=True)


@pytest.fixture
def inactive_user(db):
    """Persisted, inactive User instance (registration not yet confirmed)."""
    from accounts.repositories.user_repo import UserRepository
    return UserRepository.create(email='inactive@example.com', password='Str0ngPass!', is_active=False)


@pytest.fixture
def otp_for_user(db):
    """Factory: create a valid OTPCode for any user."""
    def _factory(user, code='1234', offset_seconds=60):
        from accounts.repositories.otp_repo import OTPRepository
        return OTPRepository.create(
            user=user,
            code=code,
            expires_at=datetime.now() + timedelta(seconds=offset_seconds),
        )
    return _factory
