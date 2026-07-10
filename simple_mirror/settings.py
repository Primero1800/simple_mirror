import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-sm1rr0r-x7k2p9q4n8v3j6w5t1y0u8i3o6l4a9s2d5f8g1h7b0c",
)

DEBUG = os.environ.get("DEBUG", "True").lower() == "true"

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "mirror",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "simple_mirror.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "simple_mirror.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": os.environ.get("DB_ENGINE", "django.db.backends.postgresql"),
        "NAME": os.environ.get("POSTGRES_DB", "mirror"),
        "USER": os.environ.get("POSTGRES_USER", "postgres"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

AUTH_USER_MODEL = "accounts.User"

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 180  # 6 months
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

USE_TZ = False

# ── i18n ───────────────────────────────────────────────────────────────────────
USE_I18N = True
LANGUAGE_CODE = "ru"
LANGUAGES = [
    ("ru", "Русский"),
    ("en", "English"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]

# ── Redis ──────────────────────────────────────────────────────────────────────
REDIS_HOST: str = os.environ.get("REDIS_HOST", "127.0.0.1")
REDIS_PORT: int = int(os.environ.get("REDIS_PORT", "6379"))
_REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}"

CACHES = {
    # Sessions live here; also used by @cache_page / {% cache %} when added later.
    # Explicit timeout always wins over this default, so mixing uses is safe.
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"{_REDIS_URL}/0",
        "TIMEOUT": 60 * 60 * 24 * 180,  # 6 months (matches SESSION_COOKIE_AGE)
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
            "CONNECTION_POOL_KWARGS": {
                "socket_timeout": 1,
                "socket_connect_timeout": 1,
            },
        },
        "KEY_PREFIX": "mirror",
    },
    # OTP attempt counters (otp_attempts::{email}) and resend cooldowns
    # (otp_cooldown::{email}). Default TTL covers attempt counters; cooldowns
    # always pass an explicit timeout=30 at write time.
    "otp": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"{_REDIS_URL}/1",
        "TIMEOUT": 60 * 60 * 24,  # 24 h — attempt counters double as the block
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "socket_timeout": 1,
                "socket_connect_timeout": 1,
            },
        },
        "KEY_PREFIX": "mirror",
    },
}

# ── OTP ────────────────────────────────────────────────────────────────────────
OTP_LIFETIME_SECONDS: int = int(os.environ.get("OTP_LIFETIME_SECONDS", 60))
OTP_MAX_ATTEMPTS: int = int(os.environ.get("OTP_MAX_ATTEMPTS", 0))
OTP_RESEND_COOLDOWN_SECONDS: int = int(os.environ.get("OTP_RESEND_COOLDOWN_SECONDS", 0))
OTP_CACHE_KEY_SEPARATOR: str = "::"
OTP_ATTEMPTS_KEY_PREFIX: str = "otp_attempts"
OTP_COOLDOWN_KEY_PREFIX: str = "otp_cooldown"

# ── Login brute-force ──────────────────────────────────────────────────────────
LOGIN_MAX_ATTEMPTS: int = int(os.environ.get("LOGIN_MAX_ATTEMPTS", 5))
LOGIN_ATTEMPTS_KEY_PREFIX: str = "login_attempts"

# ── Email ──────────────────────────────────────────────────────────────────────
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "25"))
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "False").lower() == "true"
EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "False").lower() == "true"
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER or "noreply@example.com"
EMAIL_TIMEOUT: int = int(os.environ.get("EMAIL_TIMEOUT", 5))

EMAIL_MAX_RETRIES: int = int(os.environ.get("EMAIL_MAX_RETRIES", 3))
EMAIL_RETRY_DELAY: float = float(os.environ.get("EMAIL_RETRY_DELAY", 0.5))
EMAIL_THREAD_POOL_SIZE: int = int(os.environ.get("EMAIL_THREAD_POOL_SIZE", 4))

DJANGO_REDIS_LOG_IGNORED_EXCEPTIONS = True

# ── Logging ────────────────────────────────────────────────────────────────────
# Fill ADMINS to receive error emails on production (requires DEBUG=False).
ADMINS: list[tuple[str, str]] = []

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_debug_false": {"()": "django.utils.log.RequireDebugFalse"},
        "require_debug_true": {"()": "django.utils.log.RequireDebugTrue"},
    },
    "formatters": {
        "django.server": {
            "()": "django.utils.log.ServerFormatter",
            "format": "[{server_time}] {message}",
            "style": "{",
        },
        "simple": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "datefmt": "%Y.%m.%d %H:%M:%S",
            "style": "{",
        },
    },
    "handlers": {
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "filename": BASE_DIR / "logging" / "logs.log",
            "maxBytes": 1_048_576,
            "backupCount": 10,
            "formatter": "simple",
        },
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "filters": ["require_debug_true"],
            "formatter": "django.server",
        },
        "mail_admins": {
            "class": "django.utils.log.AdminEmailHandler",
            "level": "ERROR",
            "filters": ["require_debug_false"],
        },
        "django.server": {
            "class": "logging.StreamHandler",
            "level": "WARNING",
            "formatter": "django.server",
        },
    },
    "loggers": {
        # Root logger — catches all our app loggers (accounts.*, mirror.*, etc.)
        "": {
            "handlers": ["file", "console", "mail_admins"],
            "level": "INFO",
        },
        # Django internals — same destinations, propagate=False prevents duplicate writes
        "django": {
            "handlers": ["file", "console", "mail_admins"],
            "propagate": False,
        },
        # Dev-server access log — separate handler only, no file spam
        "django.server": {
            "handlers": ["django.server"],
            "propagate": False,
        },
    },
}
