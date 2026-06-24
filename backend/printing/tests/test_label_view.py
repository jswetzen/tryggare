"""
Regression tests for label_page_view (GET /print-job/<uuid>/label/).

Covers the family auto-print bug: when a whole family is checked in, the printer
renders labels one at a time and a job can reach a terminal status (FAILED retry,
stale/duplicate completion, reconnect re-delivery) before its label is fetched.
The label endpoint must NOT 404 in that case — the label is a pure rendering of
the check-in and must stay fetchable while the child is checked in.
"""

import datetime
import uuid

from django.test import TestCase
from django.utils import timezone

from accounts.models import AdminUser
from checkins.models import CheckInRecord, QRCode
from events.models import Event, Session
from families.models import Child, Family
from printing.models import Printer, PrintJob


class LabelPageViewTest(TestCase):
    def setUp(self):
        self.user = AdminUser.objects.create_user(
            username="labeltest", password="pass123", name="Label Tester"
        )
        self.family = Family.objects.create()
        self.child = Child.objects.create(
            family=self.family, first_name="Alice", last_name="Smith"
        )
        self.event = Event.objects.create(
            name="Conf",
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
        )
        self.session = Session.objects.create(
            name="Morning",
            start_time=timezone.now(),
            end_time=timezone.now() + datetime.timedelta(hours=3),
            is_active=True,
            event=self.event,
        )
        self.printer = Printer.objects.create(id=uuid.uuid4(), name="P", is_online=True)
        self.checkin = CheckInRecord.objects.create(
            child=self.child, session=self.session, check_in_staff=self.user
        )
        QRCode.objects.create(code="AB12C", checkin_record=self.checkin)

    def _label_status(self, job):
        return self.client.get(f"/print-job/{job.id}/label/?label=29x90").status_code

    def test_label_fetchable_for_every_job_status_while_checked_in(self):
        job = PrintJob.objects.create(checkin=self.checkin, printer=self.printer)
        for status in (
            PrintJob.STATUS_PENDING,
            PrintJob.STATUS_SENT,
            PrintJob.STATUS_COMPLETED,  # this 404'd before the fix
            PrintJob.STATUS_FAILED,  # this 404'd before the fix
        ):
            PrintJob.objects.filter(pk=job.id).update(status=status)
            self.assertEqual(
                self._label_status(job),
                200,
                msg=f"label should render for status={status}",
            )

    def test_label_404s_after_checkout(self):
        """Privacy guard: a checked-out child's label is no longer served."""
        job = PrintJob.objects.create(
            checkin=self.checkin,
            printer=self.printer,
            status=PrintJob.STATUS_COMPLETED,
        )
        self.assertEqual(self._label_status(job), 200)

        self.checkin.check_out_time = timezone.now()
        self.checkin.save()
        self.assertEqual(self._label_status(job), 404)

    def test_label_404s_for_unknown_job(self):
        self.assertEqual(
            self.client.get(
                f"/print-job/{uuid.uuid4()}/label/?label=29x90"
            ).status_code,
            404,
        )
