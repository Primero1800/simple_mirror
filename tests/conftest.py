"""Root conftest: infra mocks and shared fixtures available to all tests."""
import threading
import pytest
from datetime import datetime, timedelta
from django.utils.translation import activate
from testcontainers.postgres import PostgresContainer


# ── Database ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope='session')
def django_db_setup(django_test_environment, django_db_blocker):
    """Spin up a real PostgreSQL container for the entire test session.

    Overrides settings.DATABASES and resets Django's thread-local connection
    cache so all subsequent queries use the container instead of the configured
    host.
    """
    with PostgresContainer('postgres:16-alpine') as pg:
        from django.conf import settings
        from django.db import connections

        # 1. Point Django at the fresh container (include all keys Django requires)
        settings.DATABASES['default'] = {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': pg.dbname,
            'USER': pg.username,
            'PASSWORD': pg.password,
            'HOST': pg.get_container_host_ip(),
            'PORT': pg.get_exposed_port(5432),
            'TIME_ZONE': None,
            'AUTOCOMMIT': True,
            'ATOMIC_REQUESTS': False,
            'CONN_MAX_AGE': 0,
            'CONN_HEALTH_CHECKS': False,
            'OPTIONS': {},
            'TEST': {
                'CHARSET': None,
                'COLLATION': None,
                'MIGRATE': True,
                'MIRROR': None,
                'NAME': None,
            },
        }
        # 2. Wipe the thread-local cache so no stale wrapper survives
        connections._connections = threading.local()

        # 3. Run migrations against the clean container
        with django_db_blocker.unblock():
            from django.core.management import call_command
            call_command('migrate', verbosity=0)
        yield


@pytest.fixture(autouse=True)
def set_language_ru():
    """Activate Russian for every test so reverse() returns /ru/... URLs."""
    activate('ru')


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
