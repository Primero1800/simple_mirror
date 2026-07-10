"""Unit tests for UserRepository — real DB via pytest-django @pytest.mark.django_db."""

import pytest

from accounts.repositories.user_repo import UserRepository


@pytest.mark.django_db
class TestGetByEmail:
    def test_returns_user_when_found(self, active_user):
        found = UserRepository.get_by_email(active_user.email)
        assert found is not None
        assert found.pk == active_user.pk

    def test_returns_none_when_not_found(self):
        assert UserRepository.get_by_email("nobody@example.com") is None


@pytest.mark.django_db
class TestGetById:
    def test_returns_user_when_found(self, active_user):
        found = UserRepository.get_by_id(active_user.pk)
        assert found is not None
        assert found.email == active_user.email

    def test_returns_none_for_unknown_id(self):
        assert UserRepository.get_by_id(99999) is None


@pytest.mark.django_db
class TestCreate:
    def test_creates_active_user_by_default(self):
        user = UserRepository.create(email="new@example.com", password="Secret123")
        assert user.pk is not None
        assert user.is_active is True

    def test_creates_inactive_user_when_specified(self):
        user = UserRepository.create(
            email="pending@example.com", password="Secret123", is_active=False
        )
        assert user.is_active is False

    def test_password_is_hashed(self):
        user = UserRepository.create(email="hash@example.com", password="PlainText")
        assert user.check_password("PlainText") is True
        assert user.password != "PlainText"

    def test_email_is_used_as_username_field(self):
        user = UserRepository.create(email="uname@example.com", password="pass1234")
        assert user.email == "uname@example.com"


@pytest.mark.django_db
class TestSave:
    def test_persists_field_change(self, inactive_user):
        inactive_user.is_active = True
        returned = UserRepository.save(inactive_user)
        assert returned is inactive_user

        from django.contrib.auth import get_user_model

        User = get_user_model()
        refreshed = User.objects.get(pk=inactive_user.pk)
        assert refreshed.is_active is True
