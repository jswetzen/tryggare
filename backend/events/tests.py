"""
Tests for event ticket models and API endpoints.
"""

from datetime import date
from unittest.mock import patch, AsyncMock

from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from events.models import (
    Event,
    Extra,
    ExtraChoice,
    EventTicket,
    RegistrationWindowStatus,
    Session,
    SessionTicket,
    TicketType,
)
from families.models import Child, Family, Parent
from accounts.models import AdminUser
from accounts.roles import COORDINATOR, grant


class TicketModelTest(TestCase):
    """Test the polymorphic ticket models."""

    def setUp(self):
        """Set up test data."""
        self.family = Family.objects.create()
        self.child = Child.objects.create(
            family=self.family,
            first_name="Test",
            last_name="Child",
            birthdate=timezone.now().date(),
        )
        self.event = Event.objects.create(
            name="Test Event",
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
        )
        self.session = Session.objects.create(
            event=self.event,
            name="Test Session",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=2),
            is_active=True,
        )

    def test_create_event_ticket(self):
        """Test creating an event ticket."""
        ticket = EventTicket.objects.create(attendee=self.child, event=self.event)
        self.assertEqual(ticket.attendee, self.child)
        self.assertEqual(ticket.event, self.event)
        self.assertIn(str(self.child), str(ticket))
        self.assertIn(str(self.event), str(ticket))

    def test_create_session_ticket(self):
        """Test creating a session ticket."""
        ticket = SessionTicket.objects.create(attendee=self.child, session=self.session)
        self.assertEqual(ticket.attendee, self.child)
        self.assertEqual(ticket.session, self.session)
        self.assertIn(str(self.child), str(ticket))
        self.assertIn(str(self.session), str(ticket))

    def test_event_ticket_unique_constraint(self):
        """Test that a child cannot have duplicate event tickets."""
        EventTicket.objects.create(attendee=self.child, event=self.event)

        # Try to create a duplicate
        with self.assertRaises(Exception):  # Will raise IntegrityError
            EventTicket.objects.create(attendee=self.child, event=self.event)

    def test_session_ticket_unique_constraint(self):
        """Test that a child cannot have duplicate session tickets."""
        SessionTicket.objects.create(attendee=self.child, session=self.session)

        # Try to create a duplicate
        with self.assertRaises(Exception):  # Will raise IntegrityError
            SessionTicket.objects.create(attendee=self.child, session=self.session)

    def test_child_can_have_both_ticket_types(self):
        """Test that a child can have both event and session tickets."""
        event_ticket = EventTicket.objects.create(attendee=self.child, event=self.event)
        session_ticket = SessionTicket.objects.create(
            attendee=self.child, session=self.session
        )

        self.assertEqual(self.child.event_tickets.count(), 1)
        self.assertEqual(self.child.session_tickets.count(), 1)
        self.assertEqual(self.child.event_tickets.first(), event_ticket)
        self.assertEqual(self.child.session_tickets.first(), session_ticket)


class TicketAPITest(TestCase):
    """Test the ticket API endpoints."""

    def setUp(self):
        """Set up test data and authentication."""
        self.client = APIClient()
        self.user = AdminUser.objects.create_user(
            username="testuser", password="testpass123", name="Test User"
        )
        grant(self.user, COORDINATOR)
        self.client.force_authenticate(user=self.user)

        self.family = Family.objects.create()
        self.child = Child.objects.create(
            family=self.family,
            first_name="Test",
            last_name="Child",
            birthdate=timezone.now().date(),
        )
        self.event = Event.objects.create(
            name="Test Event",
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
        )
        self.session = Session.objects.create(
            event=self.event,
            name="Test Session",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=2),
        )

    def test_list_event_tickets(self):
        """Test listing event tickets."""
        EventTicket.objects.create(attendee=self.child, event=self.event)

        response = self.client.get("/api/event-tickets/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["ticket_type"], "EVENT_PASS")

    def test_create_event_ticket(self):
        """Test creating an event ticket via API."""
        data = {"child": str(self.child.id), "event": str(self.event.id)}
        response = self.client.post("/api/event-tickets/", data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(EventTicket.objects.count(), 1)

    def test_list_session_tickets(self):
        """Test listing session tickets."""
        SessionTicket.objects.create(attendee=self.child, session=self.session)

        response = self.client.get("/api/session-tickets/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["ticket_type"], "SESSION_TICKET")

    def test_create_session_ticket(self):
        """Test creating a session ticket via API."""
        data = {"child": str(self.child.id), "session": str(self.session.id)}
        response = self.client.post("/api/session-tickets/", data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(SessionTicket.objects.count(), 1)

    def test_filter_tickets_by_child(self):
        """Test filtering tickets by child."""
        # First, ensure no tickets exist from previous tests
        EventTicket.objects.all().delete()

        family2 = Family.objects.create()
        child2 = Child.objects.create(
            family=family2,
            first_name="Other",
            last_name="Child",
            birthdate=timezone.now().date(),
        )

        EventTicket.objects.create(attendee=self.child, event=self.event)
        EventTicket.objects.create(attendee=child2, event=self.event)

        response = self.client.get(f"/api/event-tickets/?attendee={self.child.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(response.data),
            1,
            f"Expected 1 ticket, got {len(response.data)}: {response.data}",
        )
        # The response uses "child" key for back-compat
        self.assertEqual(str(response.data[0]["child"]), str(self.child.id))

    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated users cannot access ticket endpoints."""
        self.client.force_authenticate(user=None)

        response = self.client.get("/api/event-tickets/")
        self.assertEqual(response.status_code, 403)

        response = self.client.get("/api/session-tickets/")
        self.assertEqual(response.status_code, 403)


class AutoCheckoutOnDeactivateTest(TestCase):
    """Test that deactivating a session auto-checks out all open check-ins."""

    def setUp(self):
        self.staff = AdminUser.objects.create_user(
            username="autotest_staff",
            password="testpass123",
            name="Auto Test Staff",
        )
        self.family = Family.objects.create()
        self.child1 = Child.objects.create(
            family=self.family,
            first_name="Alice",
            last_name="Test",
            birthdate=timezone.now().date(),
        )
        self.child2 = Child.objects.create(
            family=self.family,
            first_name="Bob",
            last_name="Test",
            birthdate=timezone.now().date(),
        )
        self.event = Event.objects.create(
            name="Auto Test Event",
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
        )
        self.session = Session.objects.create(
            event=self.event,
            name="Auto Test Session",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=2),
            is_active=True,
        )

    def _make_checkin(self, child):
        from checkins.models import CheckInRecord

        return CheckInRecord.objects.create(
            attendee=child,
            session=self.session,
            check_in_staff=self.staff,
        )

    @patch("events.signals.get_channel_layer")
    def test_deactivating_session_checks_out_all_open_records(self, mock_get_layer):
        """Deactivating an active session auto-checks out open check-in records."""
        mock_layer = AsyncMock()
        mock_get_layer.return_value = mock_layer

        record1 = self._make_checkin(self.child1)
        record2 = self._make_checkin(self.child2)

        self.session.is_active = False
        self.session.save()

        record1.refresh_from_db()
        record2.refresh_from_db()

        self.assertIsNotNone(record1.check_out_time)
        self.assertIsNotNone(record2.check_out_time)
        self.assertIsNone(record1.check_out_staff)
        self.assertIsNone(record2.check_out_staff)

    @patch("events.signals.get_channel_layer")
    def test_deactivating_session_creates_audit_logs(self, mock_get_layer):
        """Auto-checkout creates AuditLog entries with user=None."""
        mock_layer = AsyncMock()
        mock_get_layer.return_value = mock_layer

        from checkins.models import AuditLog

        self._make_checkin(self.child1)

        self.session.is_active = False
        self.session.save()

        log = AuditLog.objects.filter(action="auto_check_out").first()
        self.assertIsNotNone(log)
        self.assertIsNone(log.user)
        self.assertEqual(log.details["reason"], "session_deactivated")

    @patch("events.signals.get_channel_layer")
    def test_deactivating_session_with_no_open_checkins_is_safe(self, mock_get_layer):
        """Deactivating a session with no open check-ins does not raise an error."""
        mock_layer = AsyncMock()
        mock_get_layer.return_value = mock_layer

        # No check-ins created — should not raise
        self.session.is_active = False
        self.session.save()

    @patch("events.signals.get_channel_layer")
    def test_already_inactive_session_save_does_not_trigger(self, mock_get_layer):
        """Saving an already-inactive session does not double-checkout."""
        mock_layer = AsyncMock()
        mock_get_layer.return_value = mock_layer

        from checkins.models import AuditLog

        self._make_checkin(self.child1)

        # First deactivation
        self.session.is_active = False
        self.session.save()

        audit_count_after_first = AuditLog.objects.filter(
            action="auto_check_out"
        ).count()

        # Second save of same inactive session (e.g. other field change)
        self.session.name = "Renamed"
        self.session.save()

        audit_count_after_second = AuditLog.objects.filter(
            action="auto_check_out"
        ).count()
        self.assertEqual(audit_count_after_first, audit_count_after_second)

    @patch("events.signals.get_channel_layer")
    def test_reactivating_session_does_not_checkout(self, mock_get_layer):
        """Activating (True) or re-activating a session does not trigger checkout."""
        mock_layer = AsyncMock()
        mock_get_layer.return_value = mock_layer

        from checkins.models import AuditLog

        self._make_checkin(self.child1)

        # Save without changing is_active (still True)
        self.session.name = "Renamed Active"
        self.session.save()

        self.assertEqual(AuditLog.objects.filter(action="auto_check_out").count(), 0)

    @patch("events.signals.get_channel_layer")
    def test_standard_checkin_can_move_to_new_session_after_auto_checkout(
        self, mock_get_layer
    ):
        """After auto-checkout, a standard check-in can check into another session."""
        mock_layer = AsyncMock()
        mock_get_layer.return_value = mock_layer

        from checkins.models import CheckInRecord

        self._make_checkin(self.child1)

        # Deactivate the session → triggers auto-checkout
        self.session.is_active = False
        self.session.save()

        # Create a new active session
        new_session = Session.objects.create(
            event=self.event,
            name="New Session",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=2),
            is_active=True,
        )

        # child1 should now be checkable into the new session (no open records)
        open_standard = CheckInRecord.objects.filter(
            attendee=self.child1,
            check_out_time__isnull=True,
            supervised=False,
        ).exclude(session=new_session)
        self.assertFalse(open_standard.exists())


class TicketTypeExtraModelTest(TestCase):
    """Phase 3 itemization models: TicketType, Extra, ExtraChoice."""

    def setUp(self):
        self.event = Event.objects.create(
            name="Summer Camp",
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timezone.timedelta(days=2),
        )
        self.session = Session.objects.create(
            event=self.event,
            name="Saturday",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=8),
        )
        self.family = Family.objects.create()
        self.child = Child.objects.create(
            family=self.family,
            first_name="Ebba",
            last_name="Test",
            birthdate=timezone.now().date(),
        )

    def test_ticket_type_str(self):
        ticket_type = TicketType.objects.create(
            event=self.event, name="Child 0-12", price=400
        )
        self.assertEqual(str(ticket_type), "Summer Camp - Child 0-12")

    def test_ticket_type_defaults(self):
        ticket_type = TicketType.objects.create(
            event=self.event, name="Adult", price=1100
        )
        self.assertEqual(ticket_type.applies_to, "either")
        self.assertEqual(ticket_type.kind, TicketType.Kind.EVENT)
        self.assertTrue(ticket_type.is_active)
        self.assertFalse(ticket_type.is_hidden)
        self.assertIsNone(ticket_type.capacity)

    def test_ticket_type_session_bundle(self):
        ticket_type = TicketType.objects.create(
            event=self.event,
            name="Saturday only",
            price=350,
            kind=TicketType.Kind.SESSION_BUNDLE,
        )
        ticket_type.sessions.add(self.session)
        self.assertIn(self.session, ticket_type.sessions.all())
        self.assertIn(ticket_type, self.session.bundle_ticket_types.all())

    def test_clean_accepts_age_bounds_on_event_start_anniversaries(self):
        """Task #19: age is judged once, on the event's start date. A bound
        that lands exactly on an anniversary of that date states that rule
        and must be accepted."""
        start = self.event.start_date
        ticket_type = TicketType(
            event=self.event,
            name="Barn 0-12",
            price=400,
            max_birthdate=start.replace(year=start.year - 12),
        )
        ticket_type.full_clean()  # must not raise

        youth = TicketType(
            event=self.event,
            name="Ungdom 13-17",
            price=700,
            min_birthdate=start.replace(year=start.year - 18)
            + timezone.timedelta(days=1),
            max_birthdate=start.replace(year=start.year - 13),
        )
        youth.full_clean()  # must not raise

    def test_clean_rejects_max_birthdate_off_the_anniversary(self):
        from django.core.exceptions import ValidationError

        start = self.event.start_date
        ticket_type = TicketType(
            event=self.event,
            name="Barn 0-12",
            price=400,
            max_birthdate=start.replace(year=start.year - 12)
            - timezone.timedelta(days=1),
        )
        with self.assertRaises(ValidationError) as ctx:
            ticket_type.full_clean()
        self.assertIn("max_birthdate", ctx.exception.message_dict)

    def test_clean_rejects_min_birthdate_off_the_anniversary(self):
        from django.core.exceptions import ValidationError

        start = self.event.start_date
        ticket_type = TicketType(
            event=self.event,
            name="Ungdom 13-17",
            price=700,
            min_birthdate=start.replace(year=start.year - 18),
        )
        with self.assertRaises(ValidationError) as ctx:
            ticket_type.full_clean()
        self.assertIn("min_birthdate", ctx.exception.message_dict)

    def test_clean_allows_blank_bounds_regardless_of_event_start(self):
        # Blank means "deliberately unrestricted", not "unconfigured" — no
        # anniversary requirement applies to a bound that isn't set.
        ticket_type = TicketType(event=self.event, name="Vuxen", price=1100)
        ticket_type.full_clean()  # must not raise

    def test_admin_form_rejects_session_bundle_with_no_sessions(self):
        """A2: staff-facing backstop — TicketTypeAdminForm.clean() must
        reject this at save time rather than silently producing a
        zero-SessionTicket ticket type."""
        from events.admin import TicketTypeAdminForm

        form = TicketTypeAdminForm(
            data={
                "event": str(self.event.id),
                "name": "Saturday only",
                "price": "350",
                "applies_to": "either",
                "kind": TicketType.Kind.SESSION_BUNDLE,
                "sort_order": "0",
                "is_active": "on",
                "sessions": [],
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn(
            "session",
            str(form.errors).lower(),
        )

    def test_admin_form_accepts_session_bundle_with_a_session(self):
        from events.admin import TicketTypeAdminForm

        form = TicketTypeAdminForm(
            data={
                "event": str(self.event.id),
                "name": "Saturday only",
                "price": "350",
                "applies_to": "either",
                "kind": TicketType.Kind.SESSION_BUNDLE,
                "sort_order": "0",
                "is_active": "on",
                "sessions": [str(self.session.id)],
            }
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_extra_choice_relation(self):
        extra = Extra.objects.create(
            event=self.event, name="T-shirt", requires_choice=True
        )
        small = ExtraChoice.objects.create(extra=extra, label="S")
        large = ExtraChoice.objects.create(
            extra=extra, label="L", price_delta=20, sort_order=1
        )
        self.assertEqual(list(extra.choice_rows.all()), [small, large])
        self.assertEqual(str(small), "T-shirt - S")

    def test_extra_session_scoping(self):
        extra = Extra.objects.create(
            event=self.event, name="Saturday dinner", session=self.session, price=150
        )
        self.assertEqual(extra.session, self.session)
        self.assertIn(extra, self.session.extras.all())

    def test_event_ticket_protects_ticket_type_from_deletion(self):
        ticket_type = TicketType.objects.create(
            event=self.event, name="Child 0-12", price=400
        )
        EventTicket.objects.create(
            attendee=self.child,
            event=self.event,
            ticket_type=ticket_type,
            price_at_registration=400,
        )
        with self.assertRaises(Exception):
            ticket_type.delete()

    def test_registration_extra_protects_extra_from_deletion(self):
        from registrations.models import Registration, RegistrationExtra

        extra = Extra.objects.create(event=self.event, name="Cabin", per_attendee=False)
        registration = Registration.objects.create(
            event=self.event,
            family=self.family,
            contact_email="a@example.com",
            verification_token_hash="x" * 64,
        )
        RegistrationExtra.objects.create(
            registration=registration,
            extra=extra,
            attendee=None,
            price_at_registration=0,
        )
        with self.assertRaises(Exception):
            extra.delete()

    def test_registration_extra_unique_per_attendee(self):
        from django.db import IntegrityError, transaction

        from registrations.models import Registration, RegistrationExtra

        extra = Extra.objects.create(event=self.event, name="Lunch", price=50)
        registration = Registration.objects.create(
            event=self.event,
            family=self.family,
            contact_email="a@example.com",
            verification_token_hash="y" * 64,
        )
        RegistrationExtra.objects.create(
            registration=registration,
            extra=extra,
            attendee=self.child,
            price_at_registration=50,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                RegistrationExtra.objects.create(
                    registration=registration,
                    extra=extra,
                    attendee=self.child,
                    price_at_registration=50,
                )


class ExtraDuplicationTest(TestCase):
    """Reusable-extras via clone: events/services.py::duplicate_extra_to_event
    plus the Extra.origin / lineage_siblings lineage helpers it feeds."""

    def setUp(self):
        self.event = Event.objects.create(
            name="Summer Camp",
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timezone.timedelta(days=2),
        )
        self.other_event = Event.objects.create(
            name="Winter Retreat",
            start_date=timezone.now().date() + timezone.timedelta(days=90),
            end_date=timezone.now().date() + timezone.timedelta(days=92),
        )
        self.session = Session.objects.create(
            event=self.event,
            name="Saturday",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=8),
        )

    def test_duplicate_copies_fields_and_choices(self):
        from events.services import duplicate_extra_to_event

        extra = Extra.objects.create(
            event=self.event,
            name="T-shirt",
            price=100,
            per_attendee=True,
            applies_to="child",
            requires_choice=True,
            required=True,
            default_selected=True,
            sort_order=3,
            is_active=True,
        )
        small = ExtraChoice.objects.create(extra=extra, label="S", price_delta=0)
        large = ExtraChoice.objects.create(
            extra=extra, label="L", price_delta=20, sort_order=1
        )

        clone = duplicate_extra_to_event(extra, self.other_event)

        self.assertNotEqual(clone.id, extra.id)
        self.assertEqual(clone.event, self.other_event)
        self.assertEqual(clone.name, "T-shirt")
        self.assertEqual(clone.price, extra.price)
        self.assertEqual(clone.per_attendee, extra.per_attendee)
        self.assertEqual(clone.applies_to, extra.applies_to)
        self.assertEqual(clone.requires_choice, extra.requires_choice)
        self.assertEqual(clone.required, extra.required)
        self.assertEqual(clone.default_selected, extra.default_selected)
        self.assertEqual(clone.sort_order, extra.sort_order)
        self.assertEqual(clone.is_active, extra.is_active)
        self.assertEqual(clone.cloned_from, extra)

        clone_labels = set(clone.choice_rows.values_list("label", "price_delta"))
        self.assertEqual(
            clone_labels,
            {("S", small.price_delta), ("L", large.price_delta)},
        )
        # Choice rows are independent copies, not the same rows.
        self.assertFalse(clone.choice_rows.filter(id__in=[small.id, large.id]).exists())

    def test_duplicate_clears_session_across_events(self):
        from events.services import duplicate_extra_to_event

        extra = Extra.objects.create(
            event=self.event, name="Saturday dinner", session=self.session, price=150
        )

        clone = duplicate_extra_to_event(extra, self.other_event)

        self.assertIsNone(clone.session)

    def test_duplicate_preserves_session_within_same_event(self):
        from events.services import duplicate_extra_to_event

        extra = Extra.objects.create(
            event=self.event, name="Saturday dinner", session=self.session, price=150
        )

        clone = duplicate_extra_to_event(extra, self.event)

        self.assertEqual(clone.session, self.session)

    def test_duplicate_leaves_source_untouched(self):
        from events.services import duplicate_extra_to_event

        extra = Extra.objects.create(event=self.event, name="Parking", price=30)

        duplicate_extra_to_event(extra, self.other_event)
        extra.refresh_from_db()

        self.assertEqual(extra.event, self.event)
        self.assertEqual(extra.price, 30)
        self.assertIsNone(extra.cloned_from)

    def test_origin_and_lineage_siblings_across_a_chain(self):
        from events.services import duplicate_extra_to_event

        third_event = Event.objects.create(
            name="Autumn Weekend",
            start_date=timezone.now().date() + timezone.timedelta(days=180),
            end_date=timezone.now().date() + timezone.timedelta(days=182),
        )

        a = Extra.objects.create(event=self.event, name="T-shirt", price=100)
        b = duplicate_extra_to_event(a, self.other_event)
        c = duplicate_extra_to_event(b, third_event)

        self.assertEqual(a.origin, a)
        self.assertEqual(b.origin, a)
        self.assertEqual(c.origin, a)

        self.assertEqual(set(a.lineage_siblings()), {b, c})
        self.assertEqual(set(b.lineage_siblings()), {a, c})
        self.assertEqual(set(c.lineage_siblings()), {a, b})

    def test_extra_with_no_clones_has_empty_lineage(self):
        extra = Extra.objects.create(event=self.event, name="Parking", price=30)

        self.assertEqual(extra.origin, extra)
        self.assertEqual(extra.lineage_siblings(), [])


class RegistrationWindowStatusTest(TestCase):
    """Event.registration_window_status — the actual enforcement point for
    the public registration endpoint gate, and what the landing page reads
    to decide what to show (see event_registration_ux_case_catalog.md,
    punch-list item 13: nothing gated the public endpoint before this)."""

    def _make_event(self, **kwargs):
        return Event.objects.create(
            name="Camp",
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
            **kwargs,
        )

    def test_both_unset_is_not_configured(self):
        event = self._make_event()
        self.assertEqual(
            event.registration_window_status, RegistrationWindowStatus.NOT_CONFIGURED
        )

    def test_before_opens_at_is_not_open_yet(self):
        event = self._make_event(
            registration_opens_at=timezone.now() + timezone.timedelta(days=1)
        )
        self.assertEqual(
            event.registration_window_status, RegistrationWindowStatus.NOT_OPEN_YET
        )

    def test_within_window_is_open(self):
        event = self._make_event(
            registration_opens_at=timezone.now() - timezone.timedelta(days=1),
            registration_closes_at=timezone.now() + timezone.timedelta(days=1),
        )
        self.assertEqual(
            event.registration_window_status, RegistrationWindowStatus.OPEN
        )

    def test_open_ended_after_opens_at_is_open(self):
        event = self._make_event(
            registration_opens_at=timezone.now() - timezone.timedelta(days=1)
        )
        self.assertEqual(
            event.registration_window_status, RegistrationWindowStatus.OPEN
        )

    def test_after_closes_at_is_closed(self):
        event = self._make_event(
            registration_opens_at=timezone.now() - timezone.timedelta(days=2),
            registration_closes_at=timezone.now() - timezone.timedelta(days=1),
        )
        self.assertEqual(
            event.registration_window_status, RegistrationWindowStatus.CLOSED
        )

    def test_closes_at_only_is_open_before_deadline(self):
        event = self._make_event(
            registration_closes_at=timezone.now() + timezone.timedelta(days=1)
        )
        self.assertEqual(
            event.registration_window_status, RegistrationWindowStatus.OPEN
        )

    def test_clean_rejects_closes_at_before_opens_at(self):
        """D2: this misconfiguration reads as NOT_OPEN_YET/CLOSED forever —
        registration_window_status itself has no way to flag it, so
        Event.clean() must catch it at save time."""
        from django.core.exceptions import ValidationError

        event = self._make_event(
            registration_opens_at=timezone.now() + timezone.timedelta(days=2),
            registration_closes_at=timezone.now() + timezone.timedelta(days=1),
        )
        with self.assertRaises(ValidationError):
            event.full_clean()

    def test_clean_allows_closes_at_after_opens_at(self):
        event = self._make_event(
            registration_opens_at=timezone.now() - timezone.timedelta(days=1),
            registration_closes_at=timezone.now() + timezone.timedelta(days=1),
        )
        event.full_clean()  # must not raise


# The project ships WhiteNoise's manifest static storage, which refuses to
# resolve admin CSS unless collectstatic has run. Rendering an admin page in
# a test is unrelated to static-asset hashing, so swap in the plain backend.
@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    }
)
class TicketTriageAdminTest(TestCase):
    """The failure this exists to prevent: a coordinator was told "a family
    says their 13-year-old is on the 0-12 ticket, fix it" and gave up after
    20+ minutes, because no screen showed a child's name, age and ticket
    type together. These tests pin the columns, the search, and the age
    arithmetic that make that a one-screen answer."""

    @classmethod
    def setUpTestData(cls):
        cls.user = AdminUser.objects.create_superuser("triage", "pw12345")
        # A five-day summer camp. Deliberately fixed dates, not relative to
        # today: the birthday-boundary assertions below only mean anything
        # against a known event window.
        cls.event = Event.objects.create(
            name="Sommarläger 2026",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 5),
        )
        cls.session = Session.objects.create(
            event=cls.event,
            name="Kväll 1",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=2),
        )
        cls.child_type = TicketType.objects.create(
            event=cls.event, name="Barn 0-12", price=0
        )
        cls.youth_type = TicketType.objects.create(
            event=cls.event, name="Ungdom 13-17", price=500
        )
        cls.family = Family.objects.create(last_name="Lindqvist")
        # Already 13 on the first day of the event, sitting on the 0-12
        # ticket — the exact row the coordinator could not find.
        cls.alva = Child.objects.create(
            family=cls.family,
            first_name="Alva",
            last_name="Lindqvist",
            birthdate=date(2013, 6, 15),
        )
        cls.alva_ticket = EventTicket.objects.create(
            attendee=cls.alva, event=cls.event, ticket_type=cls.child_type
        )
        # Turns 13 *during* the event (3 July). Correct answer at event
        # start is 12, so this child is legitimately on the 0-12 ticket.
        cls.nils = Child.objects.create(
            family=cls.family,
            first_name="Nils",
            last_name="Lindqvist",
            birthdate=date(2013, 7, 3),
        )
        cls.nils_ticket = EventTicket.objects.create(
            attendee=cls.nils, event=cls.event, ticket_type=cls.child_type
        )
        # Birthday falls exactly on the event's first day: already 13.
        cls.saga = Child.objects.create(
            family=cls.family,
            first_name="Saga",
            last_name="Lindqvist",
            birthdate=date(2013, 7, 1),
        )
        cls.saga_ticket = EventTicket.objects.create(
            attendee=cls.saga, event=cls.event, ticket_type=cls.child_type
        )

    def setUp(self):
        self.client.force_login(self.user)

    def _admin(self, model):
        # Looked up at call time rather than cached on the class:
        # setUpTestData deep-copies class attributes, and an AdminSite is
        # not deep-copyable (it holds module references).
        from django.contrib.admin.sites import site

        return site._registry[model]

    # --- age arithmetic -------------------------------------------------

    def test_age_at_event_is_whole_years_on_the_first_day(self):
        model_admin = self._admin(EventTicket)
        self.assertEqual(model_admin.age_at_event(self.alva_ticket), 13)

    def test_age_at_event_does_not_count_a_birthday_during_the_event(self):
        """Nils turns 13 on 3 July, mid-event. Age is measured at
        event.start_date (1 July), so he is 12 — consistent with
        reports.services, which buckets the same child the same way."""
        model_admin = self._admin(EventTicket)
        self.assertEqual(model_admin.age_at_event(self.nils_ticket), 12)

    def test_age_at_event_counts_a_birthday_on_the_first_day(self):
        model_admin = self._admin(EventTicket)
        self.assertEqual(model_admin.age_at_event(self.saga_ticket), 13)

    def test_age_at_event_matches_reports_services(self):
        """One age calculation, not two — a second implementation would
        eventually disagree with the reports snapshot on a boundary."""
        from reports.services import age_on

        model_admin = self._admin(EventTicket)
        for ticket, child in (
            (self.alva_ticket, self.alva),
            (self.nils_ticket, self.nils),
            (self.saga_ticket, self.saga),
        ):
            self.assertEqual(
                model_admin.age_at_event(ticket),
                age_on(child.birthdate, self.event.start_date),
            )

    def test_age_at_event_is_blank_without_a_birthdate(self):
        child = Child.objects.create(
            family=self.family, first_name="Okänd", last_name="Lindqvist"
        )
        ticket = EventTicket.objects.create(attendee=child, event=self.event)
        self.assertIsNone(self._admin(EventTicket).age_at_event(ticket))

    def test_age_at_event_is_blank_for_a_parent_ticket(self):
        """Tickets point at Attendee; birthdate only exists on the Child
        subclass, so a parent's ticket must render blank rather than
        raising Child.DoesNotExist."""
        parent = Parent.objects.create(
            family=self.family, first_name="Karin", last_name="Lindqvist"
        )
        ticket = EventTicket.objects.create(attendee=parent, event=self.event)
        self.assertIsNone(self._admin(EventTicket).age_at_event(ticket))

    def test_session_ticket_age_uses_the_events_start_date(self):
        ticket = SessionTicket.objects.create(
            attendee=self.nils, session=self.session, ticket_type=self.child_type
        )
        self.assertEqual(self._admin(SessionTicket).age_at_event(ticket), 12)

    # --- the changelist itself ------------------------------------------

    def test_event_ticket_changelist_renders_age_and_ticket_type(self):
        response = self.client.get(reverse("admin:events_eventticket_changelist"))
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("Barn 0-12", body)
        self.assertIn("Alva", body)
        self.assertIn("Lindqvist", body)

    def test_session_ticket_changelist_renders(self):
        SessionTicket.objects.create(
            attendee=self.alva, session=self.session, ticket_type=self.child_type
        )
        response = self.client.get(reverse("admin:events_sessionticket_changelist"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Barn 0-12", response.content.decode())

    def test_search_finds_a_child_by_first_name(self):
        """The abandoned job's first blocker: no ticket screen could be
        searched by a child's name."""
        response = self.client.get(
            reverse("admin:events_eventticket_changelist"), {"q": "Alva"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [t.pk for t in response.context["cl"].result_list], [self.alva_ticket.pk]
        )

    def test_search_finds_a_child_by_family_last_name(self):
        response = self.client.get(
            reverse("admin:events_eventticket_changelist"), {"q": "Lindqvist"}
        )
        self.assertEqual(len(response.context["cl"].result_list), 3)

    def test_search_finds_a_ticket_by_external_code(self):
        ticket = EventTicket.objects.create(
            attendee=Child.objects.create(
                family=self.family, first_name="Ext", last_name="Lindqvist"
            ),
            event=self.event,
            external_ticket_code="ETK-4711",
        )
        response = self.client.get(
            reverse("admin:events_eventticket_changelist"), {"q": "ETK-4711"}
        )
        self.assertEqual(
            [t.pk for t in response.context["cl"].result_list], [ticket.pk]
        )

    def test_ticket_type_filter_narrows_the_changelist(self):
        EventTicket.objects.create(
            attendee=Child.objects.create(
                family=self.family,
                first_name="Teen",
                last_name="Lindqvist",
                birthdate=date(2010, 1, 1),
            ),
            event=self.event,
            ticket_type=self.youth_type,
        )
        response = self.client.get(
            reverse("admin:events_eventticket_changelist"),
            {"ticket_type__id__exact": str(self.child_type.id)},
        )
        self.assertEqual(len(response.context["cl"].result_list), 3)

    def test_registration_status_column(self):
        from registrations.models import Registration

        registration = Registration.objects.create(
            event=self.event,
            family=self.family,
            contact_email="karin@example.com",
            verification_token_hash="a" * 64,
            status=Registration.Status.CONFIRMED,
        )
        self.alva_ticket.registration = registration
        self.alva_ticket.save(update_fields=["registration"])
        model_admin = self._admin(EventTicket)
        self.assertEqual(
            model_admin.registration_status(
                EventTicket.objects.get(pk=self.alva_ticket.pk)
            ),
            "Confirmed",
        )
        self.assertIsNone(model_admin.registration_status(self.nils_ticket))

    # --- N+1 guard ------------------------------------------------------

    def test_changelist_query_count_does_not_scale_with_rows(self):
        """age_at_event/family/registration_status are per-row Python, which
        is exactly where an N+1 hides. Same page, 3 rows vs 33 rows: the
        query count must not move."""
        url = reverse("admin:events_eventticket_changelist")
        self.client.get(url)  # warm any per-process caches

        with CaptureQueriesContext(connection) as small:
            self.client.get(url)
        baseline = len(small.captured_queries)

        for i in range(30):
            child = Child.objects.create(
                family=Family.objects.create(last_name=f"Extra{i}"),
                first_name=f"Barn{i}",
                last_name=f"Extra{i}",
                birthdate=date(2012, 3, 4),
            )
            EventTicket.objects.create(
                attendee=child, event=self.event, ticket_type=self.child_type
            )

        with CaptureQueriesContext(connection) as large:
            response = self.client.get(url)
        self.assertEqual(len(response.context["cl"].result_list), 33)
        self.assertEqual(
            len(large.captured_queries),
            baseline,
            f"changelist query count moved from {baseline} (3 rows) to "
            f"{len(large.captured_queries)} (33 rows) — an N+1 crept in",
        )

    def test_changelist_query_count_does_not_scale_with_filter_options(self):
        """The ticket_type sidebar renders str(TicketType), which
        interpolates the type's event name — stock RelatedFieldListFilter
        pays a query per option. TicketTypeListFilter pre-joins it."""
        url = reverse("admin:events_eventticket_changelist")
        self.client.get(url)

        with CaptureQueriesContext(connection) as small:
            self.client.get(url)
        baseline = len(small.captured_queries)

        for i in range(20):
            TicketType.objects.create(event=self.event, name=f"Typ {i}", price=i)

        with CaptureQueriesContext(connection) as large:
            self.client.get(url)
        self.assertEqual(len(large.captured_queries), baseline)
