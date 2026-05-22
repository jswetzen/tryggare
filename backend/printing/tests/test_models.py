"""
Unit tests for printing models: Printer and PrintJob.
"""

import uuid
from django.test import TestCase
from django.utils import timezone

from accounts.models import AdminUser
from checkins.models import CheckInRecord
from events.models import Event, Session
from families.models import Child, Family
from printing.models import Printer, PrintJob


class PrinterModelTest(TestCase):
    """Tests for the Printer model."""

    def test_create_printer(self):
        printer_id = uuid.uuid4()
        printer = Printer.objects.create(
            id=printer_id,
            name="Test Printer",
            is_online=True,
        )
        self.assertEqual(printer.name, "Test Printer")
        self.assertTrue(printer.is_online)
        self.assertEqual(str(printer.id), str(printer_id))

    def test_printer_default_offline(self):
        printer = Printer.objects.create(id=uuid.uuid4(), name="Offline Printer")
        self.assertFalse(printer.is_online)

    def test_printer_str(self):
        printer = Printer.objects.create(
            id=uuid.uuid4(), name="My Printer", is_online=True
        )
        self.assertIn("My Printer", str(printer))
        self.assertIn("online", str(printer))

    def test_printer_str_offline(self):
        printer = Printer.objects.create(
            id=uuid.uuid4(), name="Old Printer", is_online=False
        )
        self.assertIn("offline", str(printer))


class PrintJobModelTest(TestCase):
    """Tests for the PrintJob model."""

    def setUp(self):
        self.user = AdminUser.objects.create_user(
            username="printtest", password="pass123", name="Print Tester"
        )
        self.family = Family.objects.create()
        self.child = Child.objects.create(
            family=self.family,
            first_name="Alice",
            last_name="Smith",
        )
        today = timezone.now().date()
        self.event = Event.objects.create(
            name="Test Event", start_date=today, end_date=today
        )
        self.session = Session.objects.create(
            event=self.event,
            name="Test Session",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=2),
        )
        self.checkin = CheckInRecord.objects.create(
            child=self.child,
            session=self.session,
            check_in_staff=self.user,
            label_printed=False,
        )
        self.printer = Printer.objects.create(
            id=uuid.uuid4(), name="Test Printer", is_online=True
        )

    def test_create_job_pending(self):
        job = PrintJob.objects.create(checkin=self.checkin)
        self.assertEqual(job.status, PrintJob.STATUS_PENDING)
        self.assertIsNone(job.printer)
        self.assertIsNone(job.sent_at)
        self.assertIsNone(job.completed_at)

    def test_create_job_with_printer(self):
        job = PrintJob.objects.create(checkin=self.checkin, printer=self.printer)
        self.assertEqual(job.printer, self.printer)
        self.assertEqual(job.status, PrintJob.STATUS_PENDING)

    def test_job_uuid_primary_key(self):
        job = PrintJob.objects.create(checkin=self.checkin)
        # UUID should be auto-generated
        self.assertIsNotNone(job.id)
        # Should be parseable as UUID
        uuid.UUID(str(job.id))

    def test_job_status_transitions(self):
        job = PrintJob.objects.create(checkin=self.checkin, printer=self.printer)
        self.assertEqual(job.status, PrintJob.STATUS_PENDING)

        job.status = PrintJob.STATUS_SENT
        job.sent_at = timezone.now()
        job.save()
        job.refresh_from_db()
        self.assertEqual(job.status, PrintJob.STATUS_SENT)
        self.assertIsNotNone(job.sent_at)

        job.status = PrintJob.STATUS_COMPLETED
        job.completed_at = timezone.now()
        job.save()
        job.refresh_from_db()
        self.assertEqual(job.status, PrintJob.STATUS_COMPLETED)
        self.assertIsNotNone(job.completed_at)

    def test_job_status_failed(self):
        job = PrintJob.objects.create(checkin=self.checkin, printer=self.printer)
        job.status = PrintJob.STATUS_FAILED
        job.save()
        job.refresh_from_db()
        self.assertEqual(job.status, PrintJob.STATUS_FAILED)

    def test_job_printer_null_on_printer_delete(self):
        """When printer is deleted, job.printer should become NULL (SET_NULL)."""
        job = PrintJob.objects.create(checkin=self.checkin, printer=self.printer)
        self.printer.delete()
        job.refresh_from_db()
        self.assertIsNone(job.printer)
        # Status should still be pending
        self.assertEqual(job.status, PrintJob.STATUS_PENDING)

    def test_job_deleted_on_checkin_delete(self):
        """When checkin is deleted, all related jobs should be deleted (CASCADE)."""
        job = PrintJob.objects.create(checkin=self.checkin)
        job_id = job.id
        self.checkin.delete()
        self.assertFalse(PrintJob.objects.filter(id=job_id).exists())

    def test_job_str(self):
        job = PrintJob.objects.create(checkin=self.checkin)
        self.assertIn("pending", str(job))


class PrintJobReassignmentTest(TestCase):
    """Tests for job reassignment logic on printer offline."""

    def setUp(self):
        self.user = AdminUser.objects.create_user(
            username="reassigntest", password="pass123", name="Reassign Tester"
        )
        self.family = Family.objects.create()
        self.child = Child.objects.create(
            family=self.family,
            first_name="Bob",
            last_name="Jones",
        )
        today = timezone.now().date()
        self.event = Event.objects.create(
            name="Reassign Event", start_date=today, end_date=today
        )
        self.session = Session.objects.create(
            event=self.event,
            name="Reassign Session",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=2),
        )
        self.printer = Printer.objects.create(
            id=uuid.uuid4(), name="Going Offline", is_online=True
        )

    def _make_checkin(self):
        return CheckInRecord.objects.create(
            child=self.child,
            session=self.session,
            check_in_staff=self.user,
            label_printed=False,
        )

    def test_reassign_pending_jobs_on_offline(self):
        """Pending/sent jobs should be unassigned when printer goes offline."""
        checkin1 = self._make_checkin()
        checkin2 = self._make_checkin()

        job1 = PrintJob.objects.create(
            checkin=checkin1, printer=self.printer, status=PrintJob.STATUS_PENDING
        )
        job2 = PrintJob.objects.create(
            checkin=checkin2, printer=self.printer, status=PrintJob.STATUS_SENT
        )

        # Simulate offline: mark offline and reassign
        self.printer.is_online = False
        self.printer.save()
        PrintJob.objects.filter(
            printer=self.printer,
            status__in=[PrintJob.STATUS_PENDING, PrintJob.STATUS_SENT],
        ).update(printer=None, status=PrintJob.STATUS_PENDING)

        job1.refresh_from_db()
        job2.refresh_from_db()
        self.assertIsNone(job1.printer)
        self.assertEqual(job1.status, PrintJob.STATUS_PENDING)
        self.assertIsNone(job2.printer)
        self.assertEqual(job2.status, PrintJob.STATUS_PENDING)

    def test_completed_jobs_not_reassigned_on_offline(self):
        """Completed jobs should not be touched when printer goes offline."""
        checkin = self._make_checkin()
        job = PrintJob.objects.create(
            checkin=checkin,
            printer=self.printer,
            status=PrintJob.STATUS_COMPLETED,
            sent_at=timezone.now(),
            completed_at=timezone.now(),
        )

        PrintJob.objects.filter(
            printer=self.printer,
            status__in=[PrintJob.STATUS_PENDING, PrintJob.STATUS_SENT],
        ).update(printer=None, status=PrintJob.STATUS_PENDING)

        job.refresh_from_db()
        # Completed jobs are not touched
        self.assertEqual(job.printer, self.printer)
        self.assertEqual(job.status, PrintJob.STATUS_COMPLETED)
