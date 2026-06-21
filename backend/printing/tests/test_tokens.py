"""Tests for per-printer auth tokens: model lifecycle + provisioning API."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from printing.models import Printer

User = get_user_model()


class PrinterTokenModelTest(TestCase):
    def test_token_generated_on_create(self):
        printer = Printer.objects.create(name="P1")
        self.assertTrue(printer.token)
        self.assertTrue(printer.token_active)
        self.assertIsNone(printer.token_revoked_at)

    def test_tokens_are_unique(self):
        a = Printer.objects.create(name="A")
        b = Printer.objects.create(name="B")
        self.assertNotEqual(a.token, b.token)

    def test_rotate_changes_token_and_clears_revocation(self):
        printer = Printer.objects.create(name="P")
        old = printer.token
        printer.revoke_token()
        self.assertFalse(printer.token_active)

        new = printer.rotate_token()
        self.assertNotEqual(new, old)
        self.assertEqual(printer.token, new)
        self.assertTrue(printer.token_active)

    def test_revoke_marks_inactive(self):
        printer = Printer.objects.create(name="P")
        printer.revoke_token()
        printer.refresh_from_db()
        self.assertFalse(printer.token_active)
        self.assertIsNotNone(printer.token_revoked_at)


class PrinterProvisioningAPITest(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username="staff", password="pw")
        self.client = APIClient()
        self.client.force_authenticate(user=self.staff)

    def test_provision_returns_token_once(self):
        resp = self.client.post(
            "/api/printing/printers/provision/", {"name": "Foyer"}, format="json"
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["name"], "Foyer")
        self.assertIn("token", resp.data)
        self.assertTrue(resp.data["token"])

    def test_create_endpoint_also_returns_token(self):
        resp = self.client.post(
            "/api/printing/printers/", {"name": "Hall"}, format="json"
        )
        self.assertEqual(resp.status_code, 201)
        self.assertIn("token", resp.data)

    def test_list_omits_token(self):
        Printer.objects.create(name="P")
        resp = self.client.get("/api/printing/printers/")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data)
        self.assertNotIn("token", resp.data[0])
        self.assertIn("token_active", resp.data[0])

    def test_rotate_token_endpoint(self):
        printer = Printer.objects.create(name="P")
        old = printer.token
        resp = self.client.post(f"/api/printing/printers/{printer.id}/rotate-token/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("token", resp.data)
        self.assertNotEqual(resp.data["token"], old)

    def test_revoke_token_endpoint(self):
        printer = Printer.objects.create(name="P")
        resp = self.client.post(f"/api/printing/printers/{printer.id}/revoke-token/")
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("token", resp.data)
        printer.refresh_from_db()
        self.assertFalse(printer.token_active)

    def test_provision_requires_auth(self):
        anon = APIClient()
        resp = anon.post(
            "/api/printing/printers/provision/", {"name": "X"}, format="json"
        )
        self.assertIn(resp.status_code, (401, 403))

    def test_bootstrap_flow_via_session_login(self):
        """The printer-client's first-run path: log in, then provision a token.

        Mirrors bootstrap_token() in printer-client/client/__init__.py — a fresh
        session authenticates with staff credentials and provisions a printer.
        """
        session = APIClient()
        login = session.post(
            "/api/auth/login/",
            {"username": "staff", "password": "pw"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)

        resp = session.post(
            "/api/printing/printers/provision/", {"name": "Bootstrapped"}, format="json"
        )
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.data["token"])

        # The token actually authorises a printer (it maps to a live, active row).
        printer = Printer.objects.get(name="Bootstrapped")
        self.assertEqual(printer.token, resp.data["token"])
        self.assertTrue(printer.token_active)
