"""
Phase 2: Swish/Bankgiro payment verification for paid-event registrations.

Covers verify_registration's paid-event branch, Payment/registration state
transitions via mark_payment_paid(), the swish.py URL/QR builder, and the
public payment-status lookup endpoint.
"""

from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from checkins.models import AuditLog
from events.models import Event
from families.models import Family, Parent

from .models import Payment, Registration
from .services import InvalidPaymentTransition, mark_payment_paid
from .swish import build_qr_data_url, build_swish_url
from .tokens import generate_verification_token, hash_token


def _make_event(name="Summer Camp", price=None):
    today = timezone.now().date()
    return Event.objects.create(
        name=name, start_date=today, end_date=today, price=price
    )


class PaymentModelTests(TestCase):
    def test_reference_code_delegates_to_registration(self):
        event = _make_event(price=Decimal("100.00"))
        family = Family.objects.create(last_name="Test")
        registration = Registration.objects.create(
            event=event,
            family=family,
            contact_email="guardian@example.com",
            verification_token_hash=hash_token(generate_verification_token()),
        )
        payment = Payment.objects.create(registration=registration, amount=event.price)
        self.assertEqual(payment.reference_code, registration.reference_code)


class SwishUrlTests(TestCase):
    def test_build_swish_url_encodes_reference_and_amount(self):
        url = build_swish_url(
            payee_number="1234567890", amount=Decimal("150.00"), reference="KL2026 1"
        )
        self.assertIn("sw=1234567890", url)
        self.assertIn("amt=150.00", url)
        self.assertIn("cur=SEK", url)
        self.assertIn("msg=KL2026%201", url)

    def test_build_qr_data_url_returns_png_data_url(self):
        url = build_swish_url(
            payee_number="1234567890", amount=Decimal("10.00"), reference="ABC"
        )
        data_url = build_qr_data_url(url)
        self.assertTrue(data_url.startswith("data:image/png;base64,"))

    @override_settings(SWISH_PAYEE_NUMBER="", BANKGIRO_NUMBER="")
    def test_payment_instructions_blank_safe_when_unconfigured(self):
        from .swish import payment_instructions

        event = _make_event(price=Decimal("50.00"))
        family = Family.objects.create(last_name="Test")
        registration = Registration.objects.create(
            event=event,
            family=family,
            contact_email="guardian@example.com",
            verification_token_hash=hash_token(generate_verification_token()),
        )
        payment = Payment.objects.create(registration=registration, amount=event.price)

        instructions = payment_instructions(payment)

        self.assertIsNone(instructions["swish_url"])
        self.assertIsNone(instructions["swish_qr_data_url"])
        self.assertIsNone(instructions["bankgiro_number"])

    @override_settings(SWISH_PAYEE_NUMBER="1231231231", BANKGIRO_NUMBER="123-4567")
    def test_payment_instructions_populated_when_configured(self):
        from .swish import payment_instructions

        event = _make_event(price=Decimal("50.00"))
        family = Family.objects.create(last_name="Test")
        registration = Registration.objects.create(
            event=event,
            family=family,
            contact_email="guardian@example.com",
            verification_token_hash=hash_token(generate_verification_token()),
        )
        payment = Payment.objects.create(registration=registration, amount=event.price)

        instructions = payment_instructions(payment)

        self.assertIsNotNone(instructions["swish_url"])
        self.assertIsNotNone(instructions["swish_qr_data_url"])
        self.assertEqual(instructions["bankgiro_number"], "123-4567")


class MarkPaymentPaidTests(TestCase):
    def setUp(self):
        self.event = _make_event(price=Decimal("75.00"))
        self.family = Family.objects.create(last_name="Test")
        self.registration = Registration.objects.create(
            event=self.event,
            family=self.family,
            contact_email="guardian@example.com",
            verification_token_hash=hash_token(generate_verification_token()),
            status=Registration.Status.PENDING_PAYMENT,
        )
        self.payment = Payment.objects.create(
            registration=self.registration, amount=self.event.price
        )

    @patch("registrations.services.send_confirmation_email")
    def test_happy_path_confirms_registration_and_pays(self, mock_confirm):
        mark_payment_paid(self.payment, method=Payment.Method.SWISH, marked_by=None)

        self.payment.refresh_from_db()
        self.registration.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.PAID)
        self.assertEqual(self.payment.method, Payment.Method.SWISH)
        self.assertIsNotNone(self.payment.paid_at)
        self.assertEqual(self.registration.status, Registration.Status.CONFIRMED)
        mock_confirm.assert_called_once_with(self.registration)

    @patch("registrations.services.send_confirmation_email")
    def test_already_paid_raises(self, mock_confirm):
        mark_payment_paid(self.payment, method=Payment.Method.SWISH, marked_by=None)
        with self.assertRaises(InvalidPaymentTransition):
            mark_payment_paid(self.payment, method=Payment.Method.SWISH, marked_by=None)

    def test_registration_not_pending_payment_raises(self):
        self.registration.status = Registration.Status.CONFIRMED
        self.registration.save(update_fields=["status"])
        with self.assertRaises(InvalidPaymentTransition):
            mark_payment_paid(self.payment, method=Payment.Method.SWISH, marked_by=None)


class VerifyRegistrationPaymentBranchTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _submit_and_get_token(self, event, contact_email="guardian@example.com"):
        payload = {
            "event": str(event.id),
            "contact_email": contact_email,
            "parents": [
                {
                    "first_name": "Anna",
                    "relationship_type": "Mother",
                    "email": contact_email,
                }
            ],
            "children": [{"first_name": "Kim", "birthdate": "2018-01-01"}],
        }
        with patch("registrations.views.send_verification_email") as mock_send:
            response = self.client.post("/api/registrations/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        _, token = mock_send.call_args[0]
        registration = Registration.objects.get(
            reference_code=response.data["reference_code"]
        )
        return registration, token

    @patch("registrations.views.send_confirmation_email")
    def test_free_event_confirms_with_no_payment_row(self, mock_confirm):
        event = _make_event(price=None)
        registration, token = self._submit_and_get_token(event)

        response = self.client.get(f"/api/registrations/verify/{token}/")

        self.assertEqual(response.status_code, 200, response.data)
        registration.refresh_from_db()
        self.assertEqual(registration.status, Registration.Status.CONFIRMED)
        self.assertFalse(Payment.objects.filter(registration=registration).exists())
        mock_confirm.assert_called_once()

    @patch("registrations.views.send_payment_instructions_email")
    def test_paid_event_routes_to_pending_payment_with_payment_row(self, mock_send):
        event = _make_event(price=Decimal("120.00"))
        registration, token = self._submit_and_get_token(event)

        response = self.client.get(f"/api/registrations/verify/{token}/")

        self.assertEqual(response.status_code, 200, response.data)
        registration.refresh_from_db()
        self.assertEqual(registration.status, Registration.Status.PENDING_PAYMENT)
        payment = Payment.objects.get(registration=registration)
        self.assertEqual(payment.amount, Decimal("120.00"))
        self.assertEqual(payment.status, Payment.Status.PENDING)
        self.assertEqual(response.data["amount"], "120.00")
        self.assertEqual(response.data["reference_code"], registration.reference_code)
        mock_send.assert_called_once()

    @patch("registrations.views.send_payment_instructions_email")
    @patch("registrations.views.send_confirmation_email")
    def test_email_match_takes_precedence_over_paid_event(
        self, mock_confirm, mock_payment_email
    ):
        """A paid event AND an email match on another family: pending_review
        wins, but a Payment row is still created so it's ready once review
        clears it."""
        event = _make_event(price=Decimal("120.00"))
        other_family = Family.objects.create(last_name="Existing")
        Parent.objects.create(
            first_name="Someone",
            relationship_type="Other",
            email="guardian@example.com",
            family=other_family,
        )

        registration, token = self._submit_and_get_token(
            event, contact_email="guardian@example.com"
        )

        response = self.client.get(f"/api/registrations/verify/{token}/")

        self.assertEqual(response.status_code, 200, response.data)
        registration.refresh_from_db()
        self.assertEqual(registration.status, Registration.Status.PENDING_REVIEW)
        self.assertTrue(Payment.objects.filter(registration=registration).exists())
        mock_confirm.assert_not_called()
        mock_payment_email.assert_not_called()

    @patch("registrations.views.send_payment_instructions_email")
    def test_pending_payment_expiry_uses_payment_ttl(self, mock_send):
        event = _make_event(price=Decimal("120.00"))
        registration, token = self._submit_and_get_token(event)

        self.client.get(f"/api/registrations/verify/{token}/")

        registration.refresh_from_db()
        days_left = (registration.expires_at - timezone.now()).days
        self.assertGreaterEqual(days_left, 6)
        self.assertLessEqual(days_left, 7)


class RegistrationPaymentStatusTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.event = _make_event(price=Decimal("90.00"))
        self.family = Family.objects.create(last_name="Test")
        self.registration = Registration.objects.create(
            event=self.event,
            family=self.family,
            contact_email="guardian@example.com",
            verification_token_hash=hash_token(generate_verification_token()),
            status=Registration.Status.PENDING_PAYMENT,
        )
        self.payment = Payment.objects.create(
            registration=self.registration, amount=self.event.price
        )
        self.url = "/api/registrations/payment-status/"

    def test_correct_reference_and_email_returns_payload(self):
        response = self.client.post(
            self.url,
            {
                "reference_code": self.registration.reference_code,
                "contact_email": "guardian@example.com",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["status"], Registration.Status.PENDING_PAYMENT)
        self.assertEqual(response.data["amount"], "90.00")

    def test_wrong_email_returns_404(self):
        response = self.client.post(
            self.url,
            {
                "reference_code": self.registration.reference_code,
                "contact_email": "wrong@example.com",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_free_event_registration_returns_404(self):
        free_event = _make_event(name="Free Event", price=None)
        free_registration = Registration.objects.create(
            event=free_event,
            family=self.family,
            contact_email="guardian2@example.com",
            verification_token_hash=hash_token(generate_verification_token()),
            status=Registration.Status.CONFIRMED,
        )
        response = self.client.post(
            self.url,
            {
                "reference_code": free_registration.reference_code,
                "contact_email": "guardian2@example.com",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_lookup_logs_audit(self):
        self.client.post(
            self.url,
            {
                "reference_code": self.registration.reference_code,
                "contact_email": "guardian@example.com",
            },
            format="json",
        )
        self.assertTrue(
            AuditLog.objects.filter(
                action="registration_payment_status_checked"
            ).exists()
        )


class AdminMarkPaidActionTests(TestCase):
    def setUp(self):
        from accounts.models import AdminUser

        self.event = _make_event(price=Decimal("60.00"))
        self.family = Family.objects.create(last_name="Test")
        self.registration = Registration.objects.create(
            event=self.event,
            family=self.family,
            contact_email="guardian@example.com",
            verification_token_hash=hash_token(generate_verification_token()),
            status=Registration.Status.PENDING_PAYMENT,
        )
        self.payment = Payment.objects.create(
            registration=self.registration, amount=self.event.price
        )
        self.staff = AdminUser.objects.create_superuser(
            username="admin", password="testpass123", name="Admin"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.staff)
        self.client.force_login(self.staff)

    @patch("registrations.services.send_confirmation_email")
    def test_mark_paid_swish_action_confirms_registration(self, mock_confirm):
        response = self.client.post(
            "/admin/registrations/registration/",
            {
                "action": "mark_paid_swish",
                "_selected_action": [str(self.registration.pk)],
            },
        )
        self.assertIn(response.status_code, (200, 302))
        self.payment.refresh_from_db()
        self.registration.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.PAID)
        self.assertEqual(self.payment.method, Payment.Method.SWISH)
        self.assertEqual(self.registration.status, Registration.Status.CONFIRMED)
        self.assertTrue(
            AuditLog.objects.filter(action="registration_payment_marked_paid").exists()
        )
