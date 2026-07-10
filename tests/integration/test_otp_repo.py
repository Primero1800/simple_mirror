"""Unit tests for OTPRepository — real DB via pytest-django @pytest.mark.django_db."""

import pytest
from datetime import datetime, timedelta

from accounts.repositories.otp_repo import OTPRepository


@pytest.mark.django_db
class TestDeleteForUser:
    def test_deletes_all_codes_for_user(self, active_user, otp_for_user):
        otp_for_user(active_user, code="0001")
        otp_for_user(active_user, code="0002")
        OTPRepository.delete_for_user(active_user)
        assert OTPRepository.get_latest(active_user) is None

    def test_does_not_affect_other_users(
        self, active_user, inactive_user, otp_for_user
    ):
        otp_for_user(active_user, code="1111")
        otp_for_user(inactive_user, code="2222")
        OTPRepository.delete_for_user(active_user)
        assert OTPRepository.get_latest(inactive_user) is not None


@pytest.mark.django_db
class TestCreate:
    def test_persists_record(self, active_user):
        expires = datetime.now() + timedelta(seconds=60)
        otp = OTPRepository.create(user=active_user, code="4321", expires_at=expires)
        assert otp.pk is not None
        assert otp.code == "4321"
        assert otp.user == active_user

    def test_returns_otp_code_instance(self, active_user):
        from accounts.models import OTPCode

        expires = datetime.now() + timedelta(seconds=30)
        otp = OTPRepository.create(user=active_user, code="0000", expires_at=expires)
        assert isinstance(otp, OTPCode)


@pytest.mark.django_db
class TestGetLatest:
    def test_returns_none_when_no_codes(self, active_user):
        assert OTPRepository.get_latest(active_user) is None

    def test_returns_most_recent_code(self, active_user, otp_for_user):
        otp_for_user(active_user, code="1111")
        otp2 = otp_for_user(active_user, code="2222")
        latest = OTPRepository.get_latest(active_user)
        # OTPCode.Meta.ordering = ['-created_at'], so 2222 is first
        assert latest.code == otp2.code


@pytest.mark.django_db
class TestDelete:
    def test_removes_single_record(self, active_user, otp_for_user):
        otp = otp_for_user(active_user, code="9999")
        OTPRepository.delete(otp)
        assert OTPRepository.get_latest(active_user) is None

    def test_leaves_other_records_intact(self, active_user, otp_for_user):
        otp1 = otp_for_user(active_user, code="1111")
        otp_for_user(active_user, code="2222")
        OTPRepository.delete(otp1)
        remaining = OTPRepository.get_latest(active_user)
        assert remaining is not None
