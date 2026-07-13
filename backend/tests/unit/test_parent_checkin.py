"""
Unit / API-level tests for parent (guardian) check-in behaviour.

These tests exercise the check_in view action and the print-queue endpoint at
the HTTP level, using APIClient with force_authenticate so no login flow is
needed.  They run against the live dev PostgreSQL (config.settings.local) just
like the other unit tests in this package.

URL resolution
--------------
  router basename "checkin" → action "check_in"  → "checkin-check-in"
                                                    → /api/checkins/check_in/
  router basename "print-queue"                   → "print-queue-list"
                                                    → /api/print-queue/

MTI downcast note
-----------------
Django multi-table inheritance does not return the concrete subclass:
``Attendee.objects.get()`` always yields a plain ``Attendee`` instance, so a
bare ``isinstance(attendee, Parent)`` is always ``False``.  The check_in view
resolves the concrete ``Parent`` explicitly (``Parent.objects.filter(pk=...)``)
so the parent branch actually runs.  These tests assert the resulting correct
behaviour: parents require a ticket, are pre-marked ``label_printed`` so they
never enter the label queue, and are exempt from the single-session block.
"""

import pytest
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APIClient

from families.models import Child, Family, Parent
from events.models import Event, EventTicket, Session, SessionTicket
from checkins.models import CheckInRecord

AdminUser = get_user_model()

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

CHECKIN_URL = reverse("checkin-check-in")
PRINT_QUEUE_URL = reverse("print-queue-list")


def _make_staff(username: str) -> AdminUser:
    return AdminUser.objects.create_user(username=username, is_staff=True)


def _make_family(last_name: str = "TestFamily") -> Family:
    return Family.objects.create(last_name=last_name)


def _make_parent(family: Family, first: str = "Alice") -> Parent:
    return Parent.objects.create(
        first_name=first,
        last_name="TestParent",
        family=family,
        relationship_type="Parent",
    )


def _make_child(family: Family, first: str = "Charlie") -> Child:
    return Child.objects.create(
        first_name=first,
        last_name="TestChild",
        family=family,
    )


def _make_event() -> Event:
    today = timezone.now().date()
    return Event.objects.create(name="Test Event", start_date=today, end_date=today)


def _make_session(
    event: Event,
    name: str = "Session A",
    parent_checkin_policy: str = Session.ParentCheckinPolicy.TICKET_REQUIRED,
) -> Session:
    now = timezone.now()
    return Session.objects.create(
        name=name,
        event=event,
        start_time=now,
        end_time=now + timedelta(hours=2),
        is_active=True,
        requires_ticket=False,
        # Defaults to ticket_required so existing ticket-gate tests below
        # keep testing what their names say regardless of the system-wide
        # default (Event.parent_checkin_policy_default is "open").
        parent_checkin_policy=parent_checkin_policy,
    )


def _authed_client(staff: AdminUser) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=staff)
    return client


# ---------------------------------------------------------------------------
# Test classes
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestParentCheckIn:
    """Parent-specific check-in behaviour."""

    # 1 -----------------------------------------------------------------------
    def test_parent_with_ticket_can_check_in(self):
        """A parent with a SessionTicket should be accepted (201) and be
        pre-marked ``label_printed`` so they never enter the label queue."""
        staff = _make_staff("pci_staff_1")
        family = _make_family("Pci1")
        parent = _make_parent(family)
        event = _make_event()
        session = _make_session(event)
        SessionTicket.objects.create(attendee=parent, session=session)

        client = _authed_client(staff)
        resp = client.post(
            CHECKIN_URL,
            {"child": str(parent.id), "session": str(session.id)},
            format="json",
        )

        assert resp.status_code == 201, resp.data

        record = CheckInRecord.objects.get(attendee_id=parent.id)
        assert record.check_out_time is None
        # Parents are pre-marked printed so they never enter the label queue.
        assert record.label_printed is True

    # 2 -----------------------------------------------------------------------
    def test_parent_without_ticket_rejected(self):
        """A parent with no ticket must be rejected with 400 (parent ticket
        gate)."""
        staff = _make_staff("pci_staff_2")
        family = _make_family("Pci2")
        parent = _make_parent(family)
        event = _make_event()
        session = _make_session(event)
        # Intentionally no ticket created

        client = _authed_client(staff)
        resp = client.post(
            CHECKIN_URL,
            {"child": str(parent.id), "session": str(session.id)},
            format="json",
        )

        assert resp.status_code == 400
        assert "ticket" in resp.data["error"].lower()

    # 3 -----------------------------------------------------------------------
    def test_checked_in_parent_excluded_from_print_queue(self):
        """After checking in both a parent and a child to the same session,
        the print-queue should contain the child but NOT the parent.

        The parent is pre-marked ``label_printed`` (test 1) and
        PrintQueueViewSet.get_queryset additionally filters out Parent
        attendee IDs, so parents never appear in the queue.
        """
        staff = _make_staff("pci_staff_3")
        family = _make_family("Pci3")
        parent = _make_parent(family)
        child = _make_child(family)
        event = _make_event()
        session = _make_session(event)
        SessionTicket.objects.create(attendee=parent, session=session)
        SessionTicket.objects.create(attendee=child, session=session)

        client = _authed_client(staff)

        resp_parent = client.post(
            CHECKIN_URL,
            {"child": str(parent.id), "session": str(session.id)},
            format="json",
        )
        assert resp_parent.status_code == 201, resp_parent.data

        resp_child = client.post(
            CHECKIN_URL,
            {"child": str(child.id), "session": str(session.id)},
            format="json",
        )
        assert resp_child.status_code == 201, resp_child.data

        parent_record_id = str(CheckInRecord.objects.get(attendee_id=parent.id).id)
        child_record_id = str(CheckInRecord.objects.get(attendee_id=child.id).id)

        queue_resp = client.get(PRINT_QUEUE_URL)
        assert queue_resp.status_code == 200

        result_ids = [str(item["id"]) for item in queue_resp.data]
        assert child_record_id in result_ids, "Child record should be in print queue"
        assert parent_record_id not in result_ids, (
            "Parent record must NOT be in print queue"
        )

    # 4 -----------------------------------------------------------------------
    def test_parent_allowed_in_multiple_sessions(self):
        """Parents are NOT subject to the single-session block: checking a
        parent into two simultaneous sessions should both succeed."""
        staff = _make_staff("pci_staff_4")
        family = _make_family("Pci4")
        parent = _make_parent(family)
        event = _make_event()
        session_a = _make_session(event, name="Session A")
        session_b = _make_session(event, name="Session B")
        EventTicket.objects.create(attendee=parent, event=event)

        client = _authed_client(staff)

        resp_a = client.post(
            CHECKIN_URL,
            {"child": str(parent.id), "session": str(session_a.id)},
            format="json",
        )
        assert resp_a.status_code == 201, resp_a.data

        resp_b = client.post(
            CHECKIN_URL,
            {"child": str(parent.id), "session": str(session_b.id)},
            format="json",
        )
        assert resp_b.status_code == 201, resp_b.data

        active_count = CheckInRecord.objects.filter(
            attendee_id=parent.id, check_out_time__isnull=True
        ).count()
        assert active_count == 2

    # 5 -----------------------------------------------------------------------
    def test_parent_duplicate_same_session_rejected(self):
        """Attempting to check a parent into the same session twice (while still
        active) should return 400 via the parent duplicate-session guard."""
        staff = _make_staff("pci_staff_5")
        family = _make_family("Pci5")
        parent = _make_parent(family)
        event = _make_event()
        session = _make_session(event)
        SessionTicket.objects.create(attendee=parent, session=session)

        client = _authed_client(staff)

        resp1 = client.post(
            CHECKIN_URL,
            {"child": str(parent.id), "session": str(session.id)},
            format="json",
        )
        assert resp1.status_code == 201, resp1.data

        resp2 = client.post(
            CHECKIN_URL,
            {"child": str(parent.id), "session": str(session.id)},
            format="json",
        )
        assert resp2.status_code == 400
        assert "error" in resp2.data
        assert "already" in resp2.data["error"].lower()

    # 6 -----------------------------------------------------------------------
    def test_child_single_session_block_still_enforced(self):
        """Regression guard: a child checked into session A should be blocked
        from checking into session B (non-supervised).  The parent check-in
        path must not have inadvertently relaxed child rules.

        The child is given an EventTicket so has_ticket is satisfied for both
        sessions; the block must come from the active-check-in guard, not from
        missing tickets.
        """
        staff = _make_staff("pci_staff_6")
        family = _make_family("Pci6")
        child = _make_child(family)
        event = _make_event()
        session_a = _make_session(event, name="Session A")
        session_b = _make_session(event, name="Session B")
        EventTicket.objects.create(attendee=child, event=event)

        client = _authed_client(staff)

        resp_a = client.post(
            CHECKIN_URL,
            {"child": str(child.id), "session": str(session_a.id)},
            format="json",
        )
        assert resp_a.status_code == 201, resp_a.data

        resp_b = client.post(
            CHECKIN_URL,
            {"child": str(child.id), "session": str(session_b.id)},
            format="json",
        )
        assert resp_b.status_code == 400
        assert "error" in resp_b.data
        assert (
            "active" in resp_b.data["error"].lower()
            or "session" in resp_b.data["error"].lower()
        )

    # 7 -----------------------------------------------------------------------
    def test_parent_cannot_be_checked_out(self):
        """Parents are check-in only (no checkout — by design). The check_out
        action must reject it even though nothing else prevents the HTTP call
        from reaching it (no checkout button is rendered in the UI for parents,
        but that's not a security boundary)."""
        staff = _make_staff("pci_staff_7")
        family = _make_family("Pci7")
        parent = _make_parent(family)
        event = _make_event()
        session = _make_session(event)
        SessionTicket.objects.create(attendee=parent, session=session)

        client = _authed_client(staff)
        resp = client.post(
            CHECKIN_URL,
            {"child": str(parent.id), "session": str(session.id)},
            format="json",
        )
        assert resp.status_code == 201, resp.data
        record_id = CheckInRecord.objects.get(attendee_id=parent.id).id

        resp = client.post(reverse("checkin-check-out", args=[record_id]))
        assert resp.status_code == 400
        assert "error" in resp.data

        record = CheckInRecord.objects.get(id=record_id)
        assert record.check_out_time is None


@pytest.mark.django_db
class TestQrInfoAttendeeType:
    """The QR-info endpoint must distinguish Child vs Parent attendees.

    Django MTI does not downcast ``checkin.attendee``, so the endpoint resolves
    the concrete Child explicitly.  Otherwise every QR lookup would report
    ``is_parent`` and silently blank out child allergies / birthdate / notes —
    a safety regression, since the QR page surfaces allergy info.
    """

    def _checkin(self, client, attendee, session) -> str:
        resp = client.post(
            CHECKIN_URL,
            {"child": str(attendee.id), "session": str(session.id)},
            format="json",
        )
        assert resp.status_code == 201, resp.data
        return CheckInRecord.objects.get(attendee_id=attendee.id).qr_code.code

    def test_qr_info_for_child_includes_allergies(self):
        staff = _make_staff("qri_staff_1")
        family = _make_family("Qri1")
        child = Child.objects.create(
            first_name="Charlie",
            last_name="QriChild",
            family=family,
            allergies="Peanuts",
            birthdate=timezone.now().date(),
        )
        event = _make_event()
        session = _make_session(event)
        EventTicket.objects.create(attendee=child, event=event)

        client = _authed_client(staff)
        code = self._checkin(client, child, session)

        resp = client.get(reverse("qr-info", args=[code]))
        assert resp.status_code == 200, resp.data
        assert resp.data["child"]["is_parent"] is False
        assert resp.data["child"]["allergies"] == "Peanuts"
        assert resp.data["child"]["birthdate"] is not None

    def test_qr_info_for_parent_marks_is_parent(self):
        staff = _make_staff("qri_staff_2")
        family = _make_family("Qri2")
        parent = _make_parent(family)
        event = _make_event()
        session = _make_session(event)
        SessionTicket.objects.create(attendee=parent, session=session)

        client = _authed_client(staff)
        code = self._checkin(client, parent, session)

        resp = client.get(reverse("qr-info", args=[code]))
        assert resp.status_code == 200, resp.data
        assert resp.data["child"]["is_parent"] is True
        assert resp.data["child"]["allergies"] == ""
        assert resp.data["child"]["birthdate"] is None

    def test_qr_info_omits_allergies_and_notes_for_anonymous_caller(self):
        """9.3-style gate: an anonymous caller gets has_safety_info only,
        never the text itself — see qr_reveal_safety_info for the actual
        reveal path."""
        staff = _make_staff("qri_staff_3")
        family = _make_family("Qri3")
        child = Child.objects.create(
            first_name="Dana",
            last_name="QriChild",
            family=family,
            allergies="Peanuts",
            notes="Epilepsy",
            birthdate=timezone.now().date(),
        )
        event = _make_event()
        session = _make_session(event)
        EventTicket.objects.create(attendee=child, event=event)

        staff_client = _authed_client(staff)
        code = self._checkin(staff_client, child, session)

        anon_resp = APIClient().get(reverse("qr-info", args=[code]))
        assert anon_resp.status_code == 200, anon_resp.data
        assert anon_resp.data["child"]["allergies"] is None
        assert anon_resp.data["child"]["notes"] is None
        assert anon_resp.data["child"]["has_safety_info"] is True

        # Authenticated response is unchanged by this gate.
        staff_resp = staff_client.get(reverse("qr-info", args=[code]))
        assert staff_resp.data["child"]["allergies"] == "Peanuts"
        assert staff_resp.data["child"]["notes"] == "Epilepsy"
        assert staff_resp.data["child"]["has_safety_info"] is True

    def test_qr_info_has_safety_info_false_when_no_allergies_or_notes(self):
        staff = _make_staff("qri_staff_4")
        family = _make_family("Qri4")
        child = Child.objects.create(
            first_name="Eli",
            last_name="QriChild",
            family=family,
            birthdate=timezone.now().date(),
        )
        event = _make_event()
        session = _make_session(event)
        EventTicket.objects.create(attendee=child, event=event)

        staff_client = _authed_client(staff)
        code = self._checkin(staff_client, child, session)

        anon_resp = APIClient().get(reverse("qr-info", args=[code]))
        assert anon_resp.status_code == 200, anon_resp.data
        assert anon_resp.data["child"]["has_safety_info"] is False


@pytest.mark.django_db
class TestQrRevealSafetyInfo:
    """POST /api/qr/{code}/reveal-safety-info/ — the anonymous, throttled,
    individually audit-logged path to allergy/emergency-medical text."""

    def _checkin(self, client, attendee, session) -> str:
        resp = client.post(
            CHECKIN_URL,
            {"child": str(attendee.id), "session": str(session.id)},
            format="json",
        )
        assert resp.status_code == 201, resp.data
        return CheckInRecord.objects.get(attendee_id=attendee.id).qr_code.code

    def test_reveal_returns_allergies_and_notes_for_anonymous_caller(self):
        staff = _make_staff("qrr_staff_1")
        family = _make_family("Qrr1")
        child = Child.objects.create(
            first_name="Finn",
            last_name="QrrChild",
            family=family,
            allergies="Peanuts",
            notes="Epilepsy",
            birthdate=timezone.now().date(),
        )
        event = _make_event()
        session = _make_session(event)
        EventTicket.objects.create(attendee=child, event=event)

        staff_client = _authed_client(staff)
        code = self._checkin(staff_client, child, session)

        resp = APIClient().post(reverse("qr-reveal-safety-info", args=[code]))
        assert resp.status_code == 200, resp.data
        assert resp.data["allergies"] == "Peanuts"
        assert resp.data["notes"] == "Epilepsy"

    def test_reveal_404_for_invalid_code(self):
        resp = APIClient().post(reverse("qr-reveal-safety-info", args=["ZZZZZ"]))
        assert resp.status_code == 404

    def test_reveal_404_when_child_checked_out(self):
        staff = _make_staff("qrr_staff_2")
        family = _make_family("Qrr2")
        child = Child.objects.create(
            first_name="Gwen",
            last_name="QrrChild",
            family=family,
            allergies="Peanuts",
            birthdate=timezone.now().date(),
        )
        event = _make_event()
        session = _make_session(event)
        EventTicket.objects.create(attendee=child, event=event)

        staff_client = _authed_client(staff)
        code = self._checkin(staff_client, child, session)
        record = CheckInRecord.objects.get(attendee_id=child.id)
        checkout_resp = staff_client.post(
            reverse("checkin-check-out", args=[record.id]), {}, format="json"
        )
        assert checkout_resp.status_code == 200, checkout_resp.data

        resp = APIClient().post(reverse("qr-reveal-safety-info", args=[code]))
        assert resp.status_code == 404

    def test_reveal_respects_quarantine_policy(self):
        """A needs_reconfirmation child still reveals text — same safety
        rationale as qr_info's own quarantine display policy (DPIA §4)."""
        staff = _make_staff("qrr_staff_3")
        family = _make_family("Qrr3")
        child = Child.objects.create(
            first_name="Hana",
            last_name="QrrChild",
            family=family,
            allergies="Peanuts",
            health_consent_status=Child.HealthConsentStatus.NEEDS_RECONFIRMATION,
            birthdate=timezone.now().date(),
        )
        event = _make_event()
        session = _make_session(event)
        EventTicket.objects.create(attendee=child, event=event)

        staff_client = _authed_client(staff)
        code = self._checkin(staff_client, child, session)

        resp = APIClient().post(reverse("qr-reveal-safety-info", args=[code]))
        assert resp.status_code == 200, resp.data
        assert resp.data["allergies"] == "Peanuts"

    def test_reveal_blank_for_parent_self_checkin(self):
        staff = _make_staff("qrr_staff_4")
        family = _make_family("Qrr4")
        parent = _make_parent(family)
        event = _make_event()
        session = _make_session(event)
        SessionTicket.objects.create(attendee=parent, session=session)

        staff_client = _authed_client(staff)
        code = self._checkin(staff_client, parent, session)

        resp = APIClient().post(reverse("qr-reveal-safety-info", args=[code]))
        assert resp.status_code == 200, resp.data
        assert resp.data["allergies"] == ""
        assert resp.data["notes"] == ""


@pytest.mark.django_db
class TestParentCheckinPolicy:
    """Session.effective_parent_checkin_policy gates parent check-in — see
    checkins/eligibility.py parent_checkin_gate_error, the single source of
    truth used by both the check_in view and CheckInRecordSerializer."""

    def _check_in(self, client, parent, session):
        return client.post(
            CHECKIN_URL,
            {"child": str(parent.id), "session": str(session.id)},
            format="json",
        )

    def test_open_policy_allows_checkin_without_ticket(self):
        staff = _make_staff("pcp_staff_1")
        family = _make_family("Pcp1")
        parent = _make_parent(family)
        event = _make_event()
        session = _make_session(
            event, parent_checkin_policy=Session.ParentCheckinPolicy.OPEN
        )
        # Intentionally no ticket.

        resp = self._check_in(_authed_client(staff), parent, session)
        assert resp.status_code == 201, resp.data

    def test_disabled_policy_rejects_even_with_ticket(self):
        staff = _make_staff("pcp_staff_2")
        family = _make_family("Pcp2")
        parent = _make_parent(family)
        event = _make_event()
        session = _make_session(
            event, parent_checkin_policy=Session.ParentCheckinPolicy.DISABLED
        )
        SessionTicket.objects.create(attendee=parent, session=session)

        resp = self._check_in(_authed_client(staff), parent, session)
        assert resp.status_code == 400
        assert "not enabled" in resp.data["error"].lower()
        assert not CheckInRecord.objects.filter(attendee_id=parent.id).exists()

    def test_ticket_required_policy_rejects_without_ticket(self):
        staff = _make_staff("pcp_staff_3")
        family = _make_family("Pcp3")
        parent = _make_parent(family)
        event = _make_event()
        session = _make_session(
            event, parent_checkin_policy=Session.ParentCheckinPolicy.TICKET_REQUIRED
        )

        resp = self._check_in(_authed_client(staff), parent, session)
        assert resp.status_code == 400
        assert "ticket" in resp.data["error"].lower()

    def test_blank_session_policy_inherits_event_default(self):
        staff = _make_staff("pcp_staff_4")
        family = _make_family("Pcp4")
        parent = _make_parent(family)
        event = _make_event()
        event.parent_checkin_policy_default = Session.ParentCheckinPolicy.DISABLED
        event.save(update_fields=["parent_checkin_policy_default"])
        # parent_checkin_policy left blank ("") — must inherit the event default.
        session = _make_session(event, parent_checkin_policy="")

        assert (
            session.effective_parent_checkin_policy
            == Session.ParentCheckinPolicy.DISABLED
        )
        resp = self._check_in(_authed_client(staff), parent, session)
        assert resp.status_code == 400
        assert "not enabled" in resp.data["error"].lower()

    def test_session_policy_overrides_event_default(self):
        staff = _make_staff("pcp_staff_5")
        family = _make_family("Pcp5")
        parent = _make_parent(family)
        event = _make_event()
        event.parent_checkin_policy_default = Session.ParentCheckinPolicy.DISABLED
        event.save(update_fields=["parent_checkin_policy_default"])
        session = _make_session(
            event, parent_checkin_policy=Session.ParentCheckinPolicy.OPEN
        )

        assert (
            session.effective_parent_checkin_policy == Session.ParentCheckinPolicy.OPEN
        )
        resp = self._check_in(_authed_client(staff), parent, session)
        assert resp.status_code == 201, resp.data
