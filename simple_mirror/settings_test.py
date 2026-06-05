"""Test settings: extends base settings with accounts app and testcontainers DB."""
import threading

from simple_mirror.settings import *  # noqa: F401, F403

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'mirror',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

TEMPLATES[0]['OPTIONS']['context_processors'] += [  # noqa: F405
    'django.contrib.auth.context_processors.auth',
    'django.contrib.messages.context_processors.messages',
]

AUTH_USER_MODEL = 'accounts.User'

SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# OTP / Email constants
OTP_LIFETIME_SECONDS: int = 60
EMAIL_OTP_MAX_RETRIES: int = 3
EMAIL_OTP_RETRY_DELAY: float = 0.5
EMAIL_OTP_THREAD_POOL_SIZE: int = 4

EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
DEFAULT_FROM_EMAIL = 'noreply@example.com'
