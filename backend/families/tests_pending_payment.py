"""9.3 "unpaid at the door": FamilySerializer/FamilyDetailSerializer's
`pending_payment` field, which gives the check-in screen the amount owed for
a family with a pending_payment registration — see
docs/roadmap/event_registration_ux_case_catalog.md §9.3.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from events.models import Event
from families.models import Family
from registrations.models import Payment, PaymentEvent, Registration
from registrations.tokens import generate_verification_token, hash_token
from accounts.roles import COORDINATOR, grant

User = get_user_model()


def _make_event(name="Weekend 2026", price=None):
    today = timezone.now().date()
    return Event.objects.create(
        name=name,
        start_date=today,
        end_date=today,
        price=price,
        registration_opens_at=timezone.now() - timezone.timedelta(days=1),
    )


class PendingPaymentFieldTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="staff", password="testpass")
        self.client = APIClient()
        grant(self.user, COORDINATOR)
        self.client.force_authenticate(user=self.user)
        self.event = _make_event()

    def test_family_without_registration_has_no_pending_payment(self):
        family = Family.objects.create(last_name="NoReg")

        response = self.client.get("/api/families/")

        self.assertEqual(response.status_code, 200)
        row = next(f for f in response.data if f["id"] == str(family.id))
        self.assertIsNone(row["pending_payment"])

    def test_confirmed_registration_has_no_pending_payment(self):
        family = Family.objects.create(last_name="Confirmed")
        registration = Registration.objects.create(
            event=self.event,
            family=family,
            contact_email="guardian@example.com",
            verification_token_hash=hash_token(generate_verification_token()),
            status=Registration.Status.CONFIRMED,
        )
        Payment.objects.create(
            registration=registration,
            amount=Decimal("500.00"),
            status=Payment.Status.PAID,
        )

        response = self.client.get("/api/families/")

        row = next(f for f in response.data if f["id"] == str(family.id))
        self.assertIsNone(row["pending_payment"])

    def test_pending_payment_registration_surfaces_amount_owed(self):
        family = Family.objects.create(last_name="Owes")
        registration = Registration.objects.create(
            event=self.event,
            family=family,
            contact_email="guardian@example.com",
            verification_token_hash=hash_token(generate_verification_token()),
            status=Registration.Status.PENDING_PAYMENT,
        )
        Payment.objects.create(registration=registration, amount=Decimal("1500.00"))

        response = self.client.get("/api/families/")

        row = next(f for f in response.data if f["id"] == str(family.id))
        self.assertIsNotNone(row["pending_payment"])
        self.assertEqual(
            row["pending_payment"]["registration_id"], str(registration.id)
        )
        self.assertEqual(
            row["pending_payment"]["reference_code"], registration.reference_code
        )
        self.assertEqual(row["pending_payment"]["amount_owed"], "1500.00")
        self.assertEqual(row["pending_payment"]["currency"], "SEK")

    def test_partial_payment_reduces_amount_owed(self):
        family = Family.objects.create(last_name="PartlyPaid")
        registration = Registration.objects.create(
            event=self.event,
            family=family,
            contact_email="guardian@example.com",
            verification_token_hash=hash_token(generate_verification_token()),
            status=Registration.Status.PENDING_PAYMENT,
        )
        payment = Payment.objects.create(
            registration=registration, amount=Decimal("1500.00")
        )
        PaymentEvent.objects.create(
            payment=payment, kind=PaymentEvent.Kind.RECEIVED, amount=Decimal("1000.00")
        )

        response = self.client.get("/api/families/")

        row = next(f for f in response.data if f["id"] == str(family.id))
        self.assertEqual(row["pending_payment"]["amount_owed"], "500.00")

    def test_family_detail_endpoint_includes_pending_payment(self):
        family = Family.objects.create(last_name="Detail")
        registration = Registration.objects.create(
            event=self.event,
            family=family,
            contact_email="guardian@example.com",
            verification_token_hash=hash_token(generate_verification_token()),
            status=Registration.Status.PENDING_PAYMENT,
        )
        Payment.objects.create(registration=registration, amount=Decimal("300.00"))

        response = self.client.get(f"/api/families/{family.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["pending_payment"]["amount_owed"], "300.00")
