"""Unit conftest: lightweight mock fixtures for service and repository tests."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from accounts.models import OTPCode, User


@pytest.fixture
def mock_user() -> MagicMock:
    """Mock User with sensible defaults."""
    user = MagicMock(spec=User)
    user.pk = 1
    user.email = "test@example.com"
    user.is_active = True
    user.check_password = MagicMock(return_value=True)
    return user


@pytest.fixture
def mock_inactive_user(mock_user) -> MagicMock:
    mock_user.is_active = False
    return mock_user


@pytest.fixture
def mock_otp() -> MagicMock:
    """Mock OTPCode that is valid by default."""
    otp = MagicMock(spec=OTPCode)
    otp.code = "1234"
    otp.expires_at = datetime.now() + timedelta(seconds=60)
    otp.is_valid = MagicMock(return_value=True)
    return otp


@pytest.fixture
def expired_otp(mock_otp) -> MagicMock:
    mock_otp.expires_at = datetime.now() - timedelta(seconds=1)
    mock_otp.is_valid = MagicMock(return_value=False)
    return mock_otp
