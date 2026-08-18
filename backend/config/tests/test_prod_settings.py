"""
Tests for config.settings.prod's fail-fast startup checks.

config.settings.prod raises ValueError at *import time* when misconfigured
(same pattern as its existing SECRET_KEY check), so it can't be exercised via
Django's already-configured settings object -- the active test run uses
config.settings.local/unit, not prod. Instead we reload the real module under
a patched environment and assert on what happens during that reload.
"""

import importlib
import os
from unittest.mock import patch

from django.test import SimpleTestCase

import config.settings.base as base_settings
import config.settings.prod as prod_settings

# A SECRET_KEY that isn't the "insecure-change-me" default, so these tests
# exercise the FRONTEND_BASE_URL check and not the pre-existing SECRET_KEY one.
VALID_SECRET_KEY = "a-real-secret-key-for-this-test"


class FrontendBaseUrlProdSettingsTests(SimpleTestCase):
    """FRONTEND_BASE_URL must be an absolute http(s) URL in prod settings."""

    def tearDown(self):
        # Reloading config.settings.base/prod is process-global (they're
        # cached in sys.modules). Put both back to reflect the real
        # environment again so later tests don't see values left over from
        # a patched os.environ.
        importlib.reload(base_settings)
        importlib.reload(prod_settings)

    def _reload_prod_with_env(self, frontend_base_url):
        """Reload base then prod under a patched os.environ.

        prod.py does `from .base import *`, which only copies the *current*
        attributes off the already-imported base module. base must be
        reloaded first so FRONTEND_BASE_URL (computed in base.py from
        os.environ) reflects the patched value before prod re-derives its
        check from it.
        """
        env = {"SECRET_KEY": VALID_SECRET_KEY, "FRONTEND_BASE_URL": frontend_base_url}
        with patch.dict(os.environ, env, clear=False):
            importlib.reload(base_settings)
            return importlib.reload(prod_settings)

    def test_rejects_empty_frontend_base_url(self):
        with self.assertRaisesMessage(ValueError, "FRONTEND_BASE_URL"):
            self._reload_prod_with_env("")

    def test_rejects_non_absolute_frontend_base_url(self):
        with self.assertRaisesMessage(ValueError, "FRONTEND_BASE_URL"):
            self._reload_prod_with_env("localhost:8080")

    def test_rejects_protocol_relative_frontend_base_url(self):
        with self.assertRaisesMessage(ValueError, "FRONTEND_BASE_URL"):
            self._reload_prod_with_env("//localhost:8080")

    def test_accepts_valid_https_frontend_base_url(self):
        module = self._reload_prod_with_env("https://app.example.com")
        self.assertEqual(module.FRONTEND_BASE_URL, "https://app.example.com")

    def test_accepts_valid_http_frontend_base_url(self):
        module = self._reload_prod_with_env("http://localhost:8080")
        self.assertEqual(module.FRONTEND_BASE_URL, "http://localhost:8080")
