"""
Idempotency-key protection for submit_registration.

Added 2026-09-24: an audit of the public /register/[eventId] flow found no
protection against a retried POST anywhere in the stack — see
RegistrationIdempotencyKey's docstring in models.py for the full reasoning,
and tests_dedup.py for the pre-existing (event, contact_email) dedup+resend
path this is deliberately layered *in front of* rather than folded into:
that path is for a guardian who deliberately wants a fresh email later, this
one is for an accidental retry of the exact same request that must never be
allowed to run twice.
"""

import threading
from datetime import timedelta
from unittest.mock import patch

from django.db import IntegrityError, connection
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from events.models import Event

from .models import Registration, RegistrationIdempotencyKey
from .views import _idempotency_fingerprint


def _make_event(name="Summer Camp"):
    today = timezone.now().date()
    return Event.objects.create(
        name=name,
        start_date=today,
        end_date=today,
        registration_opens_at=timezone.now() - timedelta(days=1),
    )


class RegistrationIdempotencyTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.event = _make_event()
        self.url = "/api/registrations/"

    def _payload(self, **overrides):
        payload = {
            "event": str(self.event.id),
            "contact_email": "guardian@example.com",
            "parents": [
                {
                    "first_name": "Anna",
                    "relationship_type": "Mother",
                    "email": "guardian@example.com",
                }
            ],
            "children": [],
            "idempotency_key": "11111111-1111-1111-1111-111111111111",
        }
        payload.update(overrides)
        return payload

    @patch("registrations.views.send_verification_email", return_value=True)
    def test_no_key_is_unaffected(self, mock_send):
        """The whole mechanism is opt-in — a request that omits
        idempotency_key entirely must behave exactly as it did before this
        increment (still governed by the (event, contact_email) dedup path
        in tests_dedup.py, not by anything here)."""
        payload = self._payload()
        del payload["idempotency_key"]

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Registration.objects.count(), 1)
        self.assertEqual(RegistrationIdempotencyKey.objects.count(), 0)

    @patch("registrations.views.send_verification_email", return_value=True)
    def test_first_submit_creates_and_stores_the_key(self, mock_send):
        response = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Registration.objects.count(), 1)
        key_record = RegistrationIdempotencyKey.objects.get(
            key="11111111-1111-1111-1111-111111111111"
        )
        self.assertEqual(key_record.response_status, 201)
        self.assertEqual(
            key_record.response_body["reference_code"], response.data["reference_code"]
        )
        self.assertIsNotNone(key_record.registration)

    @patch("registrations.views.send_verification_email", return_value=True)
    def test_replay_returns_original_response_without_creating_or_emailing_again(
        self, mock_send
    ):
        first = self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(mock_send.call_count, 1)

        # Retried exactly as-is — same key, same payload, as a network-retry
        # or a double submit that slipped past the frontend's own in-flight
        # guard would send it.
        second = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(second.status_code, first.status_code)
        self.assertEqual(second.data, first.data)
        self.assertEqual(Registration.objects.count(), 1)
        # The whole point: a replay must not send a second confirmation/
        # verification email.
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(RegistrationIdempotencyKey.objects.count(), 1)

    @patch("registrations.views.send_verification_email", return_value=True)
    def test_same_key_different_payload_is_a_conflict_not_a_silent_replay(
        self, mock_send
    ):
        first = self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(first.status_code, 201, first.data)

        # Same key, but the contact email (part of the payload) differs —
        # a client bug, or reuse of a key across two genuinely different
        # submissions. Must not be served the first request's result.
        response = self.client.post(
            self.url,
            self._payload(contact_email="someone-else@example.com"),
            format="json",
        )

        self.assertEqual(response.status_code, 409, response.data)
        self.assertIn("idempotency_key", response.data)
        # P1 (gate review, 2026-09-24): a machine-readable code alongside
        # the translated message, so the frontend can branch on it directly
        # rather than pattern-matching translated text — see handleSubmit's
        # catch block, which checks this before falling back to
        # extractErrorMessage's generic heuristic.
        self.assertEqual(response.data.get("code"), "idempotency_conflict")
        # No second registration, and the mismatch must not have touched
        # the first (send_verification_email called exactly once, from the
        # first request only).
        self.assertEqual(Registration.objects.count(), 1)
        self.assertEqual(mock_send.call_count, 1)

    @patch("registrations.views.send_verification_email", return_value=True)
    def test_validation_failure_does_not_permanently_block_a_retry_under_the_same_key(
        self, mock_send
    ):
        """A submission that fails before reaching a persisted outcome (here:
        no parents and no children at all, which the serializer itself
        rejects) never gets a stored response — retrying with a corrected
        payload under the *same* key must succeed, not 409 forever against
        a reservation that will never complete. See the model docstring's
        "reserve, then delete on failure" note."""
        broken_payload = self._payload(parents=[], children=[])
        broken_response = self.client.post(self.url, broken_payload, format="json")
        self.assertEqual(broken_response.status_code, 400, broken_response.data)
        self.assertEqual(RegistrationIdempotencyKey.objects.count(), 0)

        fixed_response = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(fixed_response.status_code, 201, fixed_response.data)
        self.assertEqual(Registration.objects.count(), 1)

    @patch("registrations.views.send_verification_email", return_value=True)
    def test_concurrent_request_with_an_unfinished_reservation_gets_409_not_a_guess(
        self, mock_send
    ):
        """Simulates the losing side of a true race: two requests reserve
        the same key at nearly the same instant, and this one's reservation
        INSERT hits the unique constraint because the other got there
        first — but the other hasn't finished _execute_submit_registration
        yet, so there is no response to replay. Pre-populating an
        unfinished reservation row (response_body=None) reproduces exactly
        the state submit_registration would see mid-race, without needing
        real threads against TestCase's wrapped transaction."""
        payload = self._payload()
        fingerprint = _idempotency_fingerprint(dict(payload))
        RegistrationIdempotencyKey.objects.create(
            key=payload["idempotency_key"],
            event=self.event,
            request_fingerprint=fingerprint,
        )

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 409, response.data)
        self.assertEqual(response.data.get("code"), "idempotency_in_progress")
        self.assertEqual(Registration.objects.count(), 0)
        mock_send.assert_not_called()

    @patch("registrations.views.send_verification_email", return_value=True)
    def test_concurrent_duplicate_insert_is_caught_as_integrity_error_not_two_registrations(
        self, mock_send
    ):
        """More directly exercises the "catch the IntegrityError race, not
        just check-then-insert" requirement: forces the reservation INSERT
        itself to raise IntegrityError (as the real unique constraint would
        under true concurrency) on the *second* of two back-to-back calls,
        and asserts only one Registration ever gets created."""
        real_create = RegistrationIdempotencyKey.objects.create
        call_count = {"n": 0}

        def flaky_create(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return real_create(*args, **kwargs)
            raise IntegrityError("duplicate key value violates unique constraint")

        with patch.object(
            RegistrationIdempotencyKey.objects, "create", side_effect=flaky_create
        ):
            first = self.client.post(self.url, self._payload(), format="json")
            second = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(first.status_code, 201, first.data)
        # The forced IntegrityError sends the second request down the same
        # "someone already holds this key" path a genuine race would —
        # since the first request has, in this sequential test, already
        # finished and stored its response, the second replays it verbatim
        # rather than guessing (that "still in-flight" case is covered by
        # test_concurrent_request_with_an_unfinished_reservation_gets_409_not_a_guess).
        self.assertEqual(second.status_code, first.status_code)
        self.assertEqual(second.data, first.data)
        self.assertEqual(Registration.objects.count(), 1)
        self.assertEqual(mock_send.call_count, 1)

    # -- P2: stale-reservation reclaim (gate review, 2026-09-24) ----------
    #
    # A reservation is "stale" once it's sat unfinished (response_body
    # still None) longer than views.STALE_RESERVATION_AGE (60s) — the
    # owning request presumably died (killed worker, rescheduled pod)
    # before it could fill the row in. Without a reclaim, every future
    # retry under that key would see "already being processed" forever.

    @patch("registrations.views.send_verification_email", return_value=True)
    def test_stale_unfinished_reservation_is_reclaimed_and_the_retry_succeeds(
        self, mock_send
    ):
        payload = self._payload()
        fingerprint = _idempotency_fingerprint(dict(payload))
        stale = RegistrationIdempotencyKey.objects.create(
            key=payload["idempotency_key"],
            event=self.event,
            request_fingerprint=fingerprint,
        )
        # Backdate past STALE_RESERVATION_AGE via update() (bypasses
        # auto_now_add, same trick tests_dedup.py uses for
        # verification_sent_at) — this row now looks like a reservation
        # whose owning request died over a minute ago.
        RegistrationIdempotencyKey.objects.filter(pk=stale.pk).update(
            created_at=timezone.now() - timedelta(seconds=61)
        )

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Registration.objects.count(), 1)
        mock_send.assert_called_once()
        # The stale row was reclaimed (deleted + re-reserved), not left
        # behind alongside a second one — exactly one row for this key,
        # now finished.
        key_records = RegistrationIdempotencyKey.objects.filter(
            key=payload["idempotency_key"]
        )
        self.assertEqual(key_records.count(), 1)
        self.assertIsNotNone(key_records.get().response_body)

    @patch("registrations.views.send_verification_email", return_value=True)
    def test_not_yet_stale_reservation_still_gets_in_progress_409(self, mock_send):
        """The mirror of the reclaim test above: a reservation that is
        unfinished but still *young* (well inside STALE_RESERVATION_AGE)
        must NOT be reclaimed — it might just be a genuinely fast
        concurrent request that hasn't finished yet, not an abandoned one."""
        payload = self._payload()
        fingerprint = _idempotency_fingerprint(dict(payload))
        RegistrationIdempotencyKey.objects.create(
            key=payload["idempotency_key"],
            event=self.event,
            request_fingerprint=fingerprint,
        )
        # created_at defaults to right now via auto_now_add — nowhere near
        # STALE_RESERVATION_AGE (60s).

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 409, response.data)
        self.assertEqual(response.data.get("code"), "idempotency_in_progress")
        self.assertEqual(Registration.objects.count(), 0)
        mock_send.assert_not_called()
        self.assertEqual(
            RegistrationIdempotencyKey.objects.filter(
                key=payload["idempotency_key"]
            ).count(),
            1,
        )

    # A third P2 scenario — two requests genuinely racing to reclaim the
    # same stale key — needs two real DB connections to be faithful (see
    # IdempotencyKeyStaleReclaimRaceTests below, a TransactionTestCase):
    # a single-connection mock here would have to insert a "concurrent
    # winner" row from inside the very transaction.atomic() block that's
    # about to roll back on the forced IntegrityError, which silently
    # undoes that insert right along with it — not a real race, just a
    # test that looked like one.


class IdempotencyKeyStaleReclaimRaceTests(TransactionTestCase):
    """Real, multi-threaded concurrency for the trickiest P2 case (gate
    review, 2026-09-24): two requests both see the same stale, reclaimable
    reservation and both attempt to reclaim it.

    TransactionTestCase, not TestCase, is required here. TestCase wraps an
    entire test in one shared connection/transaction (rolled back at the
    end via a savepoint), so two "concurrent" writes on it can never
    actually interleave the way two real request-handling threads — each
    with its own DB connection — do; every other race test in this file
    fakes a collision with a mocked IntegrityError on a single connection,
    which is a faithful-enough stand-in for "someone else already holds
    this key" (see test_concurrent_duplicate_insert_is_caught_as_
    integrity_error_not_two_registrations). This specific case is
    different: it depends on each side's own DELETE and retried INSERT
    becoming visible to the *other* side at exactly the right moments,
    which single-connection mocking can't reproduce (see the comment left
    in RegistrationIdempotencyTests above, where the first attempt at this
    test tried exactly that and failed for precisely this reason).
    """

    def setUp(self):
        self.event = _make_event()
        self.url = "/api/registrations/"

    @patch("registrations.views.send_verification_email", return_value=True)
    def test_two_concurrent_reclaimers_of_a_stale_key_yield_one_registration_never_500(
        self, mock_send
    ):
        key = "race-stale-key"
        payload = {
            "event": str(self.event.id),
            "contact_email": "guardian@example.com",
            "parents": [
                {
                    "first_name": "Anna",
                    "relationship_type": "Mother",
                    "email": "guardian@example.com",
                }
            ],
            "children": [],
            "idempotency_key": key,
        }
        fingerprint = _idempotency_fingerprint(dict(payload))
        stale = RegistrationIdempotencyKey.objects.create(
            key=key, event=self.event, request_fingerprint=fingerprint
        )
        RegistrationIdempotencyKey.objects.filter(pk=stale.pk).update(
            created_at=timezone.now() - timedelta(seconds=61)
        )

        # A barrier, not a sleep: both threads block until both have
        # reached this line, so the two requests actually start together
        # rather than one reliably finishing before the other begins —
        # a fixed sleep would just as reliably produce a false pass.
        barrier = threading.Barrier(2)
        results = []
        errors = []

        def worker():
            try:
                barrier.wait(timeout=5)
                client = APIClient()
                response = client.post(self.url, payload, format="json")
                results.append(response.status_code)
            except Exception as exc:  # pragma: no cover - surfaced below
                errors.append(exc)
            finally:
                # Each thread gets its own DB connection (Django connections
                # are thread-local); close it explicitly rather than
                # leaking it past the thread's lifetime.
                connection.close()

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        self.assertEqual(errors, [], errors)
        self.assertEqual(len(results), 2, results)
        # Never a 500 — every outcome the reviewed plan allows (the
        # winner's real 201, or the loser's graceful replay/409) is a
        # deliberate, resolved response, not an unhandled exception.
        for status_code in results:
            self.assertLess(status_code, 500, results)
        # Exactly one Registration, regardless of which thread "won" —
        # the whole point of the reservation-before-work ordering.
        self.assertEqual(Registration.objects.count(), 1)
        self.assertEqual(RegistrationIdempotencyKey.objects.filter(key=key).count(), 1)


class IdempotencyKeySweepTests(TestCase):
    """sweep_idempotency_keys (P3, gate review 2026-09-24) — the TTL pass
    that hard-deletes RegistrationIdempotencyKey rows once a retry of their
    original POST is no longer plausible. See tasks.py::
    IDEMPOTENCY_KEY_TTL_DAYS and the field's own SET_NULL comment in
    models.py for why an orphaned (registration=NULL) row is swept exactly
    like any other."""

    def setUp(self):
        self.event = _make_event()

    def _make_key(self, *, key, age_days, registration=None):
        record = RegistrationIdempotencyKey.objects.create(
            key=key,
            event=self.event,
            request_fingerprint="deadbeef",
            response_status=201,
            response_body={"reference_code": "ABCDEFGH"},
            registration=registration,
        )
        RegistrationIdempotencyKey.objects.filter(pk=record.pk).update(
            created_at=timezone.now() - timedelta(days=age_days)
        )
        return record

    def test_old_rows_are_deleted(self):
        from .tasks import sweep_idempotency_keys

        self._make_key(key="old-1", age_days=8)

        sweep_idempotency_keys()

        self.assertEqual(RegistrationIdempotencyKey.objects.count(), 0)

    def test_recent_rows_are_kept(self):
        from .tasks import sweep_idempotency_keys

        self._make_key(key="recent-1", age_days=1)

        sweep_idempotency_keys()

        self.assertEqual(RegistrationIdempotencyKey.objects.count(), 1)

    def test_old_orphaned_rows_are_deleted_too(self):
        """registration=NULL (SET_NULL already fired, e.g. the family was
        swept/erased) must not exempt a row from the TTL — it has exactly
        as little left to do as a non-orphaned old row."""
        from .tasks import sweep_idempotency_keys

        self._make_key(key="orphaned-old", age_days=8, registration=None)

        sweep_idempotency_keys()

        self.assertEqual(RegistrationIdempotencyKey.objects.count(), 0)
