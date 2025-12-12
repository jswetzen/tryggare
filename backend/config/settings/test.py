"""
Test settings for Selenium and other E2E tests.

E2E tests use the live development database since they interact with running
frontend/backend services via Selenium. Test cleanup ensures data isolation.
"""

from .base import *  # noqa

# E2E tests use the same database as the dev environment
# since they test against the running frontend/backend services.
# Tests use unique test data and comprehensive cleanup to avoid conflicts.
# For unit/integration tests, pytest-django can use --reuse-db or transactions.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "checkins"),
        "USER": os.getenv("POSTGRES_USER", "postgres"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "postgres"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": int(os.getenv("POSTGRES_PORT", "5432")),
        "ATOMIC_REQUESTS": False,
    }
}

# Use in-memory channel layer for testing (faster, no Redis needed)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}

# Don't send real emails during tests
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Use faster password hashing for tests (significantly speeds up user creation)
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# In-memory cache for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Debug should be False in tests to catch issues that would appear in production
DEBUG = True  # Keep True for better error messages during test development

# Disable migrations for faster test database creation
# Uncomment if tests become slow:
# class DisableMigrations:
#     def __contains__(self, item):
#         return True
#     def __getitem__(self, item):
#         return None
# MIGRATION_MODULES = DisableMigrations()
