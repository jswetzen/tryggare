from .base import *  # noqa

DEBUG = False

# Require SECRET_KEY to be explicitly set in production
if SECRET_KEY == "insecure-change-me":
    raise ValueError(
        "SECRET_KEY must be set to a secure value in production. "
        "Generate one with: openssl rand -hex 32"
    )
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Require FRONTEND_BASE_URL to be explicitly set to an absolute URL in
# production. base.py already applied its dev-only default
# ("http://localhost:5173") before this module runs, so by the time we get
# here the value is either what the operator set or the empty string that
# docker-compose.portainer.yml forwards for an unset env var — never
# "unset". Links emailed to registrants (verification, payment status) have
# no browser origin to resolve against, unlike the Django admin, so a
# missing/relative value fails silently in exactly the place it matters most.
if not FRONTEND_BASE_URL or not FRONTEND_BASE_URL.startswith(("http://", "https://")):
    raise ValueError(
        "FRONTEND_BASE_URL must be set to the absolute URL of the frontend "
        "(e.g. https://app.example.com) in production. Emailed links "
        "(registration verification, payment status) are built from this "
        "value with no other origin to resolve against, so leaving it "
        "unset or non-absolute silently ships broken links."
    )

# Allow overriding via env vars (base.py already reads these, but prod defaults to True)
# For HTTPS/reverse proxy: set both to true
# For HTTP testing: set both to false
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "true").lower() == "true"
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "true").lower() == "true"

ALLOWED_HOSTS = [host for host in os.getenv("ALLOWED_HOSTS", "").split(",") if host]

# Security Headers
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "false").lower() == "true"

# Clickjacking protection
X_FRAME_OPTIONS = "DENY"

# MIME-type sniffing protection
SECURE_CONTENT_TYPE_NOSNIFF = True

# XSS protection
SECURE_BROWSER_XSS_FILTER = True

# Session security
SESSION_COOKIE_SAMESITE = "Strict"  # Override base.py
CSRF_COOKIE_SAMESITE = "Strict"
SESSION_COOKIE_AGE = 28800  # 8 hours
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
