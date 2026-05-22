"""
Settings for E2E tests that run against live development servers.

This configuration uses the same database as the development environment
but with special test user management to avoid conflicts.
"""

from .local import *  # noqa

# Inherit all settings from local development
# This ensures we use the same database, Redis, etc. as the running servers

# Use faster password hashing for tests (significantly speeds up user creation)
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Keep debug enabled for better error messages
DEBUG = True
