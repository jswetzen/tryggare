"""
Tests for event ticket models and API endpoints.
"""

from unittest.mock import patch, AsyncMock

from django.test import TestCase
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
from families.models import Child, Family
from accounts.models import AdminUser


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
