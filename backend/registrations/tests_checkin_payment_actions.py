"""Check-in screen's staff-facing payment actions (case catalog §9.3, "unpaid
at the door"): mark_registration_paid and confirm_registration_despite_balance
wrapped as authenticated API endpoints, reachable from the check-in UI
without an admin round-trip.
"""

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from checkins.models import AuditLog
from events.models import Event
from families.models import Family

from .models import Payment, Registration
from .tokens import generate_verification_token, hash_token


def _make_event(name="Weekend 2026", price=None):
    today = timezone.now().date()
    return Event.objects.create(
        name=name,
        start_date=today,
        end_date=today,
        price=price,
        registration_opens_at=timezone.now() - timezone.timedelta(days=1),
    )


def _make_pending_payment_registration(event, *, amount=Decimal("1500.00")):
    family = Family.objects.create(last_name="Test")
    registration = Registration.objects.create(
        event=event,
        family=family,
        contact_email="guardian@example.com",
        verification_token_hash=hash_token(generate_verification_token()),
        status=Registration.Status.PENDING_PAYMENT,
    )
    payment = Payment.objects.create(registration=registration, amount=amount)
    return registration, payment


class MarkRegistrationPaidViewTests(TestCase):
    def setUp(self):
        from accounts.models import AdminUser

        self.event = _make_event()
        self.staff = AdminUser.objects.create_superuser(
            username="checkin_staff", password="testpass123", name="Checkin Staff"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.staff)

    def test_requires_authentication(self):
        registration, _payment = _make_pending_payment_registration(self.event)
        anon_client = APIClient()

        response = anon_client.post(
            f"/api/registrations/{registration.id}/mark-paid/", {"method": "swish"}
        )

        self.assertEqual(response.status_code, 403)

    def test_marks_full_balance_paid_and_confirms_registration(self):
        registration, payment = _make_pending_payment_registration(self.event)

        response = self.client.post(
            f"/api/registrations/{registration.id}/mark-paid/", {"method": "swish"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], Registration.Status.CONFIRMED)

        registration.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(registration.status, Registration.Status.CONFIRMED)
        self.assertEqual(payment.status, Payment.Status.PAID)
        self.assertEqual(payment.balance, Decimal("0.00"))
        self.assertEqual(payment.method, Payment.Method.SWISH)
        self.assertEqual(payment.marked_by, self.staff)

    def test_writes_audit_log(self):
        registration, _payment = _make_pending_payment_registration(self.event)

        self.client.post(
            f"/api/registrations/{registration.id}/mark-paid/", {"method": "bankgiro"}
        )

        entry = AuditLog.objects.get(
            action="registration_payment_marked_paid", entity_id=str(registration.id)
        )
        self.assertEqual(entry.details["method"], "bankgiro")
        self.assertEqual(entry.details["source"], "checkin_ui")

    def test_unknown_method_rejected(self):
        registration, _payment = _make_pending_payment_registration(self.event)

        response = self.client.post(
            f"/api/registrations/{registration.id}/mark-paid/", {"method": "bitcoin"}
        )

        self.assertEqual(response.status_code, 400)
        registration.refresh_from_db()
        self.assertEqual(registration.status, Registration.Status.PENDING_PAYMENT)

    def test_registration_not_pending_payment_rejected(self):
        registration, payment = _make_pending_payment_registration(self.event)
        registration.status = Registration.Status.CONFIRMED
        registration.save(update_fields=["status"])

        response = self.client.post(
            f"/api/registrations/{registration.id}/mark-paid/", {"method": "swish"}
        )

        self.assertEqual(response.status_code, 400)

    def test_registration_without_payment_rejected(self):
        family = Family.objects.create(last_name="NoPayment")
        registration = Registration.objects.create(
            event=self.event,
            family=family,
            contact_email="guardian@example.com",
            verification_token_hash=hash_token(generate_verification_token()),
            status=Registration.Status.PENDING_PAYMENT,
        )

        response = self.client.post(
            f"/api/registrations/{registration.id}/mark-paid/", {"method": "swish"}
        )

        self.assertEqual(response.status_code, 400)

    def test_missing_registration_404s(self):
        import uuid

        response = self.client.post(
            f"/api/registrations/{uuid.uuid4()}/mark-paid/", {"method": "swish"}
        )

        self.assertEqual(response.status_code, 404)


class ConfirmDespiteBalanceViewTests(TestCase):
    def setUp(self):
        from accounts.models import AdminUser

        self.event = _make_event()
        self.staff = AdminUser.objects.create_superuser(
            username="checkin_staff2", password="testpass123", name="Checkin Staff 2"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.staff)

    def test_requires_authentication(self):
        registration, _payment = _make_pending_payment_registration(self.event)
        anon_client = APIClient()

        response = anon_client.post(
            f"/api/registrations/{registration.id}/confirm-despite-balance/"
        )

        self.assertEqual(response.status_code, 403)

    def test_confirms_registration_leaving_balance_outstanding(self):
        registration, payment = _make_pending_payment_registration(self.event)

        response = self.client.post(
            f"/api/registrations/{registration.id}/confirm-despite-balance/"
        )

        self.assertEqual(response.status_code, 200)
        registration.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(registration.status, Registration.Status.CONFIRMED)
        # The balance is untouched — this is a staff judgment call, not a
        # payment event.
        self.assertEqual(payment.status, Payment.Status.PENDING)
        self.assertEqual(payment.balance, Decimal("1500.00"))

    def test_writes_audit_log(self):
        registration, _payment = _make_pending_payment_registration(self.event)

        self.client.post(
            f"/api/registrations/{registration.id}/confirm-despite-balance/"
        )

        entry = AuditLog.objects.get(
            action="registration_confirmed_despite_balance",
            entity_id=str(registration.id),
        )
        self.assertEqual(entry.details["source"], "checkin_ui")

    def test_registration_not_pending_payment_rejected(self):
        registration, _payment = _make_pending_payment_registration(self.event)
        registration.status = Registration.Status.CANCELLED
        registration.save(update_fields=["status"])

        response = self.client.post(
            f"/api/registrations/{registration.id}/confirm-despite-balance/"
        )

        self.assertEqual(response.status_code, 400)
