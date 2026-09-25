"""Ticket-type capacity enforcement (registration dev-cycle round 4,
increment 2 — added 2026-09-24; race/deadlock fix, N+1 fix, and staff-path
coverage added in the gate-review revision, 2026-09-25).

An earlier audit found TicketType.capacity was schema-only: "setting 50
will not stop a 51st booking" (see the field's own help_text before this
increment). This file covers:

* ticket_type_sold_count's "what counts as sold" rule (registrations/
  services.py — the full reasoning against tasks.py's sweeps lives there
  now) — which statuses count, session_bundle attendee-dedup, and the
  null-registration (staff/import) branch. TicketTypeSoldCountTests,
  SessionBundleSoldCountTests.
* reserve_ticket_type_capacity's race- AND deadlock-safety. The original
  per-attendee-lock version deadlocked live in 5/6 opposite-order pairs
  (R1, gate review 2026-09-25) — TicketTypeCapacityRaceTests (single type,
  the original race) and OppositeOrderNoDeadlockTests (two types, opposite
  submission order, the deadlock this revision fixes) are both real
  two-thread TransactionTestCases, the same style as tests_idempotency.py
  ::IdempotencyKeyStaleReclaimRaceTests and tests_promo_codes.py::
  PromoCodeMaxUsesRaceTests — a single-connection mock can't reproduce a
  genuine cross-transaction lock wait, let alone a deadlock between two.
* RegistrationBusyRetryTests: the defence-in-depth 503 (code
  "registration_busy_retry") submit_registration returns for a Postgres
  deadlock/serialization failure that reaches it anyway, on both of its
  branches.
* sold_counts_for_event's bounded query count (R3) —
  SoldCountsForEventQueryCountTests.
* The public availability flag (_ticket_type_payload's "available") and
  the interplay with increment 1's idempotency-key reservation (a refused
  submit must delete its reservation, same as any other validation
  failure) — RegistrationSubmitCapacityTests,
  RegistrationEventInfoAvailabilityTests.

The staff-path coverage for R4/D1 (the EventTicket add-form warning, and
the ticket-type-change wizard's capacity_warning) lives in
tests_ticket_type_change.py instead, alongside the rest of that wizard's
existing tests, not here.
"""

import threading
from decimal import Decimal
from unittest.mock import patch

from django.db import OperationalError, connection
from django.test import TestCase, TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from events.models import (
    AppliesTo,
    Event,
    EventTicket,
    Session,
    SessionTicket,
    TicketType,
)
from families.models import Child, Family, Parent

from .models import Registration, RegistrationIdempotencyKey
from .services import (
    TicketTypeSoldOut,
    reserve_ticket_type_capacity,
    sold_counts_for_event,
    ticket_type_sold_count,
)
from .tokens import generate_verification_token, hash_token


def _make_event(name="Summer Camp"):
    today = timezone.now().date()
    return Event.objects.create(
        name=name,
        start_date=today,
        end_date=today,
        registration_opens_at=timezone.now() - timezone.timedelta(days=1),
    )


def _make_registration(event, *, status=Registration.Status.PENDING_VERIFICATION):
    family = Family.objects.create(last_name="Test")
    return Registration.objects.create(
        event=event,
        family=family,
        contact_email="guardian@example.com",
        verification_token_hash=hash_token(generate_verification_token()),
        status=status,
    )


class TicketTypeSoldCountTests(TestCase):
    """Which Registration statuses consume a seat — the core of the "what
    counts as sold" rule. Mirrors tests_materialization.py's own per-status
    coverage of the expiry sweeps, since this rule is built to agree with
    them (see ticket_type_sold_count's docstring)."""

    def setUp(self):
        self.event = _make_event()
        self.ticket_type = TicketType.objects.create(
            event=self.event, name="Adult", price=Decimal("100.00")
        )

    def _ticket(self, status):
        registration = _make_registration(self.event, status=status)
        parent = Parent.objects.create(
            family=registration.family, first_name="Anna", relationship_type="Mother"
        )
        return EventTicket.objects.create(
            attendee=parent,
            event=self.event,
            registration=registration,
            ticket_type=self.ticket_type,
        )

    def test_pending_verification_counts(self):
        self._ticket(Registration.Status.PENDING_VERIFICATION)
        self.assertEqual(ticket_type_sold_count(self.ticket_type), 1)

    def test_pending_payment_counts(self):
        self._ticket(Registration.Status.PENDING_PAYMENT)
        self.assertEqual(ticket_type_sold_count(self.ticket_type), 1)

    def test_pending_review_counts(self):
        self._ticket(Registration.Status.PENDING_REVIEW)
        self.assertEqual(ticket_type_sold_count(self.ticket_type), 1)

    def test_confirmed_counts(self):
        self._ticket(Registration.Status.CONFIRMED)
        self.assertEqual(ticket_type_sold_count(self.ticket_type), 1)

    def test_cancelled_does_not_count(self):
        self._ticket(Registration.Status.CANCELLED)
        self.assertEqual(ticket_type_sold_count(self.ticket_type), 0)

    def test_staff_created_ticket_with_no_registration_counts(self):
        """A NULL registration (staff-created/imported — see
        EventTicket.registration's help_text) can never become CANCELLED by
        construction, so it must always count. This is also the regression
        guard for the NULL-across-a-LEFT-JOIN gotcha the docstring warns
        about: a naive ``~Q(registration__status=CANCELLED)`` with no
        explicit isnull branch would silently drop this row instead."""
        child = Child.objects.create(family=Family.objects.create(last_name="Staff"))
        EventTicket.objects.create(
            attendee=child, event=self.event, ticket_type=self.ticket_type
        )
        self.assertEqual(ticket_type_sold_count(self.ticket_type), 1)

    def test_mixed_statuses_counts_only_the_live_ones(self):
        self._ticket(Registration.Status.CONFIRMED)
        self._ticket(Registration.Status.PENDING_VERIFICATION)
        self._ticket(Registration.Status.CANCELLED)
        self._ticket(Registration.Status.CANCELLED)
        self.assertEqual(ticket_type_sold_count(self.ticket_type), 2)


class SessionBundleSoldCountTests(TestCase):
    """A session_bundle TicketType materializes one SessionTicket row per
    covered session for the same attendee — capacity must count that
    attendee once, not once per session."""

    def setUp(self):
        self.event = _make_event()
        now = timezone.now()
        self.day1 = Session.objects.create(
            event=self.event, name="Day 1", start_time=now, end_time=now
        )
        self.day2 = Session.objects.create(
            event=self.event, name="Day 2", start_time=now, end_time=now
        )
        self.bundle = TicketType.objects.create(
            event=self.event,
            name="Weekend Pass",
            price=Decimal("200.00"),
            kind=TicketType.Kind.SESSION_BUNDLE,
        )
        self.bundle.sessions.set([self.day1, self.day2])

    def test_one_attendee_across_two_sessions_counts_once(self):
        registration = _make_registration(self.event)
        child = Child.objects.create(family=registration.family, first_name="Kim")
        for session in (self.day1, self.day2):
            SessionTicket.objects.create(
                attendee=child,
                session=session,
                registration=registration,
                ticket_type=self.bundle,
            )
        self.assertEqual(SessionTicket.objects.count(), 2)
        self.assertEqual(ticket_type_sold_count(self.bundle), 1)

    def test_two_attendees_count_two(self):
        registration = _make_registration(self.event)
        for name in ("Kim", "Alex"):
            child = Child.objects.create(family=registration.family, first_name=name)
            for session in (self.day1, self.day2):
                SessionTicket.objects.create(
                    attendee=child,
                    session=session,
                    registration=registration,
                    ticket_type=self.bundle,
                )
        self.assertEqual(ticket_type_sold_count(self.bundle), 2)


class ReserveTicketTypeCapacityTests(TestCase):
    """Unit-level coverage of registrations.services.reserve_ticket_type_
    capacity itself — the batch/dict-shaped API (R1, gate review
    2026-09-25). End-to-end HTTP-level coverage, including the DRF-shaped
    {"ticket_type": [...], "code": "ticket_sold_out"} translation views.py
    does on top of the plain TicketTypeSoldOut this function raises, lives
    in RegistrationSubmitCapacityTests below."""

    def setUp(self):
        self.event = _make_event()

    def test_empty_dict_never_raises(self):
        # No exception — just asserting this doesn't raise (a non-itemized
        # registration, or one with nothing to check, calls this with {}).
        reserve_ticket_type_capacity({})

    def test_unlimited_capacity_never_raises(self):
        ticket_type = TicketType.objects.create(
            event=self.event, name="Adult", price=Decimal("0"), capacity=None
        )
        # No exception, even asking for far more than has ever sold — just
        # asserting this doesn't raise.
        reserve_ticket_type_capacity({ticket_type: 500})

    def test_under_capacity_does_not_raise(self):
        ticket_type = TicketType.objects.create(
            event=self.event, name="Adult", price=Decimal("0"), capacity=2
        )
        self._sell_one(ticket_type)
        reserve_ticket_type_capacity({ticket_type: 1})  # 1 sold + 1 needed <= 2

    def test_needed_over_capacity_in_one_registration_raises(self):
        """Two attendees in the *same* registration both wanting a type
        with only one seat left — needed=2 against a type with nothing
        sold and capacity=1 must be refused, not silently approved because
        no single attendee alone would exceed it."""
        ticket_type = TicketType.objects.create(
            event=self.event, name="VIP", price=Decimal("0"), capacity=1
        )
        with self.assertRaises(TicketTypeSoldOut) as ctx:
            reserve_ticket_type_capacity({ticket_type: 2})
        self.assertEqual(ctx.exception.ticket_type.id, ticket_type.id)

    def test_at_capacity_raises_naming_the_ticket_type(self):
        ticket_type = TicketType.objects.create(
            event=self.event, name="VIP", price=Decimal("0"), capacity=1
        )
        self._sell_one(ticket_type)

        with self.assertRaises(TicketTypeSoldOut) as ctx:
            reserve_ticket_type_capacity({ticket_type: 1})

        self.assertEqual(ctx.exception.ticket_type.name, "VIP")
        self.assertIn("VIP", str(ctx.exception))

    def _sell_one(self, ticket_type):
        registration = _make_registration(self.event)
        parent = Parent.objects.create(
            family=registration.family, first_name="Anna", relationship_type="Mother"
        )
        EventTicket.objects.create(
            attendee=parent,
            event=self.event,
            registration=registration,
            ticket_type=ticket_type,
        )


class RegistrationSubmitCapacityTests(TestCase):
    """End-to-end through /api/registrations/ — the actual guest-facing
    enforcement point, not just the helper."""

    def setUp(self):
        self.client = APIClient()
        self.event = _make_event()
        self.full_type = TicketType.objects.create(
            event=self.event,
            name="VIP",
            price=Decimal("0"),
            applies_to=AppliesTo.PARENT,
            capacity=1,
        )
        self.open_type = TicketType.objects.create(
            event=self.event,
            name="Adult",
            price=Decimal("0"),
            applies_to=AppliesTo.PARENT,
            capacity=5,
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
            "children": [],
        }
        payload.update(overrides)
        return payload

    @patch("registrations.views.send_verification_email", return_value=True)
    def test_under_capacity_submit_succeeds(self, mock_send):
        response = self.client.post(
            self.url, self._payload(self.open_type), format="json"
        )
        self.assertEqual(response.status_code, 201, response.data)

    @patch("registrations.views.send_verification_email", return_value=True)
    def test_at_capacity_submit_is_refused_with_code_and_names_the_ticket(
        self, mock_send
    ):
        # Fill the one seat first.
        first = self.client.post(
            self.url,
            self._payload(self.full_type, contact_email="first@example.com"),
            format="json",
        )
        self.assertEqual(first.status_code, 201, first.data)

        response = self.client.post(
            self.url,
            self._payload(self.full_type, contact_email="second@example.com"),
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(response.data["code"], "ticket_sold_out")
        self.assertIn("VIP", str(response.data["ticket_type"][0]))
        # Nothing was left half-created by the rejected second submission.
        self.assertEqual(Registration.objects.count(), 1)

    @patch("registrations.views.send_verification_email", return_value=True)
    def test_sold_out_message_is_swedish_under_accept_language_sv(self, mock_send):
        self.client.post(
            self.url,
            self._payload(self.full_type, contact_email="first@example.com"),
            format="json",
        )

        response = self.client.post(
            self.url,
            self._payload(self.full_type, contact_email="second@example.com"),
            format="json",
            HTTP_ACCEPT_LANGUAGE="sv",
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("fullbokad", str(response.data["ticket_type"][0]))

    @patch("registrations.views.send_verification_email", return_value=True)
    def test_refused_submit_deletes_its_idempotency_reservation(self, mock_send):
        """Increment 1 interplay: a refused submit must not leave a
        permanent reservation behind — the existing ``except Exception:
        key_record.delete(); raise`` path in submit_registration already
        does this for every ValidationError, this just confirms capacity's
        is no exception."""
        self.client.post(
            self.url,
            self._payload(self.full_type, contact_email="first@example.com"),
            format="json",
        )

        payload = self._payload(self.full_type, contact_email="second@example.com")
        payload["idempotency_key"] = "capacity-refusal-key"
        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(
            RegistrationIdempotencyKey.objects.filter(
                key="capacity-refusal-key"
            ).exists()
        )

        # And the same key can now be retried against the still-open type
        # rather than being permanently stuck behind the dead reservation.
        retry_payload = self._payload(
            self.open_type, contact_email="second@example.com"
        )
        retry_payload["idempotency_key"] = "capacity-refusal-key"
        retry = self.client.post(self.url, retry_payload, format="json")
        self.assertEqual(retry.status_code, 201, retry.data)


class RegistrationEventInfoAvailabilityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.event = _make_event()
        self.url = f"/api/registrations/events/{self.event.id}/"

    def test_unlimited_capacity_is_always_available(self):
        TicketType.objects.create(
            event=self.event, name="Adult", price=Decimal("0"), capacity=None
        )
        response = self.client.get(self.url)
        self.assertTrue(response.data["ticket_types"][0]["available"])

    def test_under_capacity_is_available(self):
        ticket_type = TicketType.objects.create(
            event=self.event, name="Adult", price=Decimal("0"), capacity=2
        )
        registration = _make_registration(self.event)
        parent = Parent.objects.create(
            family=registration.family, first_name="Anna", relationship_type="Mother"
        )
        EventTicket.objects.create(
            attendee=parent,
            event=self.event,
            registration=registration,
            ticket_type=ticket_type,
        )

        response = self.client.get(self.url)

        self.assertTrue(response.data["ticket_types"][0]["available"])

    def test_at_capacity_is_not_available(self):
        ticket_type = TicketType.objects.create(
            event=self.event, name="Adult", price=Decimal("0"), capacity=1
        )
        registration = _make_registration(self.event)
        parent = Parent.objects.create(
            family=registration.family, first_name="Anna", relationship_type="Mother"
        )
        EventTicket.objects.create(
            attendee=parent,
            event=self.event,
            registration=registration,
            ticket_type=ticket_type,
        )

        response = self.client.get(self.url)

        self.assertFalse(response.data["ticket_types"][0]["available"])
        # The exact sold count is never exposed publicly, only the bool.
        self.assertNotIn("sold_count", response.data["ticket_types"][0])
        self.assertNotIn("remaining", response.data["ticket_types"][0])

    def test_cancelled_registration_frees_the_seat_again(self):
        ticket_type = TicketType.objects.create(
            event=self.event, name="Adult", price=Decimal("0"), capacity=1
        )
        registration = _make_registration(
            self.event, status=Registration.Status.CANCELLED
        )
        parent = Parent.objects.create(
            family=registration.family, first_name="Anna", relationship_type="Mother"
        )
        EventTicket.objects.create(
            attendee=parent,
            event=self.event,
            registration=registration,
            ticket_type=ticket_type,
        )

        response = self.client.get(self.url)

        self.assertTrue(response.data["ticket_types"][0]["available"])


class SoldCountsForEventQueryCountTests(TestCase):
    """R3 (gate review 2026-09-25): sold_counts_for_event must run in a
    fixed number of queries regardless of how many ticket types the event
    has. The version it replaced called ticket_type_sold_count once per
    ticket type rendered by registration_event_info/validate_promo_code —
    an N+1 on the public, unauthenticated form-load endpoint."""

    def _make_event_with_types(self, name, count):
        event = _make_event(name)
        for i in range(count):
            TicketType.objects.create(event=event, name=f"Type {i}", price=Decimal("0"))
        return event

    def test_sold_counts_for_event_query_count_is_constant(self):
        few = self._make_event_with_types("Few Types", 2)
        many = self._make_event_with_types("Many Types", 20)

        with CaptureQueriesContext(connection) as few_ctx:
            sold_counts_for_event(few)
        with CaptureQueriesContext(connection) as many_ctx:
            sold_counts_for_event(many)

        # Exactly two: one GROUP BY aggregate over EventTicket, one over
        # SessionTicket — see sold_counts_for_event's own docstring.
        self.assertEqual(len(few_ctx.captured_queries), 2, few_ctx.captured_queries)
        self.assertEqual(len(many_ctx.captured_queries), len(few_ctx.captured_queries))

    def test_registration_event_info_query_count_is_constant(self):
        """Same guarantee, exercised through the actual public endpoint —
        registration_event_info calls sold_counts_for_event once for the
        whole listing, not once per ticket type payload."""
        few = self._make_event_with_types("Few Types HTTP", 2)
        many = self._make_event_with_types("Many Types HTTP", 20)
        client = APIClient()

        with CaptureQueriesContext(connection) as few_ctx:
            few_response = client.get(f"/api/registrations/events/{few.id}/")
        with CaptureQueriesContext(connection) as many_ctx:
            many_response = client.get(f"/api/registrations/events/{many.id}/")

        self.assertEqual(few_response.status_code, 200)
        self.assertEqual(many_response.status_code, 200)
        self.assertEqual(len(few_response.data["ticket_types"]), 2)
        self.assertEqual(len(many_response.data["ticket_types"]), 20)
        self.assertEqual(
            len(few_ctx.captured_queries),
            len(many_ctx.captured_queries),
            "query count must not grow with the number of ticket types",
        )


class TicketTypeCapacityRaceTests(TransactionTestCase):
    """Real, multi-threaded concurrency for the last-seat race: two
    simultaneous submissions against a capacity=1 ticket type must yield
    exactly one winner, the same guarantee
    tests_promo_codes.py::PromoCodeMaxUsesRaceTests gives max_uses, and by
    the same means the idempotency-key reservation race
    (tests_idempotency.py::IdempotencyKeyStaleReclaimRaceTests) is tested —
    a real TransactionTestCase with two threads on two separate DB
    connections, not a single-connection mocked collision, because what's
    being proven is that a genuine SELECT ... FOR UPDATE lock wait forces
    the second transaction's count to see the first transaction's committed
    ticket."""

    def setUp(self):
        self.event = _make_event()
        self.ticket_type = TicketType.objects.create(
            event=self.event,
            name="Last Seat",
            price=Decimal("0"),
            applies_to=AppliesTo.PARENT,
            capacity=1,
        )
        self.url = "/api/registrations/"

    def _payload(self, contact_email):
        return {
            "event": str(self.event.id),
            "contact_email": contact_email,
            "parents": [
                {
                    "first_name": "Anna",
                    "relationship_type": "Mother",
                    "ticket_type": str(self.ticket_type.id),
                }
            ],
            "children": [],
        }

    @patch("registrations.views.send_verification_email", return_value=True)
    def test_two_concurrent_last_seat_submissions_yield_exactly_one_winner(
        self, mock_send
    ):
        barrier = threading.Barrier(2)
        results = []
        errors = []

        def worker(email):
            try:
                barrier.wait(timeout=5)
                client = APIClient()
                response = client.post(self.url, self._payload(email), format="json")
                results.append(response.status_code)
            except Exception as exc:  # pragma: no cover - surfaced below
                errors.append(exc)
            finally:
                connection.close()

        threads = [
            threading.Thread(target=worker, args=(f"guardian{i}@example.com",))
            for i in range(2)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        self.assertEqual(errors, [], errors)
        self.assertEqual(len(results), 2, results)
        for status_code in results:
            self.assertLess(status_code, 500, results)
        self.assertEqual(sorted(results), [201, 400])
        # Exactly one seat sold, regardless of which request "won".
        self.assertEqual(
            EventTicket.objects.filter(ticket_type=self.ticket_type).count(), 1
        )
        self.assertEqual(Registration.objects.count(), 1)


class OppositeOrderNoDeadlockTests(TransactionTestCase):
    """R1 (BLOCKING, gate review 2026-09-25): a live verifier reproduced a
    bare 500 in 5/6 opposite-order pairs under the per-attendee-lock
    version of capacity enforcement — two concurrent registrations each
    picking the same two capacity-limited ticket types in *opposite* order
    lock them in opposite order too, a textbook Postgres deadlock.
    reserve_ticket_type_capacity's single ``SELECT ... FOR UPDATE ... ORDER
    BY pk`` (registrations/services.py) fixes this by taking every lock a
    registration needs in one deterministic-order statement, regardless of
    what order the attendees arrived in.

    Both ticket types here have capacity=2 — enough for both concurrent
    registrations to succeed. The point of this test is deadlock-freedom
    specifically, not a capacity refusal (that is already covered by
    TicketTypeCapacityRaceTests above, with a single type). Real threads on
    real, separate DB connections, same reasoning as that test and as
    tests_idempotency.py::IdempotencyKeyStaleReclaimRaceTests — a
    single-connection mock cannot reproduce a genuine cross-transaction
    lock wait, let alone a deadlock between two of them.
    """

    def setUp(self):
        self.event = _make_event()
        self.type_a = TicketType.objects.create(
            event=self.event,
            name="Type A",
            price=Decimal("0"),
            applies_to=AppliesTo.PARENT,
            capacity=2,
        )
        self.type_b = TicketType.objects.create(
            event=self.event,
            name="Type B",
            price=Decimal("0"),
            applies_to=AppliesTo.PARENT,
            capacity=2,
        )
        self.url = "/api/registrations/"

    def _payload(self, *, contact_email, first_type, second_type):
        # Two parents on one registration, each picking a different type —
        # `first_type`/`second_type` control which type appears first in
        # this registration's own parents[] array, so the two threads can
        # submit the two types in opposite order.
        return {
            "event": str(self.event.id),
            "contact_email": contact_email,
            "parents": [
                {
                    "first_name": "Anna",
                    "relationship_type": "Mother",
                    "ticket_type": str(first_type.id),
                },
                {
                    "first_name": "Bo",
                    "relationship_type": "Father",
                    "ticket_type": str(second_type.id),
                },
            ],
            "children": [],
        }

    @patch("registrations.views.send_verification_email", return_value=True)
    def test_two_registrations_picking_the_same_two_types_in_opposite_order_never_deadlock(
        self, mock_send
    ):
        barrier = threading.Barrier(2)
        results = []
        errors = []

        def worker(email, first_type, second_type):
            try:
                barrier.wait(timeout=5)
                client = APIClient()
                response = client.post(
                    self.url,
                    self._payload(
                        contact_email=email,
                        first_type=first_type,
                        second_type=second_type,
                    ),
                    format="json",
                )
                results.append(response.status_code)
            except Exception as exc:  # pragma: no cover - surfaced below
                errors.append(exc)
            finally:
                connection.close()

        threads = [
            threading.Thread(
                target=worker,
                args=("regA@example.com", self.type_a, self.type_b),
            ),
            threading.Thread(
                target=worker,
                args=("regB@example.com", self.type_b, self.type_a),
            ),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        self.assertEqual(errors, [], errors)
        self.assertEqual(len(results), 2, results)
        # Never a 500 — in particular, never the bare 500 a deadlock used to
        # surface as before R1. Both registrations fit within capacity=2
        # each, so both must actually succeed, not just "not crash".
        self.assertEqual(results, [201, 201], results)
        self.assertEqual(EventTicket.objects.filter(ticket_type=self.type_a).count(), 2)
        self.assertEqual(EventTicket.objects.filter(ticket_type=self.type_b).count(), 2)


class _SimulatedPgError(Exception):
    """Stand-in for the real psycopg exception object
    _is_deadlock_or_serialization_failure reads ``.pgcode`` off — carries
    just that one attribute, nothing else about the real driver exception
    matters to the code under test."""

    def __init__(self, pgcode):
        self.pgcode = pgcode
        super().__init__(f"simulated pgcode {pgcode}")


def _raise_simulated_deadlock(*_args, **_kwargs):
    """A OperationalError shaped exactly like the real thing Django raises
    when psycopg reports a deadlock: the driver's own exception (carrying
    ``.pgcode``) attached as ``__cause__`` via ``raise ... from ...``."""
    try:
        raise _SimulatedPgError("40P01")
    except _SimulatedPgError as pg_exc:
        raise OperationalError("simulated deadlock") from pg_exc


class RegistrationBusyRetryTests(TestCase):
    """R1 defence-in-depth (gate review 2026-09-25): even with
    reserve_ticket_type_capacity's single-lock fix closing the specific
    opposite-order deadlock OppositeOrderNoDeadlockTests covers, Postgres
    can still legitimately detect and abort some deadlock or serialization
    conflict between this transaction and a completely different one —
    that must surface as a clean, retryable 503, never a bare 500.

    Mocks _execute_submit_registration itself, rather than trying to
    provoke a real deadlock from a single test thread (not possible — a
    deadlock is inherently a two-transaction phenomenon, already covered
    with real concurrency by OppositeOrderNoDeadlockTests/
    TicketTypeCapacityRaceTests above). This instead exercises
    submit_registration's own catch/translate logic directly, on both of
    its branches, via the one shared helper
    (_submit_registration_or_busy) both branches call.
    """

    def setUp(self):
        self.client = APIClient()
        self.event = _make_event()
        self.url = "/api/registrations/"

    def _payload(self, **overrides):
        payload = {
            "event": str(self.event.id),
            "contact_email": "guardian@example.com",
            "parents": [{"first_name": "Anna", "relationship_type": "Mother"}],
            "children": [],
        }
        payload.update(overrides)
        return payload

    @patch(
        "registrations.views._execute_submit_registration",
        side_effect=_raise_simulated_deadlock,
    )
    def test_no_key_branch_returns_503_with_code_and_bilingual_message(
        self, mock_execute
    ):
        response = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(response.status_code, 503, response.data)
        self.assertEqual(response.data["code"], "registration_busy_retry")
        self.assertIn("try again", response.data["error"])

    @patch(
        "registrations.views._execute_submit_registration",
        side_effect=_raise_simulated_deadlock,
    )
    def test_no_key_branch_message_is_swedish_under_accept_language_sv(
        self, mock_execute
    ):
        response = self.client.post(
            self.url, self._payload(), format="json", HTTP_ACCEPT_LANGUAGE="sv"
        )

        self.assertEqual(response.status_code, 503, response.data)
        self.assertIn("försök igen", response.data["error"])

    @patch(
        "registrations.views._execute_submit_registration",
        side_effect=_raise_simulated_deadlock,
    )
    def test_keyed_branch_returns_503_and_deletes_the_reservation(self, mock_execute):
        payload = self._payload(idempotency_key="busy-retry-key")

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 503, response.data)
        self.assertEqual(response.data["code"], "registration_busy_retry")
        self.assertFalse(
            RegistrationIdempotencyKey.objects.filter(key="busy-retry-key").exists()
        )

        # Retrying under the same key isn't permanently stuck behind a dead
        # reservation — same interplay guarantee as a capacity refusal's
        # (see RegistrationSubmitCapacityTests.
        # test_refused_submit_deletes_its_idempotency_reservation).
        mock_execute.side_effect = None
        mock_execute.return_value = (
            {"reference_code": "ABCDEFGH", "email_sent": True, "message": "ok"},
            201,
            None,
        )
        retry = self.client.post(self.url, payload, format="json")
        self.assertEqual(retry.status_code, 201, retry.data)

    @patch(
        "registrations.views._execute_submit_registration",
        side_effect=OperationalError("connection lost"),
    )
    def test_an_unrelated_operational_error_is_not_swallowed(self, mock_execute):
        """Only the two specific pgcodes (deadlock_detected,
        serialization_failure) are caught. This OperationalError has no
        __cause__ at all (unlike the simulated deadlock above), so
        _is_deadlock_or_serialization_failure must read that as "not a
        match" and let it propagate — never silently repackaged as a
        busy-retry response that would hide a real bug."""
        with self.assertRaises(OperationalError):
            self.client.post(self.url, self._payload(), format="json")
