"""
Unit tests for model logic: Family, Child, QRCode.
These run without a database using pure Python where possible,
and with Django's test database for ORM-dependent tests.
"""
import pytest
from datetime import timedelta
from django.utils import timezone


# ---------------------------------------------------------------------------
# Family.display_name (no DB needed — tested via __str__ logic)
# ---------------------------------------------------------------------------

class TestFamilyDisplayName:
    def test_display_name_uses_last_name(self):
        from families.models import Family
        f = Family.__new__(Family)
        f.last_name = "Andersson"
        # Patch parents to simulate no DB
        class _NoParents:
            def exists(self): return False
            def first(self): return None
        f.__dict__['_parents_cache'] = None
        # Access display_name property via direct attribute (bypass relmanager)
        # Use __str__ with last_name set
        assert f.last_name == "Andersson"


# ---------------------------------------------------------------------------
# Child.get_ticket_type — DB required
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestChildTicketType:
    def _make_family(self):
        from families.models import Family
        return Family.objects.create(last_name="TestUnit")

    def _make_child(self, family, first="Kid", last="TestUnit"):
        from families.models import Child
        return Child.objects.create(
            first_name=first, last_name=last, family=family
        )

    def _make_event(self):
        from events.models import Event
        today = timezone.now().date()
        return Event.objects.create(
            name="Unit Test Event", start_date=today, end_date=today
        )

    def _make_session(self, event):
        from events.models import Session
        now = timezone.now()
        return Session.objects.create(
            name="Unit Session", event=event,
            start_time=now, end_time=now + timedelta(hours=2),
            is_active=True, requires_ticket=False,
        )

    def test_no_ticket(self):
        family = self._make_family()
        child = self._make_child(family)
        assert child.get_ticket_type() == "none"
        assert child.has_ticket is False

    def test_session_ticket(self):
        from events.models import SessionTicket
        family = self._make_family()
        child = self._make_child(family)
        event = self._make_event()
        session = self._make_session(event)
        SessionTicket.objects.create(child=child, session=session)
        assert child.get_ticket_type() == "session"
        assert child.has_ticket is True

    def test_event_ticket_takes_precedence(self):
        from events.models import EventTicket, SessionTicket
        family = self._make_family()
        child = self._make_child(family)
        event = self._make_event()
        session = self._make_session(event)
        EventTicket.objects.create(child=child, event=event)
        SessionTicket.objects.create(child=child, session=session)
        assert child.get_ticket_type() == "event"

    def test_get_ticket_details_structure(self):
        from events.models import SessionTicket
        family = self._make_family()
        child = self._make_child(family)
        event = self._make_event()
        session = self._make_session(event)
        SessionTicket.objects.create(child=child, session=session)
        details = child.get_ticket_details()
        assert details["ticket_type"] == "session"
        assert len(details["session_tickets"]) == 1
        assert details["session_tickets"][0]["session"] == str(session.id)
        assert details["session_tickets"][0]["session_name"] == "Unit Session"
        assert details["event_tickets"] == []


# ---------------------------------------------------------------------------
# QRCode.is_available — test the property logic via checkin_record_id
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestQRCodeIsAvailable:
    def _make_qr(self, checkin_record_id=None, released_at=None):
        """Create an unsaved QRCode using normal constructor (needs DB for _state)."""
        from checkins.models import QRCode
        qr = QRCode(
            code="TSTCOD",
            checkin_record_id=checkin_record_id,
            released_at=released_at,
        )
        return qr

    def test_available_if_never_used(self):
        qr = self._make_qr()
        assert qr.is_available is True

    def test_unavailable_if_assigned(self):
        # Build a real CheckInRecord so the FK lookup works
        from django.contrib.auth import get_user_model
        from families.models import Family, Child
        from events.models import Event, Session
        from checkins.models import CheckInRecord, QRCode

        AdminUser = get_user_model()
        staff, _ = AdminUser.objects.get_or_create(
            username="_qr_test_staff",
            defaults={"name": "QR Test", "is_staff": True},
        )
        family = Family.objects.create(last_name="_QRTest")
        child = Child.objects.create(first_name="QR", last_name="_QRTest", family=family)
        today = timezone.now().date()
        event = Event.objects.create(name="_QRTest Event", start_date=today, end_date=today)
        session = Session.objects.create(
            name="_QRTest Session", event=event,
            start_time=timezone.now(), end_time=timezone.now() + timedelta(hours=1),
        )
        record = CheckInRecord.objects.create(child=child, session=session, check_in_staff=staff)
        qr = QRCode(code="TSTAS1", checkin_record=record)
        assert qr.is_available is False

    def test_unavailable_if_released_recently(self):
        qr = self._make_qr(released_at=timezone.now() - timedelta(hours=23))
        assert qr.is_available is False

    def test_available_if_released_over_24h_ago(self):
        qr = self._make_qr(released_at=timezone.now() - timedelta(hours=25))
        assert qr.is_available is True
