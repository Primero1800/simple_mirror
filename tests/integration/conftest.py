"""Integration conftest: session helpers for endpoint tests."""
import pytest


@pytest.fixture
def pending_session(client, db, inactive_user, otp_for_user):
    """Client with a pending_user_id session (simulates post-credential step)."""
    otp_for_user(inactive_user)
    session = client.session
    session['pending_user_id'] = inactive_user.pk
    session['otp_purpose'] = 'register'
    session.save()
    return client, inactive_user


@pytest.fixture
def auth_client(client, db, active_user):
    """Client authenticated as *active_user*."""
    client.force_login(active_user)
    return client, active_user
