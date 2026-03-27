from .base import *  # noqa

DEBUG = False

# Require SECRET_KEY to be explicitly set in production
if SECRET_KEY == "insecure-change-me":
    raise ValueError(
        "SECRET_KEY must be set to a secure value in production. "
        "Generate one with: openssl rand -hex 32"
    )
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

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
