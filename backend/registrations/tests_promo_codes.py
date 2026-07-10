"""Promo codes: whole/scoped discounts, hidden-ticket unlock, max-uses
locking (case catalog §5.4).

Covers pricing.py::calculate_discount directly, the submission-flow
integration in views.py (_resolve_promo_code, the is_hidden gate on
_validate_ticket_type_for_attendee), and the read-only
validate_promo_code preview endpoint.
"""

import threading
from decimal import Decimal
from unittest.mock import patch

from django.core.cache import cache
from django.db import connection, transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from events.models import AppliesTo, Event, EventTicket, PromoCode, TicketType
from families.models import Family, Parent

from .models import Registration
from .pricing import calculate_discount, calculate_total
from .services import release_promo_code_use
from .tokens import generate_verification_token, hash_token
from .views import _resolve_promo_code


def _make_event(name="Weekend 2026"):
    today = timezone.now().date()
    return Event.objects.create(
        name=name,
        start_date=today,
        end_date=today,
        registration_opens_at=timezone.now() - timezone.timedelta(days=1),
    )


def _make_registration(event, *, contact_email="guardian@example.com"):
    family = Family.objects.create(last_name="Test")
    return Registration.objects.create(
        event=event,
        family=family,
        contact_email=contact_email,
        verification_token_hash=hash_token(generate_verification_token()),
    )


def _make_promo_code(event, **overrides):
    defaults = {
        "code": "TESTCODE",
        "discount_type": PromoCode.DiscountType.FIXED,
        "discount_value": Decimal("0"),
    }
    defaults.update(overrides)
    return PromoCode.objects.create(event=event, **defaults)


class CalculateDiscountTests(TestCase):
    def _with_adult_ticket(self, event, *, price=Decimal("1000.00")):
        ticket_type = TicketType.objects.create(event=event, name="Adult", price=price)
        registration = _make_registration(event)
        parent = Parent.objects.create(
            family=registration.family, first_name="Anna", relationship_type="Mother"
        )
        EventTicket.objects.create(
            attendee=parent,
            event=event,
            registration=registration,
            ticket_type=ticket_type,
            price_at_registration=price,
        )
        return registration, ticket_type

    def test_whole_total_percent_discount(self):
        event = _make_event()
        registration, _ = self._with_adult_ticket(event, price=Decimal("1000.00"))
        promo = _make_promo_code(
            event,
            discount_type=PromoCode.DiscountType.PERCENT,
            discount_value=Decimal("10"),
        )
        self.assertEqual(calculate_discount(registration, promo), Decimal("100.00"))

    def test_whole_total_fixed_discount(self):
        event = _make_event()
        registration, _ = self._with_adult_ticket(event, price=Decimal("1000.00"))
        promo = _make_promo_code(
            event,
            discount_type=PromoCode.DiscountType.FIXED,
            discount_value=Decimal("150.00"),
        )
        self.assertEqual(calculate_discount(registration, promo), Decimal("150.00"))

    def test_scoped_discount_ignores_unmatched_lines(self):
        event = _make_event()
        adult_type = TicketType.objects.create(event=event, name="Adult", price=1000)
        child_type = TicketType.objects.create(
            event=event, name="Child", price=400, applies_to=AppliesTo.CHILD
        )
        registration = _make_registration(event)
        parent = Parent.objects.create(
            family=registration.family, first_name="Anna", relationship_type="Mother"
        )
        EventTicket.objects.create(
            attendee=parent,
            event=event,
            registration=registration,
            ticket_type=adult_type,
            price_at_registration=Decimal("1000.00"),
        )
        from families.models import Child

        child = Child.objects.create(family=registration.family, first_name="Kim")
        EventTicket.objects.create(
            attendee=child,
            event=event,
            registration=registration,
            ticket_type=child_type,
            price_at_registration=Decimal("400.00"),
        )
        promo = _make_promo_code(
            event,
            discount_type=PromoCode.DiscountType.PERCENT,
            discount_value=Decimal("100"),
        )
        promo.applies_to_ticket_types.add(child_type)

        # Only the child ticket (400) is scoped — the adult ticket (1000)
        # must be untouched (case catalog §5.4(b)'s exact failure mode).
        self.assertEqual(calculate_discount(registration, promo), Decimal("400.00"))

    def test_fixed_discount_caps_at_scoped_base(self):
        event = _make_event()
        registration, ticket_type = self._with_adult_ticket(
            event, price=Decimal("300.00")
        )
        promo = _make_promo_code(
            event,
            discount_type=PromoCode.DiscountType.FIXED,
            discount_value=Decimal("500.00"),
        )
        promo.applies_to_ticket_types.add(ticket_type)

        self.assertEqual(calculate_discount(registration, promo), Decimal("300.00"))

    def test_full_discount_drives_total_to_zero(self):
        event = _make_event()
        registration, _ = self._with_adult_ticket(event, price=Decimal("1000.00"))
        promo = _make_promo_code(
            event,
            discount_type=PromoCode.DiscountType.PERCENT,
            discount_value=Decimal("100"),
        )
        registration.promo_code = promo
        registration.discount_amount = calculate_discount(registration, promo)
        registration.save(update_fields=["promo_code", "discount_amount"])

        self.assertEqual(calculate_total(registration), Decimal("0.00"))


class PromoCodeSubmissionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.event = _make_event()
        self.adult_type = TicketType.objects.create(
            event=self.event, name="Adult", price=1000, applies_to=AppliesTo.PARENT
        )
        self.vip_type = TicketType.objects.create(
            event=self.event,
            name="VIP",
            price=0,
            applies_to=AppliesTo.PARENT,
            is_hidden=True,
        )
        self.url = "/api/registrations/"

    def _payload(self, ticket_type, **overrides):
        payload = {
            "event": str(self.event.id),
            "contact_email": "guardian@example.com",
            "parents": [
                {
                    "first_name": "Anna",
                    "relationship_type": "Mother",
                    "ticket_type": str(ticket_type.id),
                }
            ],
        }
        payload.update(overrides)
        return payload

    def test_valid_code_discounts_whole_total(self):
        promo = _make_promo_code(
            self.event,
            code="SPARA10",
            discount_type=PromoCode.DiscountType.PERCENT,
            discount_value=Decimal("10"),
        )
        payload = self._payload(self.adult_type, promo_code="SPARA10")

        with patch("registrations.views.send_verification_email"):
            response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 201, response.data)
        registration = Registration.objects.get()
        self.assertEqual(registration.promo_code_id, promo.id)
        self.assertEqual(registration.discount_amount, Decimal("100.00"))
        self.assertEqual(calculate_total(registration), Decimal("900.00"))
        promo.refresh_from_db()
        self.assertEqual(promo.uses_count, 1)

    def test_code_matched_case_insensitively(self):
        _make_promo_code(self.event, code="SPARA10", discount_value=Decimal("50.00"))
        payload = self._payload(self.adult_type, promo_code="spara10")

        with patch("registrations.views.send_verification_email"):
            response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 201, response.data)

    def test_hidden_ticket_type_rejected_without_code(self):
        payload = self._payload(self.vip_type)

        with patch("registrations.views.send_verification_email"):
            response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 400, response.data)

    def test_hidden_ticket_type_rejected_by_a_code_that_does_not_unlock_it(self):
        _make_promo_code(self.event, code="SPARA10", discount_value=Decimal("50.00"))
        payload = self._payload(self.vip_type, promo_code="SPARA10")

        with patch("registrations.views.send_verification_email"):
            response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 400, response.data)

    def test_hidden_ticket_type_accepted_when_unlocked_by_code(self):
        promo = _make_promo_code(self.event, code="VIP2026")
        promo.unlocks_ticket_types.add(self.vip_type)
        payload = self._payload(self.vip_type, promo_code="VIP2026")

        with patch("registrations.views.send_verification_email"):
            response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 201, response.data)
        ticket = EventTicket.objects.get()
        self.assertEqual(ticket.ticket_type_id, self.vip_type.id)

    def test_nonexistent_code_rejected_with_generic_message(self):
        payload = self._payload(self.adult_type, promo_code="NOPE")

        with patch("registrations.views.send_verification_email"):
            response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("promo_code", response.data)

    def test_inactive_code_rejected(self):
        _make_promo_code(
            self.event, code="OFF", is_active=False, discount_value=Decimal("10")
        )
        payload = self._payload(self.adult_type, promo_code="OFF")

        with patch("registrations.views.send_verification_email"):
            response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 400, response.data)

    def test_expired_code_rejected(self):
        _make_promo_code(
            self.event,
            code="OLD",
            valid_until=timezone.now() - timezone.timedelta(days=1),
            discount_value=Decimal("10"),
        )
        payload = self._payload(self.adult_type, promo_code="OLD")

        with patch("registrations.views.send_verification_email"):
            response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 400, response.data)

    def test_not_yet_valid_code_rejected(self):
        _make_promo_code(
            self.event,
            code="FUTURE",
            valid_from=timezone.now() + timezone.timedelta(days=1),
            discount_value=Decimal("10"),
        )
        payload = self._payload(self.adult_type, promo_code="FUTURE")

        with patch("registrations.views.send_verification_email"):
            response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 400, response.data)

    def test_exhausted_code_rejected_and_does_not_double_increment(self):
        promo = _make_promo_code(
            self.event, code="ONCE", max_uses=1, discount_value=Decimal("10")
        )
        payload = self._payload(self.adult_type, promo_code="ONCE")

        with patch("registrations.views.send_verification_email"):
            first = self.client.post(self.url, payload, format="json")
        self.assertEqual(first.status_code, 201, first.data)
        promo.refresh_from_db()
        self.assertEqual(promo.uses_count, 1)

        payload["contact_email"] = "other@example.com"
        with patch("registrations.views.send_verification_email"):
            second = self.client.post(self.url, payload, format="json")

        self.assertEqual(second.status_code, 400, second.data)
        promo.refresh_from_db()
        self.assertEqual(promo.uses_count, 1)

    def test_wrong_event_code_rejected(self):
        other_event = _make_event(name="Other Event")
        _make_promo_code(other_event, code="ELSEWHERE", discount_value=Decimal("10"))
        payload = self._payload(self.adult_type, promo_code="ELSEWHERE")

        with patch("registrations.views.send_verification_email"):
            response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 400, response.data)


class ResolvePromoCodeUnitTests(TestCase):
    """Direct unit coverage of _resolve_promo_code's guard clauses, faster
    and more targeted than always going through the full submission
    endpoint."""

    def setUp(self):
        self.event = _make_event()

    def test_blank_code_returns_none(self):
        self.assertIsNone(_resolve_promo_code(event=self.event, code_str=""))
        self.assertIsNone(_resolve_promo_code(event=self.event, code_str=None))

    def test_valid_code_increments_uses_count(self):
        promo = _make_promo_code(self.event, code="ONE")
        resolved = _resolve_promo_code(event=self.event, code_str="ONE")
        self.assertEqual(resolved.id, promo.id)
        promo.refresh_from_db()
        self.assertEqual(promo.uses_count, 1)


class ReleasePromoCodeUseTests(TestCase):
    """B2: usage accounting must be released by the TTL sweep on expiry/
    cancellation — identical semantics to capacity (case catalog §5.4).
    Sweep-integration coverage lives in tests_materialization.py; this
    covers release_promo_code_use itself."""

    def setUp(self):
        self.event = _make_event()

    def test_no_promo_code_is_a_no_op(self):
        registration = _make_registration(self.event)
        release_promo_code_use(registration)  # must not raise

    def test_decrements_uses_count(self):
        promo = _make_promo_code(self.event, max_uses=5, uses_count=2)
        registration = _make_registration(self.event)
        registration.promo_code = promo
        registration.save(update_fields=["promo_code"])

        release_promo_code_use(registration)

        promo.refresh_from_db()
        self.assertEqual(promo.uses_count, 1)

    def test_floored_at_zero(self):
        promo = _make_promo_code(self.event, max_uses=5, uses_count=0)
        registration = _make_registration(self.event)
        registration.promo_code = promo
        registration.save(update_fields=["promo_code"])

        release_promo_code_use(registration)

        promo.refresh_from_db()
        self.assertEqual(promo.uses_count, 0)

    def test_frees_a_slot_for_the_next_submission(self):
        promo = _make_promo_code(self.event, code="ONCE", max_uses=1)
        _resolve_promo_code(event=self.event, code_str="ONCE")
        promo.refresh_from_db()
        self.assertEqual(promo.uses_count, 1)
        registration = _make_registration(self.event)
        registration.promo_code = promo
        registration.save(update_fields=["promo_code"])

        release_promo_code_use(registration)

        resolved_again = _resolve_promo_code(event=self.event, code_str="ONCE")
        self.assertIsNotNone(resolved_again)
        promo.refresh_from_db()
        self.assertEqual(promo.uses_count, 1)


class AdminCancelRegistrationsReleasesPromoCodeTests(TestCase):
    def test_cancel_registrations_action_releases_promo_code_use(self):
        from accounts.models import AdminUser

        event = _make_event()
        promo = _make_promo_code(event, code="CANCEL", max_uses=1, uses_count=1)
        registration = _make_registration(event)
        registration.promo_code = promo
        registration.save(update_fields=["promo_code"])
        staff = AdminUser.objects.create_superuser(
            username="admin_cancel", password="testpass123", name="Admin Cancel"
        )
        client = APIClient()
        client.force_authenticate(user=staff)
        client.force_login(staff)

        response = client.post(
            "/admin/registrations/registration/",
            {"action": "cancel_registrations", "_selected_action": [str(registration.pk)]},
        )

        self.assertIn(response.status_code, (200, 302))
        registration.refresh_from_db()
        promo.refresh_from_db()
        self.assertEqual(registration.status, Registration.Status.CANCELLED)
        self.assertEqual(promo.uses_count, 0)


class PromoCodeMaxUsesRaceTests(TransactionTestCase):
    """Real concurrency coverage for case catalog §5.4(d): two simultaneous
    redemptions against a max_uses=1 code must yield exactly one winner —
    the select_for_update() lock in _resolve_promo_code is what enforces
    this."""

    def test_two_simultaneous_redemptions_yield_exactly_one_winner(self):
        event = _make_event()
        _make_promo_code(event, code="RACE1", max_uses=1)

        results = []
        barrier = threading.Barrier(2)

        def attempt():
            try:
                with transaction.atomic():
                    barrier.wait(timeout=5)
                    _resolve_promo_code(event=event, code_str="RACE1")
                results.append("ok")
            except ValidationError:
                results.append("rejected")
            finally:
                connection.close()

        threads = [threading.Thread(target=attempt) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(sorted(results), ["ok", "rejected"])
        promo = PromoCode.objects.get(event=event, code="RACE1")
        self.assertEqual(promo.uses_count, 1)


class ValidatePromoCodeEndpointTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.event = _make_event()
        self.vip_type = TicketType.objects.create(
            event=self.event, name="VIP", price=0, is_hidden=True
        )
        self.url = "/api/registrations/validate-promo-code/"

    def test_valid_code_reveals_unlocked_ticket_types(self):
        promo = _make_promo_code(
            self.event,
            code="VIP2026",
            discount_type=PromoCode.DiscountType.PERCENT,
            discount_value=Decimal("0"),
        )
        promo.unlocks_ticket_types.add(self.vip_type)

        response = self.client.post(
            self.url, {"event": str(self.event.id), "code": "vip2026"}, format="json"
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["valid"])
        unlocked_ids = [t["id"] for t in response.data["unlocks_ticket_types"]]
        self.assertEqual(unlocked_ids, [str(self.vip_type.id)])

    def test_invalid_code_returns_valid_false(self):
        response = self.client.post(
            self.url, {"event": str(self.event.id), "code": "NOPE"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data["valid"])

    def test_blank_code_returns_valid_false(self):
        response = self.client.post(
            self.url, {"event": str(self.event.id), "code": ""}, format="json"
        )
        self.assertFalse(response.data["valid"])

    def test_does_not_increment_uses_count(self):
        promo = _make_promo_code(self.event, code="PREVIEW")

        self.client.post(
            self.url, {"event": str(self.event.id), "code": "PREVIEW"}, format="json"
        )
        self.client.post(
            self.url, {"event": str(self.event.id), "code": "PREVIEW"}, format="json"
        )

        promo.refresh_from_db()
        self.assertEqual(promo.uses_count, 0)

    def test_exhausted_code_returns_valid_false(self):
        promo = _make_promo_code(self.event, code="GONE", max_uses=1)
        promo.uses_count = 1
        promo.save(update_fields=["uses_count"])

        response = self.client.post(
            self.url, {"event": str(self.event.id), "code": "GONE"}, format="json"
        )
        self.assertFalse(response.data["valid"])
