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
    "notifications",
    "registrations",
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
        # Deliberately loose, not the initially-considered 3/hour: on-site
        # bulk registration by one youth leader on shared venue wifi is a
        # normal workload for this product (see registrations/views.py).
        # Dedup + resend-cooldown on (event, contact_email) is the actual
        # abuse control, not this per-IP cap.
        "registration_submit": "30/hour",
        "registration_payment_status": "20/hour",
        # Live-typing validation while filling the form — looser than the
        # submit rate itself since one guardian may retype a code a few
        # times, but still bounded (this is also the only place an
        # unauthenticated caller can probe for valid promo codes).
        "registration_validate_promo_code": "60/hour",
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

# Swish/Bankgiro payee config (registrations/swish.py). Single-tenant,
# per-deployment — one congregation, one number each — matching the
# DATA_CONTROLLER_* pattern above rather than a DB-configurable multi-tenant
# field. Blank-safe: a deployment with no Swish number configured simply
# omits swish_url/swish_qr_data_url from payment instructions (Bankgiro-only).
SWISH_PAYEE_NUMBER = os.getenv("SWISH_PAYEE_NUMBER", "")
BANKGIRO_NUMBER = os.getenv("BANKGIRO_NUMBER", "")

# Version tag for the health-data consent notice shown at registration
# (Art. 9(2)(a)). Bump this whenever the notice text changes — existing
# consent records keep the version they were granted under (grandfathered);
# only new registrations see the new text. See Child.health_consent_notice_version.
HEALTH_CONSENT_NOTICE_VERSION = os.getenv("HEALTH_CONSENT_NOTICE_VERSION", "v2-2026-07")

# Demo mode also gates the notifications NullProvider fallback (see
# notifications/providers.py) — kept as a proper setting rather than a
# scattered os.getenv so it's overridable in tests. demo/apps.py's own
# scheduler still reads the env var directly; this doesn't replace that.
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

# Email sending (see notifications/providers.py). Deliberately optional —
# leaving EMAIL_HOST unset is a supported "no email" deployment mode (e.g.
# the public demo instance), not a misconfiguration. EMAIL_PROVIDER selects
# the implementation; "smtp" is the only one that exists today.
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "smtp")
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "")

# Base URL of the SvelteKit frontend, used to build links sent by email (e.g.
# the registration verification link) — these must resolve to the frontend's
# real routes even though the Django backend is on a different origin in dev
# (localhost:5173 vs :8000); in prod-like/production a single container
# serves both, so this is normally the same origin as the API.
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")

# Send-budget circuit breaker (see notifications/providers.py::SmtpProvider.send()).
# A burst from one feature (e.g. self-serve registration) must not exhaust the
# shared transactional channel that other features (consent-renewal mail) also
# depend on. Default cap is well under Simply.com's ~300msg/4h auto-suspend
# threshold, leaving headroom for other senders sharing the same window.
EMAIL_SEND_BUDGET_MAX = int(os.getenv("EMAIL_SEND_BUDGET_MAX", "200"))
EMAIL_SEND_BUDGET_WINDOW_HOURS = int(os.getenv("EMAIL_SEND_BUDGET_WINDOW_HOURS", "4"))

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
