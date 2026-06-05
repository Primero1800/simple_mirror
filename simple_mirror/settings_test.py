"""Test settings: extends base settings, overrides email backend."""
from simple_mirror.settings import *  # noqa: F401, F403

EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
DEFAULT_FROM_EMAIL = 'noreply@example.com'
