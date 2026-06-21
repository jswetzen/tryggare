"""Tests for GDPR features: retention anonymization, DSAR export/erasure, privacy endpoint."""

from datetime import date, timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from checkins.models import AuditLog, CheckInRecord
from events.models import Event, Session
from families.dsar import build_family_export
from families.models import Child, Family, Parent

User = get_user_model()


def _make_family(last_name, *, inactive_days=None):
    family = Family.objects.create(last_name=last_name)
    if inactive_days is not None:
        family.last_participation_date = timezone.now() - timedelta(days=inactive_days)
        family.save()
    Parent.objects.create(
        name="Jane Doe",
        phone="555-1234",
        email="jane@example.com",
        relationship_type="Mom",
        family=family,
    )
    child = Child.objects.create(
        first_name="Kid",
        last_name=last_name,
        birthdate=date(2018, 1, 1),
        allergies="Peanuts",
        notes="Needs inhaler",
        family=family,
    )
    return family, child


class AnonymizeExpiredDataTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username="staff", password="pw")
        self.event = Event.objects.create(
            name="Conf", start_date=date(2025, 1, 1), end_date=date(2025, 1, 2)
        )
        self.session = Session.objects.create(
            name="Morning",
            event=self.event,
            start_time="2025-01-01T09:00:00Z",
            end_time="2025-01-01T12:00:00Z",
        )

    @override_settings(DATA_RETENTION_DAYS=365)
    def test_anonymizes_inactive_family(self):
        family, child = _make_family("Old", inactive_days=400)
        # An audit log referencing the child, as written by check-in views.
        AuditLog.objects.create(
            user=self.staff,
            action="check_in",
            entity_type="CheckInRecord",
            entity_id="x",
            details={"child_id": str(child.id), "child_name": "Kid Old"},
        )

        call_command("anonymize_expired_data", stdout=StringIO())

        family.refresh_from_db()
        child.refresh_from_db()
        parent = family.parents.first()
        self.assertEqual(child.first_name, "REDACTED")
        self.assertIsNone(child.allergies)
        self.assertIsNone(child.notes)
        self.assertIsNotNone(child.anonymized_at)
        self.assertEqual(parent.name, "REDACTED")
        self.assertIsNone(parent.email)
        self.assertEqual(family.last_name, "REDACTED")

        log = AuditLog.objects.get(details__child_id=str(child.id))
        self.assertEqual(log.details["child_name"], "REDACTED")
        self.assertTrue(AuditLog.objects.filter(action="anonymize_retention").exists())

    @override_settings(DATA_RETENTION_DAYS=365)
    def test_leaves_recent_family_untouched(self):
        family, child = _make_family("Recent", inactive_days=10)
        call_command("anonymize_expired_data", stdout=StringIO())
        child.refresh_from_db()
        self.assertEqual(child.first_name, "Kid")
        self.assertIsNone(child.anonymized_at)

    @override_settings(DATA_RETENTION_DAYS=365)
    def test_never_anonymizes_checked_in_child(self):
        family, child = _make_family("Active", inactive_days=400)
        CheckInRecord.objects.create(
            child=child, session=self.session, check_in_staff=self.staff
        )  # no check_out_time => active
        call_command("anonymize_expired_data", stdout=StringIO())
        child.refresh_from_db()
        self.assertEqual(child.first_name, "Kid")

    @override_settings(DATA_RETENTION_DAYS=365)
    def test_dry_run_writes_nothing(self):
        family, child = _make_family("Old", inactive_days=400)
        call_command("anonymize_expired_data", "--dry-run", stdout=StringIO())
        child.refresh_from_db()
        self.assertEqual(child.first_name, "Kid")
        self.assertFalse(AuditLog.objects.filter(action="anonymize_retention").exists())

    @override_settings(DATA_RETENTION_DAYS=365)
    def test_idempotent(self):
        family, child = _make_family("Old", inactive_days=400)
        call_command("anonymize_expired_data", stdout=StringIO())
        # Second run should not pick the already-anonymized family up again.
        call_command("anonymize_expired_data", stdout=StringIO())
        self.assertEqual(
            AuditLog.objects.filter(action="anonymize_retention").count(), 2
        )
        batches = AuditLog.objects.filter(action="anonymize_retention").order_by(
            "timestamp"
        )
        self.assertEqual(batches.last().details["families_anonymized"], 0)


class DSARTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username="staff", password="pw")
        self.client = APIClient()
        self.client.force_authenticate(user=self.staff)

    def test_export_contains_nested_data(self):
        family, child = _make_family("Export")
        export = build_family_export(family)
        self.assertEqual(export["last_name"], "Export")
        self.assertEqual(len(export["children"]), 1)
        self.assertEqual(len(export["parents"]), 1)
        self.assertIn("checkin_history", export)
        self.assertIn("audit_logs", export)

    def test_export_endpoint_logs_action(self):
        family, child = _make_family("Export")
        resp = self.client.get(f"/api/families/{family.id}/export/")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(AuditLog.objects.filter(action="dsar_export").exists())

    def test_export_csv(self):
        family, child = _make_family("Export")
        resp = self.client.get(f"/api/families/{family.id}/export/?as=csv")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/csv")

    def test_erase_deletes_and_logs(self):
        family, child = _make_family("Erase")
        AuditLog.objects.create(
            user=self.staff,
            action="check_in",
            entity_type="CheckInRecord",
            entity_id="x",
            details={"child_id": str(child.id), "child_name": "Kid Erase"},
        )
        resp = self.client.post(f"/api/families/{family.id}/erase/")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["erased"])
        self.assertFalse(Family.objects.filter(id=family.id).exists())
        # Erasure logged before deletion; child audit PII scrubbed.
        self.assertTrue(AuditLog.objects.filter(action="dsar_erasure").exists())
        scrubbed = AuditLog.objects.get(details__child_id=str(child.id))
        self.assertEqual(scrubbed.details["child_name"], "REDACTED")


class PrivacyEndpointTests(TestCase):
    @override_settings(
        DATA_CONTROLLER_NAME="Test Org",
        DATA_CONTROLLER_CONTACT_EMAIL="dpo@test.org",
        DATA_RETENTION_DAYS=730,
    )
    def test_privacy_info_public(self):
        client = APIClient()  # unauthenticated
        resp = client.get("/api/privacy/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["controller_name"], "Test Org")
        self.assertEqual(resp.data["contact_email"], "dpo@test.org")
        self.assertEqual(resp.data["retention_days"], 730)
