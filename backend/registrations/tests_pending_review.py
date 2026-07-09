"""
B1: pending_review's real resolution path.

verify_registration routes to PENDING_REVIEW when a verified email matches
an existing Parent on a different family (the anti-spoofing dedup gate).
Before this, the only escape hatch was a raw Django-admin field edit, which
skipped Payment creation, the confirmation/payment-instructions email, and
log_audit. resolve_pending_review (services.py) and its two RegistrationAdmin
actions are the real fix.
"""

from decimal import Decimal
from unittest.mock import patch

from django.contrib import admin
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from checkins.models import AuditLog
from events.models import Event, PromoCode
from families.models import Family

from .models import Payment, Registration
from .services import InvalidPaymentTransition, resolve_pending_review
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


def _make_pending_review_registration(event, *, contact_email="guardian@example.com"):
    family = Family.objects.create(last_name="Test")
    return Registration.objects.create(
        event=event,
        family=family,
        contact_email=contact_email,
        verification_token_hash=hash_token(generate_verification_token()),
        status=Registration.Status.PENDING_REVIEW,
    )


class ResolvePendingReviewTests(TestCase):
    def test_raises_when_not_pending_review(self):
        event = _make_event()
        registration = _make_pending_review_registration(event)
        registration.status = Registration.Status.CONFIRMED
        registration.save(update_fields=["status"])

        with self.assertRaises(InvalidPaymentTransition):
            resolve_pending_review(registration, action="confirm", resolved_by=None)

    def test_unknown_action_raises(self):
        event = _make_event()
        registration = _make_pending_review_registration(event)

        with self.assertRaises(ValueError):
            resolve_pending_review(registration, action="bogus", resolved_by=None)

    @patch("registrations.services.send_confirmation_email")
    def test_confirm_with_no_payment_confirms_directly(self, mock_confirm):
        event = _make_event(price=None)
        registration = _make_pending_review_registration(event)

        resolve_pending_review(registration, action="confirm", resolved_by=None)

        registration.refresh_from_db()
        self.assertEqual(registration.status, Registration.Status.CONFIRMED)
        mock_confirm.assert_called_once_with(registration)

    @patch("registrations.services.send_payment_instructions_email")
    def test_confirm_with_outstanding_payment_routes_to_pending_payment(
        self, mock_send
    ):
        event = _make_event(price=Decimal("150.00"))
        registration = _make_pending_review_registration(event)
        payment = Payment.objects.create(registration=registration, amount=event.price)

        resolve_pending_review(registration, action="confirm", resolved_by=None)

        registration.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(registration.status, Registration.Status.PENDING_PAYMENT)
        self.assertEqual(payment.status, Payment.Status.PENDING)
        mock_send.assert_called_once_with(registration)

    def test_reject_cancels_registration_and_pending_payment(self):
        event = _make_event(price=Decimal("150.00"))
        registration = _make_pending_review_registration(event)
        payment = Payment.objects.create(registration=registration, amount=event.price)

        resolve_pending_review(registration, action="reject", resolved_by=None)

        registration.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(registration.status, Registration.Status.CANCELLED)
        self.assertEqual(payment.status, Payment.Status.CANCELLED)

    def test_reject_releases_promo_code_use(self):
        event = _make_event(price=Decimal("150.00"))
        promo = PromoCode.objects.create(
            event=event, code="REVIEW", max_uses=5, uses_count=2
        )
        registration = _make_pending_review_registration(event)
        registration.promo_code = promo
        registration.save(update_fields=["promo_code"])

        resolve_pending_review(registration, action="reject", resolved_by=None)

        promo.refresh_from_db()
        self.assertEqual(promo.uses_count, 1)


class AdminResolvePendingReviewActionTests(TestCase):
    def setUp(self):
        from accounts.models import AdminUser

        self.event = _make_event(price=None)
        self.registration = _make_pending_review_registration(self.event)
        self.staff = AdminUser.objects.create_superuser(
            username="admin_review", password="testpass123", name="Admin Review"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.staff)
        self.client.force_login(self.staff)

    @patch("registrations.services.send_confirmation_email")
    def test_confirm_action(self, mock_confirm):
        response = self.client.post(
            "/admin/registrations/registration/",
            {
                "action": "resolve_pending_review_confirm",
                "_selected_action": [str(self.registration.pk)],
            },
        )
        self.assertIn(response.status_code, (200, 302))
        self.registration.refresh_from_db()
        self.assertEqual(self.registration.status, Registration.Status.CONFIRMED)
        self.assertTrue(
            AuditLog.objects.filter(
                action="registration_pending_review_confirmed"
            ).exists()
        )

    def test_reject_action(self):
        response = self.client.post(
            "/admin/registrations/registration/",
            {
                "action": "resolve_pending_review_reject",
                "_selected_action": [str(self.registration.pk)],
            },
        )
        self.assertIn(response.status_code, (200, 302))
        self.registration.refresh_from_db()
        self.assertEqual(self.registration.status, Registration.Status.CANCELLED)
        self.assertTrue(
            AuditLog.objects.filter(
                action="registration_pending_review_rejected"
            ).exists()
        )

    def test_status_field_is_readonly(self):
        """B1: status now transitions only through service functions — a
        raw field edit used to be the only escape hatch out of
        pending_review, skipping Payment handling, email, and audit."""
        from django.test import RequestFactory

        from .admin import RegistrationAdmin
        from .models import Registration

        model_admin = RegistrationAdmin(Registration, admin.site)
        request = RequestFactory().get("/")
        request.user = self.staff
        self.assertIn(
            "status", model_admin.get_readonly_fields(request, self.registration)
        )
