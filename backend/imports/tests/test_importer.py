"""
Unit tests for imports/importer.py — requires database access.
"""

from datetime import date

from django.test import TestCase

from events.models import Event, EventTicket, Session, SessionTicket
from families.models import Child, Family, Parent
from imports.importer import run_import
from imports.models import FestivalProImportSource, ImportRun, ImportSource
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


def make_source(event, field_mappings=None):
    source = ImportSource.objects.create(
        name="Test Source",
        provider_type=ImportSource.PROVIDER_FESTIVALPRO,
        event=event,
    )
    FestivalProImportSource.objects.create(
        source=source,
        login_url="https://example.com/login",
        export_url="https://example.com/export",
        export_body="",
        field_mappings=field_mappings or {},
    )
    return source


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
        self.source = make_source(
            self.event,
            field_mappings={"SK26 Barnkonferens": "full_event"},
        )

    def test_creates_family(self):
        run_import(
            MINIMAL_JSON,
            self.source,
            self.source.festivalpro_config.field_mappings,
            self.user,
        )
        assert Family.objects.filter(external_booking_id="99001").exists()

    def test_creates_parents(self):
        run_import(
            MINIMAL_JSON,
            self.source,
            self.source.festivalpro_config.field_mappings,
            self.user,
        )
        family = Family.objects.get(external_booking_id="99001")
        # Primary contact + extra guardian
        assert Parent.objects.filter(family=family).count() == 2

    def test_creates_child(self):
        run_import(
            MINIMAL_JSON,
            self.source,
            self.source.festivalpro_config.field_mappings,
            self.user,
        )
        family = Family.objects.get(external_booking_id="99001")
        assert Child.objects.filter(family=family, first_name="Maja").exists()

    def test_creates_event_ticket(self):
        run_import(
            MINIMAL_JSON,
            self.source,
            self.source.festivalpro_config.field_mappings,
            self.user,
        )
        child = Child.objects.get(first_name="Maja", last_name="Svensson")
        ticket = EventTicket.objects.filter(child=child, event=self.event).first()
        assert ticket is not None
        assert ticket.external_ticket_code == "TICKETABC"

    def test_run_status_completed(self):
        run = run_import(
            MINIMAL_JSON,
            self.source,
            self.source.festivalpro_config.field_mappings,
            self.user,
        )
        assert run.status == ImportRun.STATUS_COMPLETED

    def test_summary_counts(self):
        run = run_import(
            MINIMAL_JSON,
            self.source,
            self.source.festivalpro_config.field_mappings,
            self.user,
        )
        assert run.summary["families_created"] == 1
        assert run.summary["children_created"] == 1
        assert run.summary["tickets_created"] == 1


class IdempotentImportTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.event = make_event()
        self.source = make_source(
            self.event,
            field_mappings={"SK26 Barnkonferens": "full_event"},
        )

    def test_reimport_no_duplicates(self):
        fm = self.source.festivalpro_config.field_mappings
        run_import(MINIMAL_JSON, self.source, fm, self.user)
        run_import(MINIMAL_JSON, self.source, fm, self.user)

        assert Family.objects.filter(external_booking_id="99001").count() == 1
        assert (
            Child.objects.filter(first_name="Maja", last_name="Svensson").count() == 1
        )
        assert EventTicket.objects.filter(event=self.event).count() == 1

    def test_reimport_skips_existing(self):
        fm = self.source.festivalpro_config.field_mappings
        run_import(MINIMAL_JSON, self.source, fm, self.user)
        run2 = run_import(MINIMAL_JSON, self.source, fm, self.user)

        assert run2.summary["families_skipped"] == 1
        assert run2.summary["children_skipped"] == 1
        assert run2.summary["families_created"] == 0
        assert run2.summary["children_created"] == 0


class MultiChildImportTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.event = make_event()
        self.source = make_source(
            self.event,
            field_mappings={"Dagsbiljett barn": "full_event"},
        )

    def test_creates_multiple_children(self):
        fm = self.source.festivalpro_config.field_mappings
        run_import(MULTI_CHILD_JSON, self.source, fm, self.user)
        family = Family.objects.get(external_booking_id="99002")
        children = list(Child.objects.filter(family=family).order_by("first_name"))
        assert len(children) == 2
        names = {c.first_name for c in children}
        assert names == {"Kalle", "Pelle"}

    def test_shared_ticket_code(self):
        fm = self.source.festivalpro_config.field_mappings
        run_import(MULTI_CHILD_JSON, self.source, fm, self.user)
        tickets = EventTicket.objects.filter(event=self.event)
        assert tickets.count() == 2
        for ticket in tickets:
            assert ticket.external_ticket_code == "SHAREDTICKET"

    def test_no_extra_guardian_when_empty(self):
        fm = self.source.festivalpro_config.field_mappings
        run_import(MULTI_CHILD_JSON, self.source, fm, self.user)
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
        self.source = make_source(
            self.event,
            field_mappings={"SK26 Barnkonferens": str(self.session.id)},
        )

    def test_creates_session_ticket(self):
        fm = self.source.festivalpro_config.field_mappings
        run_import(MINIMAL_JSON, self.source, fm, self.user)
        child = Child.objects.get(first_name="Maja")
        ticket = SessionTicket.objects.filter(child=child, session=self.session).first()
        assert ticket is not None
        assert ticket.external_ticket_code == "TICKETABC"

    def test_no_event_ticket_created(self):
        fm = self.source.festivalpro_config.field_mappings
        run_import(MINIMAL_JSON, self.source, fm, self.user)
        child = Child.objects.get(first_name="Maja")
        assert not EventTicket.objects.filter(child=child, event=self.event).exists()


class MissingBirthdateTest(TestCase):
    """Children with no parseable birthdate are imported with a ticket but no birthdate."""

    def setUp(self):
        self.user = make_user()
        self.event = make_event()
        self.source = make_source(
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
        fm = self.source.festivalpro_config.field_mappings
        return run_import(data, self.source, fm, self.user)

    def test_child_created_when_birthdate_missing(self):
        run = self._run("")
        assert Child.objects.filter(first_name="NoDate").exists()

    def test_ticket_created_when_birthdate_missing(self):
        self._run("")
        child = Child.objects.get(first_name="NoDate")
        assert EventTicket.objects.filter(child=child).exists()

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
        assert run.summary["tickets_created"] == 1

    def test_reimport_does_not_duplicate_no_birthdate_child(self):
        self._run("")
        self._run("")
        assert Child.objects.filter(first_name="NoDate").count() == 1


class NoChildrenFamilySkipTest(TestCase):
    """Bookings that produce zero children (all prefixes ignored) are skipped."""

    def setUp(self):
        self.user = make_user()
        self.event = make_event()
        # Source maps the only child prefix to "ignore" — no children will parse
        self.source = make_source(
            self.event,
            field_mappings={"SK26 Barnkonferens": "ignore"},
        )

    def test_family_not_created_when_no_children(self):
        fm = self.source.festivalpro_config.field_mappings
        run_import(MINIMAL_JSON, self.source, fm, self.user)
        assert not Family.objects.filter(external_booking_id="99001").exists()

    def test_warning_logged_for_no_children(self):
        fm = self.source.festivalpro_config.field_mappings
        run = run_import(MINIMAL_JSON, self.source, fm, self.user)
        assert any(
            "skipped" in w and "no children" in w.lower()
            for w in run.summary["warnings"]
        )

    def test_families_created_count_is_zero(self):
        fm = self.source.festivalpro_config.field_mappings
        run = run_import(MINIMAL_JSON, self.source, fm, self.user)
        assert run.summary["families_created"] == 0


class ContactUpdateOnReimportTest(TestCase):
    """
    Re-importing an existing family updates parent phone/email unless locked.
    Parent is matched by name (set at creation time).
    """

    def setUp(self):
        self.user = make_user()
        self.event = make_event()
        self.source = make_source(
            self.event,
            field_mappings={"SK26 Barnkonferens": "full_event"},
        )
        self.fm = self.source.festivalpro_config.field_mappings

    def _updated_json(self, phone="0709999999", email="new@example.se"):
        return {
            "contact1": {
                **MINIMAL_JSON["contact1"],
                "Cell/Mobile": phone,
                "Contact Email": email,
            }
        }

    def test_phone_updated_on_reimport(self):
        run_import(MINIMAL_JSON, self.source, self.fm, self.user)
        run_import(self._updated_json(phone="0709999999"), self.source, self.fm, self.user)
        parent = Parent.objects.get(family__external_booking_id="99001", name="Anna Svensson")
        assert parent.phone == "0709999999"

    def test_email_updated_on_reimport(self):
        run_import(MINIMAL_JSON, self.source, self.fm, self.user)
        run_import(self._updated_json(email="updated@example.se"), self.source, self.fm, self.user)
        parent = Parent.objects.get(family__external_booking_id="99001", name="Anna Svensson")
        assert parent.email == "updated@example.se"

    def test_phone_not_updated_when_locked(self):
        run_import(MINIMAL_JSON, self.source, self.fm, self.user)
        parent = Parent.objects.get(family__external_booking_id="99001", name="Anna Svensson")
        parent.phone_locked = True
        parent.save(update_fields=["phone_locked"])

        run_import(self._updated_json(phone="0709999999"), self.source, self.fm, self.user)
        parent.refresh_from_db()
        assert parent.phone == "0700000001"

    def test_email_not_updated_when_locked(self):
        run_import(MINIMAL_JSON, self.source, self.fm, self.user)
        parent = Parent.objects.get(family__external_booking_id="99001", name="Anna Svensson")
        parent.email_locked = True
        parent.save(update_fields=["email_locked"])

        run_import(self._updated_json(email="updated@example.se"), self.source, self.fm, self.user)
        parent.refresh_from_db()
        assert parent.email == "anna@test.se"

    def test_blank_import_value_does_not_clear_phone(self):
        run_import(MINIMAL_JSON, self.source, self.fm, self.user)
        run_import(self._updated_json(phone=""), self.source, self.fm, self.user)
        parent = Parent.objects.get(family__external_booking_id="99001", name="Anna Svensson")
        assert parent.phone == "0700000001"

    def test_blank_import_value_does_not_clear_email(self):
        run_import(MINIMAL_JSON, self.source, self.fm, self.user)
        run_import(self._updated_json(email=""), self.source, self.fm, self.user)
        parent = Parent.objects.get(family__external_booking_id="99001", name="Anna Svensson")
        assert parent.email == "anna@test.se"

    def test_parents_updated_in_summary(self):
        run_import(MINIMAL_JSON, self.source, self.fm, self.user)
        run2 = run_import(self._updated_json(), self.source, self.fm, self.user)
        assert run2.summary["parents_updated"] >= 1

    def test_no_update_when_value_unchanged(self):
        run_import(MINIMAL_JSON, self.source, self.fm, self.user)
        run2 = run_import(MINIMAL_JSON, self.source, self.fm, self.user)
        assert run2.summary["parents_updated"] == 0

    def test_extra_guardian_phone_updated_on_reimport(self):
        run_import(MINIMAL_JSON, self.source, self.fm, self.user)
        updated = {
            "contact1": {
                **MINIMAL_JSON["contact1"],
                "Extra vårdnadshavare kontaktinformation Phone": "0708888888",
            }
        }
        run_import(updated, self.source, self.fm, self.user)
        guardian = Parent.objects.get(family__external_booking_id="99001", name="Lars Svensson")
        assert guardian.phone == "0708888888"


class ErrorHandlingTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.event = make_event()
        self.source = make_source(
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
        fm = self.source.festivalpro_config.field_mappings
        run = run_import(data, self.source, fm, self.user)
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
        fm = self.source.festivalpro_config.field_mappings
        run = run_import(data, self.source, fm, self.user)
        assert run.status == ImportRun.STATUS_COMPLETED
        assert len(run.summary["warnings"]) > 0
