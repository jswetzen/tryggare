"""
Settings for fast, self-contained unit tests.

Unlike ``config.settings.test`` (which targets the live dev Postgres for
Selenium E2E), this module uses an isolated SQLite database, an in-memory
channel layer (no Redis), and a local-memory cache — so `manage.py test` runs
with no external services. Override DJANGO_SETTINGS_MODULE to use it.
"""

import os

os.environ.setdefault("SECRET_KEY", "insecure-unit-test-key")
# Force the SQLite fallback in base._database_config(): set DATABASE_URL empty
# *before* importing base. base.py calls load_dotenv(), which does not override
# an already-set env var, so this wins over any .env value.
os.environ["DATABASE_URL"] = ""

from .base import *  # noqa

# base._database_config() returns SQLite (db.sqlite3) when DATABASE_URL is empty;
# pin it to an in-memory database for speed and isolation.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# AllowedHostsOriginValidator rejects connections with no Origin header unless
# "*" is in ALLOWED_HOSTS. WebsocketCommunicator in tests sends no Origin header,
# so we must allow all hosts here. This overrides any .env value loaded by base.py.
ALLOWED_HOSTS = ["*"]

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
