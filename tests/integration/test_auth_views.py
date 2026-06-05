"""Integration tests for auth endpoints (register / login / verify / resend / logout)."""
import pytest


# ── Register ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_register_get_renders_form(client):
    response = client.get('/accounts/register/')
    assert response.status_code == 200
    assert 'accounts/register.html' in [t.name for t in response.templates]


@pytest.mark.django_db
def test_register_success_redirects_to_verify(client, user_payload):
    response = client.post('/accounts/register/', user_payload)
    assert response.status_code == 302
    assert response['Location'] == '/accounts/verify/'


@pytest.mark.django_db
def test_register_success_stores_pending_session(client, user_payload):
    client.post('/accounts/register/', user_payload)
    assert 'pending_user_id' in client.session
    assert client.session['otp_purpose'] == 'register'


@pytest.mark.django_db
def test_register_duplicate_active_user_shows_error(client, user_payload, active_user):
    user_payload['email'] = active_user.email
    response = client.post('/accounts/register/', user_payload)
    assert response.status_code == 200
    assert 'already exists' in response.content.decode()


@pytest.mark.django_db
def test_register_replaces_inactive_user(client, user_payload, inactive_user):
    """Registering with the same email as an inactive user must succeed."""
    user_payload['email'] = inactive_user.email
    response = client.post('/accounts/register/', user_payload)
    assert response.status_code == 302


@pytest.mark.django_db
def test_register_password_mismatch_shows_error(client):
    response = client.post('/accounts/register/', {
        'email': 'a@b.com', 'password': 'pass1234', 'password2': 'different',
    })
    assert response.status_code == 200
    assert response.context['form'].errors


# ── Login ─────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_login_get_renders_form(client):
    response = client.get('/accounts/login/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_login_valid_credentials_redirects_to_verify(client, active_user):
    response = client.post('/accounts/login/', {
        'email': active_user.email, 'password': 'Str0ngPass!',
    })
    assert response.status_code == 302
    assert response['Location'] == '/accounts/verify/'


@pytest.mark.django_db
def test_login_wrong_password_shows_error(client, active_user):
    response = client.post('/accounts/login/', {
        'email': active_user.email, 'password': 'wrongpassword',
    })
    assert response.status_code == 200
    assert response.context['error'] is not None


@pytest.mark.django_db
def test_login_inactive_user_shows_error(client, inactive_user):
    response = client.post('/accounts/login/', {
        'email': inactive_user.email, 'password': 'Str0ngPass!',
    })
    assert response.status_code == 200
    assert response.context['error'] is not None


# ── Verify ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_verify_no_session_redirects_to_login(client):
    response = client.get('/accounts/verify/')
    assert response.status_code == 302
    assert '/login/' in response['Location']


@pytest.mark.django_db
def test_verify_correct_code_logs_in_and_redirects(client, pending_session):
    pending_client, user = pending_session
    response = pending_client.post('/accounts/verify/', {'code': '1234'})
    assert response.status_code == 302
    assert response['Location'] == '/'


@pytest.mark.django_db
def test_verify_wrong_code_shows_error(client, pending_session):
    pending_client, _ = pending_session
    response = pending_client.post('/accounts/verify/', {'code': '0000'})
    assert response.status_code == 200
    assert response.context['error'] is not None


@pytest.mark.django_db
def test_verify_expired_code_shows_error(client, db, inactive_user, otp_for_user):
    otp_for_user(inactive_user, code='5678', offset_seconds=-1)
    session = client.session
    session['pending_user_id'] = inactive_user.pk
    session['otp_purpose'] = 'register'
    session.save()

    response = client.post('/accounts/verify/', {'code': '5678'})
    assert response.status_code == 200
    assert response.context['error'] is not None


# ── Resend ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_resend_no_session_returns_error_json(client):
    response = client.post('/accounts/resend/')
    assert response.status_code == 200
    assert response.json()['ok'] is False


@pytest.mark.django_db
def test_resend_with_session_returns_ok(client, pending_session):
    pending_client, _ = pending_session
    response = pending_client.post('/accounts/resend/')
    assert response.json()['ok'] is True
    assert 'seconds' in response.json()


# ── Logout ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_logout_redirects_to_login(auth_client):
    client, _ = auth_client
    response = client.post('/accounts/logout/')
    assert response.status_code == 302
    assert '/login/' in response['Location']
