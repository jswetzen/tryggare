import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env_file = os.getenv("ENV_FILE")
if env_file:
    load_dotenv(env_file)
else:
    load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY", "insecure-change-me")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = [host for host in os.getenv("ALLOWED_HOSTS", "*").split(",") if host]
# Add testserver for Django test client
if not ALLOWED_HOSTS or ALLOWED_HOSTS == ["*"]:
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS.append("testserver")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "django_filters",
    "channels",
    "accounts",
    "families",
    "events",
    "checkins",
    "printing",
    "imports",
    "reports",
    "demo",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Serve static files
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",  # i18n language detection
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
            BASE_DIR / "staticfiles",  # For SPA index.html
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

ASGI_APPLICATION = "config.asgi.application"
WSGI_APPLICATION = "config.wsgi.application"


def _database_config():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        # Default to SQLite if no DATABASE_URL is set
        # Tests should use config.settings.test which overrides this
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }

    parsed = urlparse(database_url)
    if parsed.scheme.startswith("postgres"):
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/"),
            "USER": parsed.username,
            "PASSWORD": parsed.password,
            "HOST": parsed.hostname,
            "PORT": parsed.port or "5432",
        }

    raise ValueError("Unsupported DATABASE_URL scheme")


databases_default = _database_config()
DATABASES = {"default": databases_default}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en"
LANGUAGES = [
    ("en", "English"),
    ("sv", "Swedish"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = "/"  # Serve static files from root (/_app/, /admin/, etc.)
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"  # User-uploaded files (different from static)

# WhiteNoise configuration for static files
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.AdminUser"

CORS_ALLOWED_ORIGINS = [
    host for host in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if host
]
CORS_ALLOW_CREDENTIALS = True  # Allow cookies in cross-origin requests
CSRF_TRUSTED_ORIGINS = [
    host for host in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if host
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "10/minute",  # Anonymous users
        "user": "100/minute",  # Authenticated users
        "login": "5/minute",  # Login attempts
    },
}

# GDPR / data-protection settings
#
# Tryggare is self-hosted: each operator is the data controller and is
# responsible for filling in these values (privacy page and DSAR responses
# read them). Defaults are intentionally empty so an unconfigured deployment
# is obviously unconfigured rather than silently wrong.
#
# Retention is enforced by the `anonymize_expired_data` management command,
# which runs automatically once a day (see families/apps.py's in-app
# apscheduler job) — no operator cron needed. It anonymises PII on families
# that have been inactive (by last_participation_date) for longer than
# DATA_RETENTION_DAYS, keeping rows/timestamps for safeguarding/aggregate
# integrity. Audit logs grow forever unless pruned with --include-audit-logs
# (the scheduled run passes this flag).
DATA_RETENTION_DAYS = int(os.getenv("DATA_RETENTION_DAYS", "1095"))  # 3 years
AUDIT_LOG_RETENTION_DAYS = int(os.getenv("AUDIT_LOG_RETENTION_DAYS", "1095"))

DATA_CONTROLLER_NAME = os.getenv("DATA_CONTROLLER_NAME", "")
DATA_CONTROLLER_CONTACT_EMAIL = os.getenv("DATA_CONTROLLER_CONTACT_EMAIL", "")
DATA_CONTROLLER_URL = os.getenv("DATA_CONTROLLER_URL", "")
PRIVACY_POLICY_URL = os.getenv("PRIVACY_POLICY_URL", "")

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [os.getenv("VALKEY_URL", "redis://valkey:6379/0")],
        },
    }
}

# Session and CSRF cookie settings
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to session cookie

CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "false").lower() == "true"
CSRF_COOKIE_SAMESITE = os.getenv("CSRF_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_HTTPONLY = False  # Allow JavaScript to read CSRF token
CSRF_USE_SESSIONS = False  # Use cookie-based CSRF tokens
CSRF_COOKIE_NAME = "csrftoken"
