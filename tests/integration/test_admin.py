"""Integration tests for the Django admin — verifies pages actually render,
not just that admin.py imports cleanly (import-time coverage hides broken
querysets/fieldsets that only surface on a real request).
"""

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_anonymous_redirected_to_admin_login(client):
    response = client.get("/admin/")
    assert response.status_code == 302
    assert "/admin/login/" in response["Location"]


@pytest.mark.django_db
def test_non_staff_user_redirected_to_admin_login(client, active_user):
    client.force_login(active_user)
    response = client.get("/admin/")
    assert response.status_code == 302
    assert "/admin/login/" in response["Location"]


@pytest.mark.django_db
def test_admin_index_renders(admin_client):
    response = admin_client.get("/admin/")
    assert response.status_code == 200


class TestUserAdmin:
    def test_changelist_renders(self, admin_client, active_user):
        response = admin_client.get(reverse("admin:accounts_user_changelist"))
        assert response.status_code == 200
        assert active_user.email.encode() in response.content

    def test_add_form_renders(self, admin_client):
        response = admin_client.get(reverse("admin:accounts_user_add"))
        assert response.status_code == 200

    def test_change_form_renders(self, admin_client, active_user):
        response = admin_client.get(
            reverse("admin:accounts_user_change", args=[active_user.pk])
        )
        assert response.status_code == 200

    def test_search_by_email(self, admin_client, active_user):
        response = admin_client.get(
            reverse("admin:accounts_user_changelist"), {"q": active_user.email}
        )
        assert response.status_code == 200
        assert active_user.email.encode() in response.content


class TestOTPCodeAdmin:
    def test_changelist_renders_and_shows_validity(
        self, admin_client, inactive_user, otp_for_user
    ):
        otp_for_user(inactive_user, code="1234")
        response = admin_client.get(reverse("admin:accounts_otpcode_changelist"))
        assert response.status_code == 200

    def test_change_form_renders_readonly(
        self, admin_client, inactive_user, otp_for_user
    ):
        otp = otp_for_user(inactive_user, code="1234")
        response = admin_client.get(
            reverse("admin:accounts_otpcode_change", args=[otp.pk])
        )
        assert response.status_code == 200
