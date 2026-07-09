"""Unit tests for the User model and its manager — real DB via @pytest.mark.django_db."""
import pytest

from accounts.models import User


@pytest.mark.django_db
class TestUserManager:
    def test_create_user_requires_email(self):
        with pytest.raises(ValueError):
            User.objects.create_user(email='', password='Secret123')

    def test_create_superuser_sets_privilege_flags(self):
        user = User.objects.create_superuser(email='admin@example.com', password='Secret123')
        assert user.is_staff is True
        assert user.is_superuser is True
        assert user.is_active is True


@pytest.mark.django_db
class TestUserStr:
    def test_str_returns_email(self):
        user = User.objects.create_user(email='str@example.com', password='Secret123')
        assert str(user) == 'str@example.com'
