import os

from .base import *  # noqa

DEBUG = True
ALLOWED_HOSTS = [host for host in os.getenv("ALLOWED_HOSTS", "*").split(",") if host]

# CORS settings for development (SvelteKit runs on port 5173)
if not CORS_ALLOWED_ORIGINS:
    CORS_ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
    CSRF_TRUSTED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
CORS_ALLOW_ALL_ORIGINS = False  # Explicitly set allowed origins for security

# Use in-memory channel layer for local development (no Redis needed)
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

# Static files - override base.py for dev mode to avoid conflict with MEDIA_URL
STATIC_URL = "/static/"  # In dev, use /static/ (production uses / for SvelteKit)

# Keep session-based authentication enabled in development
# Override base.py to allow unauthenticated access to public endpoints
# Individual views will use @permission_classes to control access
#
# DEFAULT_THROTTLE_RATES starts from base.py's own rates (**_base_throttle_rates)
# rather than a fully separate dict — a new scope added to base.py used to need
# a second, easy-to-forget edit here too, or any view using it 500s in dev with
# "No default throttle rate set" (hit this directly adding
# registration_validate_promo_code). Only the rates that are deliberately
# laxer in dev are listed explicitly below; everything else is inherited.
_base_throttle_rates = REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
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
    # Dev rates are intentionally lax so E2E suites running many logins in quick
    # succession don't get throttled. Production uses tighter rates from base.py.
    "DEFAULT_THROTTLE_RATES": {
        **_base_throttle_rates,
        "anon": "1000/minute",
        "user": "10000/minute",
        "login": "1000/minute",
        "registration_submit": "1000/minute",
        "registration_payment_status": "1000/minute",
        "registration_validate_promo_code": "1000/minute",
        "qr_safety_info_reveal": "1000/minute",
    },
}

# Local development is not a deployment: acknowledge the no-email state so the
# notifications startup check (notifications/apps.py) doesn't refuse to boot.
# pytest.ini points DJANGO_SETTINGS_MODULE here, so without this every local
# test run would fail at app-registry population. Real deployments must set
# EMAIL_HOST or EMAIL_DISABLED_ACK deliberately.
EMAIL_DISABLED_ACK = True
