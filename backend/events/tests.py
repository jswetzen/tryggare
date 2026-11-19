"""
Tests for event ticket models and API endpoints.
"""

from datetime import UTC, date, datetime
from unittest.mock import patch, AsyncMock

from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from events.event_spec import SpecError
from events.models import (
    AppliesTo,
    Event,
    Extra,
    ExtraChoice,
    PromoCode,
    EventTicket,
    RegistrationWindowStatus,
    Session,
    SessionTicket,
    TicketType,
)
from families.models import Child, Family, Parent
from accounts.models import AdminUser
from accounts.roles import COORDINATOR, grant
from tests.support import NonManifestStaticfilesTestCase


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

    def test_clean_error_message_survives_a_leap_day_anniversary(self):
        """A leap-year 28 February start must still produce a 400, not a 500.

        The message for min_birthdate is built from ``start + 1 day``, which
        for 2028-02-28 is 29 February. Shifting that back a flat 18 years
        lands on 2010, which has no 29 February, and ``date.replace`` raises
        ValueError — from inside the branch whose whole job is to raise a
        *ValidationError*. ``full_clean`` only catches ValidationError, so the
        operator would have got a bare 500 in place of the one message that
        explains the mistake they just made.
        """
        from django.core.exceptions import ValidationError

        leap_event = Event.objects.create(
            name="Skottårsläger",
            start_date=timezone.datetime(2028, 2, 28).date(),
            end_date=timezone.datetime(2028, 3, 1).date(),
        )
        ticket_type = TicketType(
            event=leap_event,
            name="Ungdom",
            price=700,
            min_birthdate=timezone.datetime(2010, 1, 1).date(),
        )
        with self.assertRaises(ValidationError) as ctx:
            ticket_type.full_clean()
        self.assertIn("min_birthdate", ctx.exception.message_dict)

        # The example offered has to be a value that would itself pass this
        # check — for a 29 February anniversary, only another 29 February.
        message = ctx.exception.message_dict["min_birthdate"][0]
        self.assertIn("2008-02-29", message)

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


class TicketTypeAdminAgeWindowWarningTest(NonManifestStaticfilesTestCase, TestCase):
    """The increment following 7cda9ae: warn (don't block) when applies_to
    makes an age window uncheckable. See events/admin.py::
    TicketTypeAdmin._warn_if_age_window_uncheckable — must agree with
    registrations/services.py::UNCHECKABLE_AGE_FIT_Q: the window can only
    ever be evaluated against a Child's birthdate, and a Parent attendee
    (which applies_to=PARENT steers this ticket type toward) never has
    one."""

    @classmethod
    def setUpTestData(cls):
        cls.admin_user = AdminUser.objects.create_superuser("age-admin", "pw12345")
        cls.event = Event.objects.create(
            name="Winter Camp",
            start_date=date(2027, 1, 10),
            end_date=date(2027, 1, 12),
        )

    def setUp(self):
        self.client.force_login(self.admin_user)

    def _post_add(self, **overrides):
        start = self.event.start_date
        data = {
            "event": str(self.event.id),
            "name": "Föräldrabiljett",
            "price": "100",
            "applies_to": AppliesTo.EITHER,
            "kind": TicketType.Kind.EVENT,
            "sort_order": "0",
            "sessions": [],
        }
        data.update(overrides)
        return self.client.post(reverse("admin:events_tickettype_add"), data=data)

    def test_warns_when_parent_only_type_has_an_age_window(self):
        start = self.event.start_date
        response = self._post_add(
            applies_to=AppliesTo.PARENT,
            max_birthdate=start.replace(year=start.year - 18).isoformat(),
        )
        # "Warn, don't block": the save must have succeeded (redirect to
        # the changelist), not re-rendered the add form with errors.
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            TicketType.objects.filter(
                event=self.event, applies_to=AppliesTo.PARENT
            ).exists()
        )
        follow = self.client.get(response.url)
        messages = [str(m) for m in follow.context["messages"]]
        self.assertTrue(
            any("will never actually be evaluated" in m for m in messages),
            messages,
        )

    def test_no_warning_for_a_normal_checkable_configuration(self):
        start = self.event.start_date
        response = self._post_add(
            applies_to=AppliesTo.CHILD,
            max_birthdate=start.replace(year=start.year - 12).isoformat(),
        )
        self.assertEqual(response.status_code, 302)
        follow = self.client.get(response.url)
        messages = [str(m) for m in follow.context["messages"]]
        self.assertFalse(
            any("will never actually be evaluated" in m for m in messages), messages
        )

    def test_no_warning_when_parent_only_type_has_no_age_window(self):
        response = self._post_add(applies_to=AppliesTo.PARENT)
        self.assertEqual(response.status_code, 302)
        follow = self.client.get(response.url)
        messages = [str(m) for m in follow.context["messages"]]
        self.assertFalse(
            any("will never actually be evaluated" in m for m in messages), messages
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


class CopyEventTest(TestCase):
    """events/services.py::copy_event."""

    def setUp(self):
        # The source window (March 2027) must stay in the future of the test clock.
        patcher = patch(
            "django.utils.timezone.now",
            return_value=datetime(2026, 11, 19, 12, 0, tzinfo=UTC),
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.tz = timezone.get_default_timezone()
        self.source = Event.objects.create(
            name="Spring Camp",
            start_date=date(2027, 3, 20),
            end_date=date(2027, 3, 22),
            ticket_rule_default="children",
            price=250,
            registration_opens_at=self._stockholm(2027, 3, 1, 8, 0),
            registration_closes_at=self._stockholm(2027, 3, 15, 23, 59),
            header_image_url="https://example.com/hero.png",
            accent_color="#2563EB",
        )
        self.sat = Session.objects.create(
            event=self.source,
            name="Saturday",
            start_time=self._stockholm(2027, 3, 20, 9, 0),
            end_time=self._stockholm(2027, 3, 20, 17, 0),
            is_active=True,
            ticket_rule="all",
            adults_not_checked_in=True,
        )
        self.sun = Session.objects.create(
            event=self.source,
            name="Sunday",
            start_time=self._stockholm(2027, 3, 21, 9, 0),
            end_time=self._stockholm(2027, 3, 21, 12, 0),
        )
        self.family_type = TicketType.objects.create(
            event=self.source, name="Family", price=400, sort_order=1
        )
        self.child_type = TicketType.objects.create(
            event=self.source,
            name="Child",
            price=100,
            applies_to="child",
            min_birthdate=date(2015, 3, 21),
            max_birthdate=date(2022, 3, 20),
            available_from=self._stockholm(2027, 3, 1, 8, 0),
            available_until=self._stockholm(2027, 3, 10, 12, 0),
            capacity=30,
            requires_ticket_type=self.family_type,
            max_per_required=4,
            is_active=False,
            is_hidden=True,
        )
        self.day_type = TicketType.objects.create(
            event=self.source,
            name="Saturday only",
            price=80,
            kind=TicketType.Kind.SESSION_BUNDLE,
        )
        self.day_type.sessions.set([self.sat])
        self.dinner = Extra.objects.create(
            event=self.source, session=self.sat, name="Dinner", price=60
        )
        ExtraChoice.objects.create(extra=self.dinner, label="Veg", price_delta=0)
        ExtraChoice.objects.create(
            extra=self.dinner, label="Meat", price_delta=10, is_active=False
        )
        self.shirt = Extra.objects.create(
            event=self.source, name="T-shirt", price=100, is_active=False
        )
        self.promo = PromoCode.objects.create(
            event=self.source,
            code="early",
            discount_type="percent",
            discount_value=10,
            max_uses=5,
            uses_count=3,
            valid_from=self._stockholm(2027, 3, 1, 0, 0),
            valid_until=self._stockholm(2027, 3, 10, 23, 59),
            is_active=False,
        )
        self.promo.applies_to_ticket_types.set([self.family_type])
        self.promo.unlocks_ticket_types.set([self.child_type])

    def _stockholm(self, *args):
        return timezone.make_aware(datetime(*args), self.tz)

    def _copy(self, start=date(2027, 4, 3)):
        from events.services import copy_event

        return copy_event(self.source, name="Spring Camp II", start_date=start)

    def test_copies_event_settings_and_shifts_dates(self):
        new = self._copy()

        self.assertNotEqual(new.pk, self.source.pk)
        self.assertEqual(new.name, "Spring Camp II")
        self.assertEqual(new.cloned_from, self.source)
        self.assertEqual(new.start_date, date(2027, 4, 3))
        self.assertEqual(new.end_date, date(2027, 4, 5))
        self.assertEqual(new.ticket_rule_default, "children")
        self.assertEqual(new.price, 250)
        self.assertEqual(new.header_image_url, "https://example.com/hero.png")
        self.assertEqual(new.accent_color, "#2563EB")
        self.assertEqual(
            timezone.localtime(new.registration_opens_at, self.tz).date(),
            date(2027, 3, 15),
        )
        closes = timezone.localtime(new.registration_closes_at, self.tz)
        self.assertEqual(
            (closes.date(), closes.hour, closes.minute), (date(2027, 3, 29), 23, 59)
        )
        self.assertEqual(list(self.source.copies.all()), [new])

    def test_datetimes_keep_wall_clock_across_dst(self):
        # Clocks go forward on 2027-03-28; 09:00 must stay 09:00 local.
        new = self._copy()

        start = new.sessions.get(name="Saturday").start_time
        self.assertEqual(self.sat.start_time.astimezone(UTC).hour, 8)
        self.assertEqual(timezone.localtime(start, self.tz).hour, 9)
        self.assertEqual(start.astimezone(UTC).hour, 7)
        self.assertEqual(timezone.localtime(start, self.tz).date(), date(2027, 4, 3))

    def test_negative_shift_across_dst(self):
        new = self._copy(start=date(2027, 3, 6))

        start = timezone.localtime(
            new.sessions.get(name="Saturday").start_time, self.tz
        )
        self.assertEqual((start.date(), start.hour), (date(2027, 3, 6), 9))

    def test_sessions_copied(self):
        new = self._copy()

        sat = new.sessions.get(name="Saturday")
        self.assertNotEqual(sat.pk, self.sat.pk)
        self.assertTrue(self.sat.is_active)
        self.assertFalse(sat.is_active)
        self.assertEqual(sat.ticket_rule, "all")
        self.assertTrue(sat.adults_not_checked_in)
        self.assertEqual(
            timezone.localtime(sat.end_time, self.tz).replace(tzinfo=None),
            datetime(2027, 4, 3, 17, 0),
        )
        self.assertFalse(new.sessions.get(name="Sunday").is_active)
        self.assertEqual(new.sessions.count(), 2)

    def test_ticket_types_copied_with_remapped_references(self):
        new = self._copy()

        types = {t.name: t for t in new.ticket_types.all()}
        self.assertEqual(set(types), {"Family", "Child", "Saturday only"})
        old_ids = {self.family_type.pk, self.child_type.pk, self.day_type.pk}
        self.assertFalse(old_ids & {t.pk for t in types.values()})

        child = types["Child"]
        self.assertEqual(child.requires_ticket_type, types["Family"])
        self.assertEqual(child.max_per_required, 4)
        self.assertEqual(child.capacity, 30)
        self.assertEqual(child.applies_to, "child")
        self.assertTrue(child.is_hidden)
        self.assertFalse(child.is_active)
        self.assertEqual(types["Family"].price, 400)
        self.assertEqual(types["Family"].sort_order, 1)

        bundle = types["Saturday only"]
        self.assertEqual(bundle.kind, TicketType.Kind.SESSION_BUNDLE)
        self.assertEqual(
            set(bundle.sessions.all()), {new.sessions.get(name="Saturday")}
        )

    def test_ticket_type_dates_and_birthdate_bounds_shift(self):
        new = self._copy()  # +14 days

        child = new.ticket_types.get(name="Child")
        self.assertEqual(child.min_birthdate, date(2015, 4, 4))
        self.assertEqual(child.max_birthdate, date(2022, 4, 3))
        until = timezone.localtime(child.available_until, self.tz)
        # 2027-03-10 12:00 CET -> 2027-03-24 12:00 CET (before the DST change).
        self.assertEqual((until.date(), until.hour), (date(2027, 3, 24), 12))
        self.assertIsNone(new.ticket_types.get(name="Family").available_from)
        self.assertIsNone(new.ticket_types.get(name="Family").min_birthdate)

    def test_registration_close_crossing_dst_keeps_local_time(self):
        new = self._copy()

        # 23:59 CET is 22:59 UTC; 23:59 CEST is 21:59 UTC.
        self.assertEqual(self.source.registration_closes_at.astimezone(UTC).hour, 22)
        self.assertEqual(new.registration_closes_at.astimezone(UTC).hour, 21)

    def test_age_bounds_stay_on_the_anniversary_across_a_leap_day(self):
        # Delta is 364 days; a plain shift would give 2020-06-10.
        source = Event.objects.create(
            name="June", start_date=date(2026, 6, 12), end_date=date(2026, 6, 12)
        )
        TicketType.objects.create(
            event=source,
            name="Kids",
            price=0,
            max_birthdate=date(2019, 6, 12),
            min_birthdate=date(2013, 6, 13),
        )
        from events.services import copy_event

        new = copy_event(source, name="June 27", start_date=date(2027, 6, 11))

        kids = new.ticket_types.get()
        self.assertEqual(kids.max_birthdate, date(2020, 6, 11))
        self.assertEqual(kids.min_birthdate, date(2014, 6, 12))

    def test_age_bound_off_the_anniversary_is_refused_with_its_path(self):
        # The old copier shifted such a bound and produced a row that failed
        # clean(); apply's validation now refuses it.
        from events.event_spec import SpecError
        from events.services import copy_event

        TicketType.objects.create(
            event=self.source, name="Odd", price=0, max_birthdate=date(2020, 1, 1)
        )
        with self.assertRaises(SpecError) as ctx:
            copy_event(self.source, name="X", start_date=date(2027, 4, 3))
        self.assertIn(
            "max_birthdate",
            {e["path"].rsplit(".", 1)[-1] for e in ctx.exception.errors},
        )
        self.assertFalse(Event.objects.filter(name="X").exists())

    def test_negative_price_is_refused_and_nothing_is_created(self):
        from events.event_spec import SpecError
        from events.services import copy_event

        TicketType.objects.filter(pk=self.family_type.pk).update(price=-5)
        with self.assertRaises(SpecError) as ctx:
            copy_event(self.source, name="X", start_date=date(2027, 4, 3))
        self.assertTrue(any("price" in e["path"] for e in ctx.exception.errors))
        self.assertFalse(Event.objects.filter(name="X").exists())

    def test_open_or_past_window_is_dropped(self):
        # Source window 2027-03-01..15; shifting back puts it in the past.
        past = self._copy(start=date(2020, 3, 20))
        self.assertIsNone(past.registration_opens_at)
        self.assertIsNone(past.registration_closes_at)

        # A shifted window that is open right now is dropped too.
        now = timezone.now()
        Event.objects.filter(pk=self.source.pk).update(
            registration_opens_at=now - timezone.timedelta(days=1),
            registration_closes_at=now + timezone.timedelta(days=30),
        )
        self.source.refresh_from_db()
        from events.services import copy_event

        live = copy_event(self.source, name="Live", start_date=self.source.start_date)
        self.assertIsNone(live.registration_opens_at)
        self.assertIsNone(live.registration_closes_at)
        self.assertEqual(live.sessions.count(), 2)

    def test_future_window_is_kept(self):
        new = self._copy()
        self.assertIsNotNone(new.registration_opens_at)
        self.assertIsNotNone(new.registration_closes_at)

    def test_autumn_dst_change_keeps_wall_clock(self):
        # 09:00 CEST (+02:00) moved past 2027-10-31 must be 09:00 CET (+01:00),
        # not the 08:00 a fixed-offset shift would give.
        from datetime import timedelta

        from events.services import copy_event

        source = Event.objects.create(
            name="Autumn", start_date=date(2027, 9, 18), end_date=date(2027, 9, 18)
        )
        Session.objects.create(
            event=source,
            name="Morning",
            start_time=self._stockholm(2027, 9, 18, 9, 0),
            end_time=self._stockholm(2027, 9, 18, 11, 0),
        )
        new = copy_event(source, name="Autumn 2", start_date=date(2027, 11, 6))

        start = timezone.localtime(new.sessions.get().start_time, self.tz)
        self.assertEqual((start.date(), start.hour), (date(2027, 11, 6), 9))
        self.assertEqual(start.utcoffset(), timedelta(hours=1))

    def test_tied_choice_ordering_still_copies(self):
        ExtraChoice.objects.filter(extra=self.dinner).update(
            label="Same", price_delta=0
        )
        ExtraChoice.objects.filter(extra=self.dinner).update(sort_order=0)

        new = self._copy()

        self.assertEqual(new.extras.get(name="Dinner").choice_rows.count(), 2)

    def test_clones_are_recorded_for_event_and_extras(self):
        new = self._copy()

        self.assertEqual(new.cloned_from, self.source)
        self.assertEqual(new.extras.get(name="Dinner").cloned_from, self.dinner)
        self.assertEqual(new.extras.get(name="T-shirt").cloned_from, self.shirt)

    def test_leap_day_start_uses_nearest_leap_year(self):
        from events.services import copy_event

        source = Event.objects.create(
            name="Leap", start_date=date(2028, 2, 29), end_date=date(2028, 2, 29)
        )
        TicketType.objects.create(
            event=source, name="K", price=0, max_birthdate=date(2016, 2, 29)
        )
        new = copy_event(source, name="Leap 2", start_date=date(2029, 2, 28))
        self.assertEqual(new.ticket_types.get().max_birthdate, date(2017, 2, 28))

    def test_every_copied_row_passes_full_clean(self):
        new = self._copy()

        new.full_clean()
        for obj in [
            *new.sessions.all(),
            *new.ticket_types.all(),
            *new.extras.all(),
            *new.promo_codes.all(),
        ]:
            obj.full_clean()

    def test_cross_event_reference_is_refused_before_anything_is_created(self):
        from events.services import copy_event

        other = Event.objects.create(
            name="Other", start_date=date(2027, 1, 1), end_date=date(2027, 1, 1)
        )
        foreign = TicketType.objects.create(event=other, name="Foreign", price=1)
        self.promo.applies_to_ticket_types.add(foreign)

        with self.assertRaisesMessage(SpecError, "Foreign"):
            copy_event(self.source, name="Nope", start_date=date(2027, 5, 1))
        self.assertFalse(Event.objects.filter(name="Nope").exists())

    def test_cross_event_session_in_bundle_is_refused(self):
        from events.services import copy_event

        other = Event.objects.create(
            name="Other", start_date=date(2027, 1, 1), end_date=date(2027, 1, 1)
        )
        foreign = Session.objects.create(
            event=other,
            name="Elsewhere",
            start_time=timezone.now(),
            end_time=timezone.now(),
        )
        self.day_type.sessions.add(foreign)

        with self.assertRaisesMessage(SpecError, "Elsewhere"):
            copy_event(self.source, name="Nope", start_date=date(2027, 5, 1))

    def test_extras_copied_with_choices_and_session_remap(self):
        new = self._copy()

        extras = {e.name: e for e in new.extras.all()}
        self.assertEqual(set(extras), {"Dinner", "T-shirt"})
        dinner = extras["Dinner"]
        self.assertEqual(dinner.session, new.sessions.get(name="Saturday"))
        self.assertEqual(dinner.cloned_from, self.dinner)
        self.assertEqual(dinner.price, 60)
        self.assertEqual(
            set(dinner.choice_rows.values_list("label", "price_delta", "is_active")),
            {("Veg", 0, True), ("Meat", 10, False)},
        )
        self.assertIsNone(extras["T-shirt"].session)
        self.assertFalse(extras["T-shirt"].is_active)

    def test_promo_codes_copied_remapped_and_counter_reset(self):
        new = self._copy()

        promo = new.promo_codes.get()
        self.assertNotEqual(promo.pk, self.promo.pk)
        self.assertEqual(promo.code, "EARLY")
        self.assertEqual(promo.discount_type, "percent")
        self.assertEqual(promo.discount_value, 10)
        self.assertEqual(promo.max_uses, 5)
        self.assertEqual(promo.uses_count, 0)
        self.assertFalse(promo.is_active)
        self.assertEqual(
            set(promo.applies_to_ticket_types.all()),
            {new.ticket_types.get(name="Family")},
        )
        self.assertEqual(
            set(promo.unlocks_ticket_types.all()),
            {new.ticket_types.get(name="Child")},
        )
        self.assertEqual(
            timezone.localtime(promo.valid_until, self.tz).date(), date(2027, 3, 24)
        )

    def test_nothing_in_the_copy_points_at_source_rows(self):
        new = self._copy()

        new_session_ids = set(new.sessions.values_list("pk", flat=True))
        new_type_ids = set(new.ticket_types.values_list("pk", flat=True))
        for t in new.ticket_types.all():
            self.assertTrue({s.pk for s in t.sessions.all()} <= new_session_ids)
            if t.requires_ticket_type_id:
                self.assertIn(t.requires_ticket_type_id, new_type_ids)
        for e in new.extras.all():
            if e.session_id:
                self.assertIn(e.session_id, new_session_ids)
        for p in new.promo_codes.all():
            self.assertTrue(
                {t.pk for t in p.applies_to_ticket_types.all()} <= new_type_ids
            )
            self.assertTrue(
                {t.pk for t in p.unlocks_ticket_types.all()} <= new_type_ids
            )

    def test_registrations_and_tickets_not_copied(self):
        from registrations.models import Registration

        family = Family.objects.create()
        child = Child.objects.create(
            family=family,
            first_name="A",
            last_name="B",
            birthdate=date(2018, 1, 1),
        )
        Registration.objects.create(
            event=self.source,
            family=family,
            contact_email="a@example.com",
            verification_token_hash="x" * 64,
        )
        EventTicket.objects.create(
            attendee=child, event=self.source, ticket_type=self.child_type
        )
        SessionTicket.objects.create(attendee=child, session=self.sat)

        new = self._copy()

        self.assertFalse(new.registrations.exists())
        self.assertFalse(EventTicket.objects.filter(event=new).exists())
        self.assertFalse(SessionTicket.objects.filter(session__event=new).exists())

    def test_source_unchanged(self):
        before = {
            "event": Event.objects.filter(pk=self.source.pk).values().get(),
            "sessions": list(self.source.sessions.order_by("pk").values()),
            "types": list(self.source.ticket_types.order_by("pk").values()),
            "extras": list(self.source.extras.order_by("pk").values()),
            "promos": list(self.source.promo_codes.order_by("pk").values()),
        }

        self._copy()

        self.assertEqual(
            before,
            {
                "event": Event.objects.filter(pk=self.source.pk).values().get(),
                "sessions": list(self.source.sessions.order_by("pk").values()),
                "types": list(self.source.ticket_types.order_by("pk").values()),
                "extras": list(self.source.extras.order_by("pk").values()),
                "promos": list(self.source.promo_codes.order_by("pk").values()),
            },
        )
        self.assertEqual(
            self.promo.__class__.objects.get(pk=self.promo.pk).uses_count, 3
        )
        self.assertEqual(self.source.sessions.count(), 2)

    def test_failure_rolls_everything_back(self):
        from events.services import copy_event

        from events.event_spec import _apply

        real_save = _apply._save

        def fail_on_promo(obj, model, *args, **kwargs):
            if model is PromoCode:
                raise RuntimeError
            return real_save(obj, model, *args, **kwargs)

        with patch("events.event_spec._apply._save", side_effect=fail_on_promo):
            with self.assertRaises(RuntimeError):
                copy_event(self.source, name="Doomed", start_date=date(2027, 5, 1))

        self.assertFalse(Event.objects.filter(name="Doomed").exists())
        self.assertEqual(Session.objects.count(), 2)

    def test_source_deletion_keeps_copy(self):
        new = self._copy()
        TicketType.objects.filter(event=self.source).update(requires_ticket_type=None)
        self.source.delete()
        new.refresh_from_db()
        self.assertIsNone(new.cloned_from)


class CopyEventAdminActionTest(NonManifestStaticfilesTestCase, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = AdminUser.objects.create_superuser("copyadmin", "pw12345")
        cls.a = Event.objects.create(
            name="Alpha", start_date=date(2027, 6, 1), end_date=date(2027, 6, 3)
        )
        cls.b = Event.objects.create(
            name="Beta", start_date=date(2027, 7, 1), end_date=date(2027, 7, 3)
        )
        Session.objects.create(
            event=cls.a,
            name="Opening",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=1),
        )

    def setUp(self):
        # The source window (March 2027) must stay in the future of the test clock.
        patcher = patch(
            "django.utils.timezone.now",
            return_value=datetime(2026, 11, 19, 12, 0, tzinfo=UTC),
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client.force_login(self.user)
        self.url = reverse("admin:events_event_changelist")

    def _post(self, ids, follow=False, **extra):
        data = {
            "action": "copy_event_action",
            "_selected_action": [str(i) for i in ids],
            **extra,
        }
        return self.client.post(self.url, data, follow=follow)

    def test_first_step_shows_form(self):
        response = self._post([self.a.pk])
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="start_date"')
        self.assertEqual(Event.objects.count(), 2)

    def test_apply_copies_and_redirects_to_new_event(self):
        response = self._post(
            [self.a.pk], apply="yes", name="Alpha 2028", start_date="2028-06-01"
        )

        new = Event.objects.get(name="Alpha 2028")
        self.assertRedirects(
            response, reverse("admin:events_event_change", args=[new.pk])
        )
        self.assertEqual(new.cloned_from, self.a)
        self.assertEqual(new.end_date, date(2028, 6, 3))
        self.assertEqual(new.sessions.count(), 1)

    def test_more_than_one_selected_is_an_error(self):
        response = self._post([self.a.pk, self.b.pk], follow=True)
        self.assertContains(response, "Select exactly one event to copy.")
        self.assertEqual(Event.objects.count(), 2)

    def test_invalid_date_rerenders_form(self):
        response = self._post([self.a.pk], apply="yes", name="X", start_date="nope")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Event.objects.count(), 2)

    def test_copied_from_is_read_only_on_change_page(self):
        new = Event.objects.create(
            name="Gamma",
            start_date=date(2027, 8, 1),
            end_date=date(2027, 8, 1),
            cloned_from=self.a,
        )
        response = self.client.get(reverse("admin:events_event_change", args=[new.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("cloned_from", response.context["adminform"].form.fields)
        self.assertContains(response, "Alpha")

    def test_cross_event_reference_shows_error_not_500(self):
        other = Event.objects.create(
            name="Other", start_date=date(2027, 1, 1), end_date=date(2027, 1, 1)
        )
        foreign = TicketType.objects.create(event=other, name="Foreign", price=1)
        promo = PromoCode.objects.create(event=self.a, code="X")
        promo.applies_to_ticket_types.add(foreign)

        response = self._post(
            [self.a.pk],
            apply="yes",
            name="Alpha 2",
            start_date="2028-06-01",
            follow=True,
        )
        self.assertContains(response, "Foreign")
        self.assertFalse(Event.objects.filter(name="Alpha 2").exists())

    def test_refused_spec_shows_error_with_paths_not_500(self):
        TicketType.objects.create(event=self.a, name="Bad", price=-1)

        response = self._post(
            [self.a.pk],
            apply="yes",
            name="Alpha 3",
            start_date="2028-06-01",
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Could not copy")
        self.assertContains(response, "ticket_types[0].price")
        self.assertFalse(Event.objects.filter(name="Alpha 3").exists())

    def test_spec_warnings_from_a_copy_are_shown(self):
        # An event with no registration window gets the "self-serve is off" warning.
        response = self._post(
            [self.a.pk],
            apply="yes",
            name="Alpha 5",
            start_date="2028-06-01",
            follow=True,
        )
        messages_ = list(response.context["messages"])
        self.assertTrue(any(m.level_tag == "warning" for m in messages_))

    def test_dropped_registration_window_is_reported(self):
        now = timezone.now()
        Event.objects.filter(pk=self.a.pk).update(
            registration_opens_at=now - timezone.timedelta(days=1),
            registration_closes_at=now + timezone.timedelta(days=30),
        )

        response = self._post(
            [self.a.pk],
            apply="yes",
            name="Alpha 4",
            start_date="2027-06-01",
            follow=True,
        )
        new = Event.objects.get(name="Alpha 4")
        self.assertIsNone(new.registration_opens_at)
        self.assertContains(response, "registration")
        self.assertContains(response, "Alpha 4")

    def test_user_with_only_add_event_is_refused(self):
        from django.contrib.auth.models import Permission

        staff = AdminUser.objects.create_user("limited", password="pw12345")
        staff.is_staff = True
        staff.save()
        staff.user_permissions.set(
            Permission.objects.filter(
                codename__in=["add_event", "change_event", "view_event"]
            )
        )
        self.client.force_login(staff)

        self._post([self.a.pk], apply="yes", name="Sneaky", start_date="2028-06-01")

        self.assertFalse(Event.objects.filter(name="Sneaky").exists())
