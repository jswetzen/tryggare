"""
Test settings for Selenium and other E2E tests.

This configuration ensures tests run in complete isolation from the development
database, preventing data loss and ensuring reproducible test results.
"""

from .base import *  # noqa

# Use a separate SQLite database for tests
# This will be automatically created and destroyed by Django's test runner
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "test_db.sqlite3",
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
        'BACKEND': 'django.core.cache.backends.locmem.LocMemBackend',
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
