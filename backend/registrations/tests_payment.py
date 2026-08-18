"""
Phase 2: Swish/Bankgiro payment verification for paid-event registrations.

Covers verify_registration's paid-event branch, Payment/registration state
transitions via mark_payment_paid(), the swish.py URL/QR builder, and the
public payment-status lookup endpoint.
"""

from decimal import Decimal
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from checkins.models import AuditLog
from events.models import Event
from families.models import Family, Parent

from .models import Payment, PaymentEvent, Registration
from .services import (
    InvalidPaymentTransition,
    confirm_registration_despite_balance,
    mark_payment_paid,
    record_payment_event,
)
from .swish import build_qr_data_url, build_swish_url
from .tokens import generate_verification_token, hash_token


def _make_event(name="Summer Camp", price=None):
    today = timezone.now().date()
    return Event.objects.create(
        name=name,
        start_date=today,
        end_date=today,
        price=price,
        registration_opens_at=timezone.now() - timezone.timedelta(days=1),
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

    def test_rejected_transition_from_concurrent_cancel_does_not_set_method_or_marked_by(
        self,
    ):
        """Regression: mark_payment_paid used to write method/marked_by
        before calling record_payment_event, so a transition rejected
        because of a concurrent cancel (e.g. the hourly sweep, racing an
        admin bulk mark-paid action) still left a false method/marked_by
        trail on a payment with no matching PaymentEvent."""
        from accounts.models import AdminUser

        staff = AdminUser.objects.create_user(
            username="racer", password="testpass123", name="Racer"
        )
        # The caller's in-memory `payment` still reads PENDING — simulates
        # the sweep cancelling the row between admin's queryset fetch and
        # this call.
        Payment.objects.filter(pk=self.payment.pk).update(
            status=Payment.Status.CANCELLED
        )

        with self.assertRaises(InvalidPaymentTransition):
            mark_payment_paid(
                self.payment, method=Payment.Method.SWISH, marked_by=staff
            )

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.CANCELLED)
        self.assertEqual(self.payment.method, "")
        self.assertIsNone(self.payment.marked_by)


class PaymentEventLedgerTests(TestCase):
    """Punch-list item 7: partial payments, overpayment, refunds, and
    goodwill adjustments, all via the append-only PaymentEvent ledger."""

    def setUp(self):
        self.event = _make_event(price=Decimal("1500.00"))
        self.family = Family.objects.create(last_name="Ledger")
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
    def test_partial_received_sets_partially_paid(self, mock_confirm):
        record_payment_event(
            self.payment,
            kind=PaymentEvent.Kind.RECEIVED,
            amount=Decimal("1200.00"),
            created_by=None,
        )

        self.payment.refresh_from_db()
        self.registration.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.PARTIALLY_PAID)
        self.assertEqual(self.payment.balance, Decimal("300.00"))
        self.assertEqual(self.registration.status, Registration.Status.PENDING_PAYMENT)
        mock_confirm.assert_not_called()

    @patch("registrations.services.send_confirmation_email")
    def test_received_events_summing_to_full_confirms_registration(self, mock_confirm):
        record_payment_event(
            self.payment,
            kind=PaymentEvent.Kind.RECEIVED,
            amount=Decimal("1200.00"),
            created_by=None,
        )
        record_payment_event(
            self.payment,
            kind=PaymentEvent.Kind.RECEIVED,
            amount=Decimal("300.00"),
            created_by=None,
        )

        self.payment.refresh_from_db()
        self.registration.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.PAID)
        self.assertEqual(self.payment.balance, Decimal("0.00"))
        self.assertEqual(self.registration.status, Registration.Status.CONFIRMED)
        mock_confirm.assert_called_once_with(self.registration)

    @patch("registrations.services.send_confirmation_email")
    def test_overpayment_is_paid_with_negative_balance(self, mock_confirm):
        record_payment_event(
            self.payment,
            kind=PaymentEvent.Kind.RECEIVED,
            amount=Decimal("1550.00"),
            created_by=None,
        )

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.PAID)
        self.assertEqual(self.payment.balance, Decimal("-50.00"))

    @patch("registrations.services.send_confirmation_email")
    def test_refund_after_confirmed_reopens_balance_without_reverting_status(
        self, mock_confirm
    ):
        record_payment_event(
            self.payment,
            kind=PaymentEvent.Kind.RECEIVED,
            amount=Decimal("1500.00"),
            created_by=None,
        )
        self.registration.refresh_from_db()
        self.assertEqual(self.registration.status, Registration.Status.CONFIRMED)

        record_payment_event(
            self.payment,
            kind=PaymentEvent.Kind.REFUNDED,
            amount=Decimal("1000.00"),
            note="Ebba avanmäld",
            created_by=None,
        )

        self.payment.refresh_from_db()
        self.registration.refresh_from_db()
        self.assertEqual(self.payment.balance, Decimal("1000.00"))
        self.assertEqual(self.payment.status, Payment.Status.PARTIALLY_PAID)
        # Orthogonality invariant (case catalog §8.2): once confirmed, a
        # ledger change never regresses Registration.status.
        self.assertEqual(self.registration.status, Registration.Status.CONFIRMED)

    @patch("registrations.services.send_confirmation_email")
    def test_adjustment_reduces_balance_and_can_confirm(self, mock_confirm):
        record_payment_event(
            self.payment,
            kind=PaymentEvent.Kind.RECEIVED,
            amount=Decimal("1200.00"),
            created_by=None,
        )
        record_payment_event(
            self.payment,
            kind=PaymentEvent.Kind.ADJUSTMENT,
            amount=Decimal("300.00"),
            note="Waived, broken arm",
            created_by=None,
        )

        self.payment.refresh_from_db()
        self.registration.refresh_from_db()
        self.assertEqual(self.payment.balance, Decimal("0.00"))
        self.assertEqual(self.payment.status, Payment.Status.PAID)
        self.assertEqual(self.registration.status, Registration.Status.CONFIRMED)
        mock_confirm.assert_called_once_with(self.registration)

    def test_rejects_event_on_cancelled_payment(self):
        self.payment.status = Payment.Status.CANCELLED
        self.payment.save(update_fields=["status"])
        with self.assertRaises(InvalidPaymentTransition):
            record_payment_event(
                self.payment,
                kind=PaymentEvent.Kind.RECEIVED,
                amount=Decimal("10.00"),
                created_by=None,
            )

    def test_rejects_non_positive_amount(self):
        with self.assertRaises(ValueError):
            record_payment_event(
                self.payment,
                kind=PaymentEvent.Kind.RECEIVED,
                amount=Decimal("0.00"),
                created_by=None,
            )

    def test_rejects_a_refund_exceeding_what_was_received(self):
        """C1, invariant 1: this is the exact bug the punch list flagged —
        an oversized refund against a partially-received payment must not
        be allowed to land the payment on a state indistinguishable from
        'never paid' while real money is still un-returned."""
        record_payment_event(
            self.payment,
            kind=PaymentEvent.Kind.RECEIVED,
            amount=Decimal("1200.00"),
            created_by=None,
        )
        with self.assertRaises(InvalidPaymentTransition):
            record_payment_event(
                self.payment,
                kind=PaymentEvent.Kind.REFUNDED,
                amount=Decimal("1300.00"),
                created_by=None,
            )
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.PARTIALLY_PAID)
        self.assertEqual(self.payment.balance, Decimal("300.00"))

    def test_rejects_a_refund_with_nothing_ever_received(self):
        with self.assertRaises(InvalidPaymentTransition):
            record_payment_event(
                self.payment,
                kind=PaymentEvent.Kind.REFUNDED,
                amount=Decimal("10.00"),
                created_by=None,
            )

    def test_rejects_an_adjustment_that_writes_off_more_than_is_owed(self):
        """C1, invariant 2: only an ADJUSTMENT can actually violate this
        (a RECEIVED event is deliberately exempt — see the module-level
        overpayment test below — and a REFUNDED event can only ever shrink
        the checked expression)."""
        record_payment_event(
            self.payment,
            kind=PaymentEvent.Kind.RECEIVED,
            amount=Decimal("1200.00"),
            created_by=None,
        )
        with self.assertRaises(InvalidPaymentTransition):
            record_payment_event(
                self.payment,
                kind=PaymentEvent.Kind.ADJUSTMENT,
                amount=Decimal("300.01"),
                created_by=None,
            )
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.balance, Decimal("300.00"))

    @patch("registrations.services.send_confirmation_email")
    def test_pure_goodwill_writeoff_with_zero_received_is_still_allowed(
        self, mock_confirm
    ):
        """The exact write-off amount owed is still a legal ADJUSTMENT with
        zero received — invariant 2 only rejects *overshooting* it."""
        record_payment_event(
            self.payment,
            kind=PaymentEvent.Kind.ADJUSTMENT,
            amount=Decimal("1500.00"),
            note="Scholarship, full waiver",
            created_by=None,
        )
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.PAID)
        self.assertEqual(self.payment.balance, Decimal("0.00"))

    @patch("registrations.services.send_confirmation_email")
    def test_overpayment_still_allowed_despite_exceeding_amount(self, mock_confirm):
        """Invariant 2 is deliberately not checked for a RECEIVED event —
        event_registration_ux_case_catalog.md §5.3 makes overpayment (a
        negative balance, with a staff 'registrera återbetalning' action) an
        intentional, supported state. Regression guard alongside
        test_overpayment_is_paid_with_negative_balance above."""
        record_payment_event(
            self.payment,
            kind=PaymentEvent.Kind.RECEIVED,
            amount=Decimal("1600.00"),
            created_by=None,
        )
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.PAID)
        self.assertEqual(self.payment.balance, Decimal("-100.00"))

    @patch("registrations.services.send_confirmation_email")
    def test_full_refund_of_fully_paid_reads_as_refunded(self, mock_confirm):
        """C1's reorder: refunded==received (and >0) must read REFUNDED, not
        fall through to the balance-threshold split where it would land on
        PENDING — indistinguishable from 'never paid' despite two real
        money movements. Narrower than 'any refund': a *partial* refund
        must stay PARTIALLY_PAID (see
        test_refund_after_confirmed_reopens_balance_without_reverting_status
        above)."""
        record_payment_event(
            self.payment,
            kind=PaymentEvent.Kind.RECEIVED,
            amount=Decimal("1500.00"),
            created_by=None,
        )
        record_payment_event(
            self.payment,
            kind=PaymentEvent.Kind.REFUNDED,
            amount=Decimal("1500.00"),
            note="Family withdrew entirely",
            created_by=None,
        )
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.REFUNDED)

    @patch("registrations.services.send_confirmation_email")
    def test_mark_payment_paid_works_from_partially_paid(self, mock_confirm):
        record_payment_event(
            self.payment,
            kind=PaymentEvent.Kind.RECEIVED,
            amount=Decimal("1200.00"),
            created_by=None,
        )

        mark_payment_paid(self.payment, method=Payment.Method.BANKGIRO, marked_by=None)

        self.payment.refresh_from_db()
        self.registration.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.PAID)
        self.assertEqual(self.payment.balance, Decimal("0.00"))
        self.assertEqual(self.registration.status, Registration.Status.CONFIRMED)


class ConfirmDespiteBalanceTests(TestCase):
    def setUp(self):
        self.event = _make_event(price=Decimal("500.00"))
        self.family = Family.objects.create(last_name="Discretion")
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
    def test_confirms_with_outstanding_balance(self, mock_confirm):
        confirm_registration_despite_balance(self.registration, confirmed_by=None)

        self.registration.refresh_from_db()
        self.payment.refresh_from_db()
        self.assertEqual(self.registration.status, Registration.Status.CONFIRMED)
        # The ledger itself is untouched — this is a staff decision to let
        # someone in, not a record of money arriving.
        self.assertEqual(self.payment.status, Payment.Status.PENDING)
        mock_confirm.assert_called_once_with(self.registration)

    def test_raises_when_not_pending_payment(self):
        self.registration.status = Registration.Status.CONFIRMED
        self.registration.save(update_fields=["status"])
        with self.assertRaises(InvalidPaymentTransition):
            confirm_registration_despite_balance(self.registration, confirmed_by=None)

    def test_concurrent_cancel_is_not_resurrected_by_stale_in_memory_read(self):
        """Regression: this used to check registration.status on the
        caller's stale in-memory instance with no lock/refresh, so a
        concurrent cancel (e.g. the hourly TTL sweep, racing a slow admin
        bulk action) could go unnoticed and get silently flipped back to
        confirmed."""
        Registration.objects.filter(pk=self.registration.pk).update(
            status=Registration.Status.CANCELLED
        )

        with self.assertRaises(InvalidPaymentTransition):
            confirm_registration_despite_balance(self.registration, confirmed_by=None)

        self.registration.refresh_from_db()
        self.assertEqual(self.registration.status, Registration.Status.CANCELLED)


class VerifyRegistrationPaymentBranchTests(TestCase):
    def setUp(self):
        # Shared anon-throttle cache persists across test classes within a
        # run (see registrations/tests_throttling.py's setUp for the same
        # pattern) — clear it so this class's own request volume doesn't
        # depend on run order.
        cache.clear()
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
        with patch(
            "registrations.views.send_verification_email", return_value=True
        ) as mock_send:
            response = self.client.post("/api/registrations/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        _, token = mock_send.call_args[0]
        registration = Registration.objects.get(
            reference_code=response.data["reference_code"]
        )
        return registration, token

    @patch("registrations.views.send_confirmation_email", return_value=True)
    def test_free_event_confirms_with_no_payment_row(self, mock_confirm):
        event = _make_event(price=None)
        registration, token = self._submit_and_get_token(event)

        response = self.client.get(f"/api/registrations/verify/{token}/")

        self.assertEqual(response.status_code, 200, response.data)
        registration.refresh_from_db()
        self.assertEqual(registration.status, Registration.Status.CONFIRMED)
        self.assertFalse(Payment.objects.filter(registration=registration).exists())
        mock_confirm.assert_called_once()

    @patch("registrations.views.send_payment_instructions_email", return_value=True)
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

    @patch("registrations.views.send_payment_instructions_email", return_value=True)
    @patch("registrations.views.send_confirmation_email", return_value=True)
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

    @patch("registrations.views.send_payment_instructions_email", return_value=True)
    @patch("registrations.views.send_confirmation_email", return_value=True)
    def test_email_match_is_case_insensitive(self, mock_confirm, mock_payment_email):
        """A differently-cased contact_email (mobile autocapitalize, or a
        deliberate spoofing attempt) must still be caught by the dedup gate
        — a case-sensitive filter() would let it auto-attach to a brand-new
        family instead of routing to pending_review."""
        event = _make_event(price=Decimal("120.00"))
        other_family = Family.objects.create(last_name="Existing")
        Parent.objects.create(
            first_name="Someone",
            relationship_type="Other",
            email="guardian@example.com",
            family=other_family,
        )

        registration, token = self._submit_and_get_token(
            event, contact_email="Guardian@Example.com"
        )

        response = self.client.get(f"/api/registrations/verify/{token}/")

        self.assertEqual(response.status_code, 200, response.data)
        registration.refresh_from_db()
        self.assertEqual(registration.status, Registration.Status.PENDING_REVIEW)
        mock_confirm.assert_not_called()
        mock_payment_email.assert_not_called()

    @patch("registrations.views.send_payment_instructions_email", return_value=True)
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


class AdminConfirmDespiteBalanceActionTests(TestCase):
    def setUp(self):
        from accounts.models import AdminUser

        self.event = _make_event(price=Decimal("500.00"))
        self.family = Family.objects.create(last_name="Discretion")
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
            username="admin_confirm", password="testpass123", name="Admin Confirm"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.staff)
        self.client.force_login(self.staff)

    @patch("registrations.services.send_confirmation_email")
    def test_confirm_despite_balance_action(self, mock_confirm):
        response = self.client.post(
            "/admin/registrations/registration/",
            {
                "action": "confirm_despite_balance",
                "_selected_action": [str(self.registration.pk)],
            },
        )
        self.assertIn(response.status_code, (200, 302))
        self.registration.refresh_from_db()
        self.payment.refresh_from_db()
        self.assertEqual(self.registration.status, Registration.Status.CONFIRMED)
        self.assertEqual(self.payment.status, Payment.Status.PENDING)
        self.assertTrue(
            AuditLog.objects.filter(
                action="registration_confirmed_despite_balance"
            ).exists()
        )


class PaymentEventAdminTests(TestCase):
    def setUp(self):
        from accounts.models import AdminUser

        self.event = _make_event(price=Decimal("500.00"))
        self.family = Family.objects.create(last_name="LedgerAdmin")
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
            username="admin_ledger", password="testpass123", name="Admin Ledger"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.staff)
        self.client.force_login(self.staff)

    @patch("registrations.services.send_confirmation_email")
    def test_add_payment_event_via_admin_records_ledger(self, mock_confirm):
        response = self.client.post(
            "/admin/registrations/paymentevent/add/",
            {
                "payment": str(self.payment.pk),
                "kind": PaymentEvent.Kind.RECEIVED,
                "amount": "200.00",
                "note": "Partial Swish",
            },
        )
        self.assertIn(response.status_code, (200, 302))
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.balance, Decimal("300.00"))
        self.assertEqual(self.payment.status, Payment.Status.PARTIALLY_PAID)
        self.assertTrue(
            PaymentEvent.objects.filter(
                payment=self.payment, amount=Decimal("200.00")
            ).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(action="payment_event_recorded").exists()
        )
