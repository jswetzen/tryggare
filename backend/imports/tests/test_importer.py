"""
Unit tests for imports/importer.py — requires database access.
"""

from datetime import date

from django.test import TestCase

from events.models import Event, EventTicket, Session, SessionTicket
from families.models import Child, Family, Parent
from imports.importer import run_import
from imports.models import EventImportConfig, ImportRun
from accounts.models import AdminUser


def make_user(username="testimporter"):
    user, _ = AdminUser.objects.get_or_create(
        username=username,
        defaults={"name": "Test Importer", "is_staff": True},
    )
    user.set_password("testpass")
    user.save()
    return user


def make_event(name="Test Conference 2026"):
    return Event.objects.create(
        name=name,
        start_date=date(2026, 6, 25),
        end_date=date(2026, 6, 28),
    )


def make_config(event, field_mappings=None):
    return EventImportConfig.objects.create(
        event=event,
        field_mappings=field_mappings or {},
    )


MINIMAL_JSON = {
    "contact1": {
        "Booking ID": "99001",
        "Contact First Name": "Anna",
        "Contact Last Name": "Svensson",
        "Contact Email": "anna@test.se",
        "Cell/Mobile": "0700000001",
        "Extra vårdnadshavare kontaktinformation First Name": "Lars",
        "Extra vårdnadshavare kontaktinformation Last Name": "Svensson",
        "Extra vårdnadshavare kontaktinformation Email": "lars@test.se",
        "Extra vårdnadshavare kontaktinformation Phone": "0700000002",
        "SK26 Barnkonferens First Name": "Maja",
        "SK26 Barnkonferens Last Name": "Svensson",
        "ETicket SK26 Barnkonferens": "TICKETABC",
        "SK26 Barnkonferens Ålder": "15/03/2018",
    }
}

MULTI_CHILD_JSON = {
    "contact2": {
        "Booking ID": "99002",
        "Contact First Name": "Erik",
        "Contact Last Name": "Nilsson",
        "Contact Email": "erik@test.se",
        "Cell/Mobile": "0700000003",
        "Extra vårdnadshavare kontaktinformation First Name": "",
        "Extra vårdnadshavare kontaktinformation Last Name": "",
        "Extra vårdnadshavare kontaktinformation Email": "",
        "Extra vårdnadshavare kontaktinformation Phone": "",
        "Dagsbiljett barn First Name": ["Kalle", "Pelle"],
        "Dagsbiljett barn Last Name": ["Nilsson", "Nilsson"],
        "ETicket Dagsbiljett barn": "SHAREDTICKET",
        "Dagsbiljett barn Ålder": "10/05/2015|22/08/2017",
    }
}


class FreshImportTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.event = make_event()
        self.config = make_config(
            self.event,
            field_mappings={"SK26 Barnkonferens": "full_event"},
        )

    def test_creates_family(self):
        run_import(MINIMAL_JSON, self.config, self.user)
        assert Family.objects.filter(external_booking_id="99001").exists()

    def test_creates_parents(self):
        run_import(MINIMAL_JSON, self.config, self.user)
        family = Family.objects.get(external_booking_id="99001")
        # Primary contact + extra guardian
        assert Parent.objects.filter(family=family).count() == 2

    def test_creates_child(self):
        run_import(MINIMAL_JSON, self.config, self.user)
        family = Family.objects.get(external_booking_id="99001")
        assert Child.objects.filter(family=family, first_name="Maja").exists()

    def test_creates_event_ticket(self):
        run_import(MINIMAL_JSON, self.config, self.user)
        child = Child.objects.get(first_name="Maja", last_name="Svensson")
        ticket = EventTicket.objects.filter(child=child, event=self.event).first()
        assert ticket is not None
        assert ticket.external_ticket_code == "TICKETABC"

    def test_run_status_completed(self):
        run = run_import(MINIMAL_JSON, self.config, self.user)
        assert run.status == ImportRun.STATUS_COMPLETED

    def test_summary_counts(self):
        run = run_import(MINIMAL_JSON, self.config, self.user)
        assert run.summary["families_created"] == 1
        assert run.summary["children_created"] == 1
        assert run.summary["tickets_created"] == 1


class IdempotentImportTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.event = make_event()
        self.config = make_config(
            self.event,
            field_mappings={"SK26 Barnkonferens": "full_event"},
        )

    def test_reimport_no_duplicates(self):
        run_import(MINIMAL_JSON, self.config, self.user)
        run_import(MINIMAL_JSON, self.config, self.user)

        assert Family.objects.filter(external_booking_id="99001").count() == 1
        assert Child.objects.filter(first_name="Maja", last_name="Svensson").count() == 1
        assert EventTicket.objects.filter(event=self.event).count() == 1

    def test_reimport_skips_existing(self):
        run_import(MINIMAL_JSON, self.config, self.user)
        run2 = run_import(MINIMAL_JSON, self.config, self.user)

        assert run2.summary["families_skipped"] == 1
        assert run2.summary["children_skipped"] == 1
        assert run2.summary["families_created"] == 0
        assert run2.summary["children_created"] == 0


class MultiChildImportTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.event = make_event()
        self.config = make_config(
            self.event,
            field_mappings={"Dagsbiljett barn": "full_event"},
        )

    def test_creates_multiple_children(self):
        run_import(MULTI_CHILD_JSON, self.config, self.user)
        family = Family.objects.get(external_booking_id="99002")
        children = list(Child.objects.filter(family=family).order_by("first_name"))
        assert len(children) == 2
        names = {c.first_name for c in children}
        assert names == {"Kalle", "Pelle"}

    def test_shared_ticket_code(self):
        run_import(MULTI_CHILD_JSON, self.config, self.user)
        tickets = EventTicket.objects.filter(event=self.event)
        assert tickets.count() == 2
        for ticket in tickets:
            assert ticket.external_ticket_code == "SHAREDTICKET"

    def test_no_extra_guardian_when_empty(self):
        run_import(MULTI_CHILD_JSON, self.config, self.user)
        family = Family.objects.get(external_booking_id="99002")
        # Only primary contact, no extra guardian
        assert Parent.objects.filter(family=family).count() == 1


class SessionTicketImportTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.event = make_event()
        from django.utils import timezone
        self.session = Session.objects.create(
            name="Thursday Session",
            event=self.event,
            start_time=timezone.now(),
            end_time=timezone.now(),
        )
        self.config = make_config(
            self.event,
            field_mappings={"SK26 Barnkonferens": str(self.session.id)},
        )

    def test_creates_session_ticket(self):
        run_import(MINIMAL_JSON, self.config, self.user)
        child = Child.objects.get(first_name="Maja")
        ticket = SessionTicket.objects.filter(child=child, session=self.session).first()
        assert ticket is not None
        assert ticket.external_ticket_code == "TICKETABC"

    def test_no_event_ticket_created(self):
        run_import(MINIMAL_JSON, self.config, self.user)
        child = Child.objects.get(first_name="Maja")
        assert not EventTicket.objects.filter(child=child, event=self.event).exists()


class MissingBirthdateTest(TestCase):
    """Children with no parseable birthdate are imported without a ticket."""

    def setUp(self):
        self.user = make_user()
        self.event = make_event()
        self.config = make_config(
            self.event,
            field_mappings={"SK26 Barnkonferens": "full_event"},
        )

    def _run(self, alder_val):
        data = {
            "contact1": {
                "Booking ID": "99010",
                "Contact First Name": "Test",
                "Contact Last Name": "Parent",
                "Contact Email": "test@example.com",
                "Cell/Mobile": "0700000010",
                "Extra vårdnadshavare kontaktinformation First Name": "",
                "Extra vårdnadshavare kontaktinformation Last Name": "",
                "Extra vårdnadshavare kontaktinformation Email": "",
                "Extra vårdnadshavare kontaktinformation Phone": "",
                "SK26 Barnkonferens First Name": "NoDate",
                "SK26 Barnkonferens Last Name": "Child",
                "SK26 Barnkonferens Ålder": alder_val,
            }
        }
        return run_import(data, self.config, self.user)

    def test_child_created_when_birthdate_missing(self):
        run = self._run("")
        assert Child.objects.filter(first_name="NoDate").exists()

    def test_no_ticket_when_birthdate_missing(self):
        self._run("")
        child = Child.objects.get(first_name="NoDate")
        assert not EventTicket.objects.filter(child=child).exists()

    def test_birthdate_is_null(self):
        self._run("")
        child = Child.objects.get(first_name="NoDate")
        assert child.birthdate is None

    def test_warning_logged_for_missing_birthdate(self):
        run = self._run("")
        assert any("without birthdate" in w for w in run.summary["warnings"])

    def test_child_created_count(self):
        run = self._run("")
        assert run.summary["children_created"] == 1
        assert run.summary["tickets_created"] == 0

    def test_reimport_does_not_duplicate_no_birthdate_child(self):
        self._run("")
        self._run("")
        assert Child.objects.filter(first_name="NoDate").count() == 1


class NoChildrenFamilySkipTest(TestCase):
    """Bookings that produce zero children (all prefixes ignored) are skipped."""

    def setUp(self):
        self.user = make_user()
        self.event = make_event()
        # Config maps the only child prefix to "ignore" — no children will parse
        self.config = make_config(
            self.event,
            field_mappings={"SK26 Barnkonferens": "ignore"},
        )

    def test_family_not_created_when_no_children(self):
        run_import(MINIMAL_JSON, self.config, self.user)
        assert not Family.objects.filter(external_booking_id="99001").exists()

    def test_warning_logged_for_no_children(self):
        run = run_import(MINIMAL_JSON, self.config, self.user)
        assert any("skipped" in w and "no children" in w.lower() for w in run.summary["warnings"])

    def test_families_created_count_is_zero(self):
        run = run_import(MINIMAL_JSON, self.config, self.user)
        assert run.summary["families_created"] == 0


class ErrorHandlingTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.event = make_event()
        self.config = make_config(
            self.event,
            field_mappings={"SK26 Barnkonferens": "full_event"},
        )

    def test_skips_non_dict_entries(self):
        data = {
            "meta": "not a booking",
            "contact1": {
                "Booking ID": "99001",
                "Contact First Name": "Anna",
                "Contact Last Name": "Svensson",
                "Contact Email": "anna@test.se",
                "Cell/Mobile": "070000001",
                "Extra vårdnadshavare kontaktinformation First Name": "",
                "Extra vårdnadshavare kontaktinformation Last Name": "",
                "Extra vårdnadshavare kontaktinformation Email": "",
                "Extra vårdnadshavare kontaktinformation Phone": "",
                "SK26 Barnkonferens First Name": "Maja",
                "SK26 Barnkonferens Last Name": "Svensson",
                "ETicket SK26 Barnkonferens": "ABC123",
                "SK26 Barnkonferens Ålder": "15/03/2018",
            },
        }
        run = run_import(data, self.config, self.user)
        assert run.status == ImportRun.STATUS_COMPLETED
        # Only 1 booking counted (the dict entry, not the string)
        assert run.summary["total_bookings"] == 1

    def test_missing_booking_id_logged_as_warning(self):
        data = {
            "contact1": {
                "Booking ID": "",
                "Contact First Name": "No",
                "Contact Last Name": "ID",
                "Contact Email": "",
                "Cell/Mobile": "",
            }
        }
        run = run_import(data, self.config, self.user)
        assert run.status == ImportRun.STATUS_COMPLETED
        assert len(run.summary["warnings"]) > 0
