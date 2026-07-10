"""Integration tests for auth endpoints (register / login / verify / resend / logout)."""

import pytest
from django.core.cache import caches
from django.urls import reverse


@pytest.fixture(autouse=True)
def clear_otp_cache():
    """Ensure the 'otp' rate-limit cache starts empty for every test."""
    caches["otp"].clear()
    yield
    caches["otp"].clear()


# ── Register ──────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_register_get_renders_form(client):
    response = client.get(reverse("accounts:register"))
    assert response.status_code == 200
    assert "accounts/register.html" in [t.name for t in response.templates]


@pytest.mark.django_db
def test_register_success_redirects_to_verify(client, user_payload):
    response = client.post(reverse("accounts:register"), user_payload)
    assert response.status_code == 302
    assert response["Location"] == reverse("accounts:verify")


@pytest.mark.django_db
def test_register_success_stores_pending_session(client, user_payload):
    client.post(reverse("accounts:register"), user_payload)
    assert "pending_user_id" in client.session
    assert client.session["otp_purpose"] == "register"


@pytest.mark.django_db
def test_register_duplicate_active_user_shows_error(client, user_payload, active_user):
    user_payload["email"] = active_user.email
    response = client.post(reverse("accounts:register"), user_payload)
    assert response.status_code == 200
    assert response.context["form"].errors


@pytest.mark.django_db
def test_register_replaces_inactive_user(client, user_payload, inactive_user):
    user_payload["email"] = inactive_user.email
    response = client.post(reverse("accounts:register"), user_payload)
    assert response.status_code == 302


@pytest.mark.django_db
def test_register_password_mismatch_shows_error(client):
    response = client.post(
        reverse("accounts:register"),
        {
            "email": "a@b.com",
            "password": "pass1234",
            "password2": "different",
        },
    )
    assert response.status_code == 200
    assert response.context["form"].errors


# ── Login ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_login_get_renders_form(client):
    response = client.get(reverse("accounts:login"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_login_valid_credentials_redirects_to_verify(client, active_user):
    response = client.post(
        reverse("accounts:login"),
        {
            "email": active_user.email,
            "password": "Str0ngPass!",
        },
    )
    assert response.status_code == 302
    assert response["Location"] == reverse("accounts:verify")


@pytest.mark.django_db
def test_login_wrong_password_shows_error(client, active_user):
    response = client.post(
        reverse("accounts:login"),
        {
            "email": active_user.email,
            "password": "wrongpassword",
        },
    )
    assert response.status_code == 200
    assert response.context["error"] is not None


@pytest.mark.django_db
def test_login_inactive_user_shows_error(client, inactive_user):
    response = client.post(
        reverse("accounts:login"),
        {
            "email": inactive_user.email,
            "password": "Str0ngPass!",
        },
    )
    assert response.status_code == 200
    assert response.context["error"] is not None


@pytest.mark.django_db
def test_login_blocked_after_max_attempts_shows_error(client, settings, active_user):
    settings.LOGIN_MAX_ATTEMPTS = 1
    wrong_credentials = {"email": active_user.email, "password": "wrongpassword"}
    client.post(
        reverse("accounts:login"), wrong_credentials
    )  # first wrong attempt trips the lockout

    response = client.post(reverse("accounts:login"), wrong_credentials)
    assert response.status_code == 200
    assert response.context["error"] is not None


@pytest.mark.django_db
def test_login_during_resend_cooldown_shows_error(client, settings, active_user):
    settings.OTP_RESEND_COOLDOWN_SECONDS = 30
    credentials = {"email": active_user.email, "password": "Str0ngPass!"}
    client.post(reverse("accounts:login"), credentials)  # first OTP starts the cooldown

    response = client.post(reverse("accounts:login"), credentials)
    assert response.status_code == 200
    assert response.context["error"] is not None


# ── Verify ────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_verify_no_session_redirects_to_login(client):
    response = client.get(reverse("accounts:verify"))
    assert response.status_code == 302
    assert reverse("accounts:login") in response["Location"]


@pytest.mark.django_db
def test_verify_stale_user_id_redirects_to_login(client, db):
    session = client.session
    session["pending_user_id"] = 999999
    session.save()
    response = client.get(reverse("accounts:verify"))
    assert response.status_code == 302
    assert reverse("accounts:login") in response["Location"]


@pytest.mark.django_db
def test_verify_correct_code_logs_in_and_redirects(client, pending_session):
    pending_client, user = pending_session
    response = pending_client.post(reverse("accounts:verify"), {"code": "1234"})
    assert response.status_code == 302
    assert response["Location"] == reverse("mirror:index")


@pytest.mark.django_db
def test_verify_wrong_code_shows_error(client, pending_session):
    pending_client, _ = pending_session
    response = pending_client.post(reverse("accounts:verify"), {"code": "0000"})
    assert response.status_code == 200
    assert response.context["error"] is not None


@pytest.mark.django_db
def test_verify_expired_code_shows_error(client, db, inactive_user, otp_for_user):
    otp_for_user(inactive_user, code="5678", offset_seconds=-1)
    session = client.session
    session["pending_user_id"] = inactive_user.pk
    session["otp_purpose"] = "register"
    session.save()
    response = client.post(reverse("accounts:verify"), {"code": "5678"})
    assert response.status_code == 200
    assert response.context["error"] is not None


@pytest.mark.django_db
def test_verify_blocked_after_max_attempts_shows_error(
    client, settings, pending_session
):
    settings.OTP_MAX_ATTEMPTS = 1
    pending_client, _ = pending_session
    response = pending_client.post(reverse("accounts:verify"), {"code": "0000"})
    assert response.status_code == 200
    assert response.context["error"] is not None


# ── Resend ────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_resend_no_session_returns_error_json(client):
    response = client.post(reverse("accounts:resend_otp"))
    assert response.status_code == 200
    assert response.json()["ok"] is False


@pytest.mark.django_db
def test_resend_stale_user_id_returns_error_json(client, db):
    session = client.session
    session["pending_user_id"] = 999999
    session.save()
    response = client.post(reverse("accounts:resend_otp"))
    assert response.json()["ok"] is False


@pytest.mark.django_db
def test_resend_with_session_returns_ok(client, pending_session):
    pending_client, _ = pending_session
    response = pending_client.post(reverse("accounts:resend_otp"))
    assert response.json()["ok"] is True
    assert "seconds" in response.json()


@pytest.mark.django_db
def test_resend_during_cooldown_returns_error(client, settings, pending_session):
    settings.OTP_RESEND_COOLDOWN_SECONDS = 30
    pending_client, _ = pending_session
    pending_client.post(
        reverse("accounts:resend_otp")
    )  # first call starts the cooldown

    response = pending_client.post(reverse("accounts:resend_otp"))
    body = response.json()
    assert body["ok"] is False
    assert body["seconds_remaining"] > 0


# ── Logout ────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_logout_redirects_to_login(auth_client):
    client, _ = auth_client
    response = client.post(reverse("accounts:logout"))
    assert response.status_code == 302
    assert reverse("accounts:login") in response["Location"]


# ── Password reset ───────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_password_reset_redirects_to_done(client, active_user):
    response = client.post(
        reverse("accounts:password_reset"), {"email": active_user.email}
    )
    assert response.status_code == 302
    assert response["Location"] == reverse("accounts:password_reset_done")
