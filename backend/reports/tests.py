"""
Tests for report snapshot aggregation and the read-only reports API.

The fixture below is hand-computed so every aggregate has a known expected
value (see the per-assertion comments). ``check_in_time`` is ``auto_now_add``,
so timed records are created then back-dated via ``.update()`` (which bypasses
auto fields) to control peak-concurrent / average-stay calculations.
"""

from datetime import date, datetime

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import AdminUser
from checkins.models import CheckInRecord
from events.models import Event, EventTicket, Session, SessionTicket
from families.models import Child, Family
from reports.models import EventReport
from reports.services import build_event_report_data, generate_event_report
from accounts.roles import COORDINATOR, VOLUNTEER, grant


def _aware(y, mo, d, h, mi):
    return timezone.make_aware(datetime(y, mo, d, h, mi))


class ReportAggregationTest(TestCase):
    def setUp(self):
        self.alice = AdminUser.objects.create_user("alice", name="Alice")
        self.bob = AdminUser.objects.create_user("bob", name="Bob")

        # An earlier event so one family counts as "returning".
        self.past_event = Event.objects.create(
            name="Past Event",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 2),
        )
        self.past_session = Session.objects.create(
            event=self.past_event,
            name="Past Session",
            start_time=_aware(2025, 1, 1, 9, 0),
            end_time=_aware(2025, 1, 1, 12, 0),
        )

        self.event = Event.objects.create(
            name="Main Event",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 3),
        )
        self.session_a = Session.objects.create(
            event=self.event,
            name="Session A",
            start_time=_aware(2026, 6, 1, 9, 0),
            end_time=_aware(2026, 6, 1, 12, 0),
        )
        self.session_b = Session.objects.create(
            event=self.event,
            name="Session B",
            start_time=_aware(2026, 6, 2, 9, 0),
            end_time=_aware(2026, 6, 2, 12, 0),
        )

        # Families and children (ages computed at event.start_date 2026-06-01).
        self.f1 = Family.objects.create(last_name="Returning")
        self.c1 = Child.objects.create(
            family=self.f1,
            first_name="C1",
            last_name="Returning",
            birthdate=date(2020, 6, 1),  # age 6 -> "6-8"
            allergies="peanuts",
        )
        self.f2 = Family.objects.create(last_name="NewTwo")
        self.c2 = Child.objects.create(
            family=self.f2,
            first_name="C2",
            last_name="NewTwo",
            birthdate=date(2023, 6, 1),  # age 3 -> "3-5"
        )
        self.f3 = Family.objects.create(last_name="NewThree")
        self.c3 = Child.objects.create(
            family=self.f3,
            first_name="C3",
            last_name="NewThree",
            birthdate=None,  # -> "unknown"
        )
        self.c4 = Child.objects.create(
            family=self.f3,
            first_name="C4",
            last_name="NewThree",
            birthdate=date(2010, 6, 1),  # age 16 -> "13+"
        )
        self.f4 = Family.objects.create(last_name="NoShow")
        self.c5 = Child.objects.create(
            family=self.f4, first_name="C5", last_name="NoShow"
        )

        # Tickets.
        EventTicket.objects.create(attendee=self.c1, event=self.event)
        EventTicket.objects.create(attendee=self.c5, event=self.event)  # no-show
        SessionTicket.objects.create(attendee=self.c2, session=self.session_a)
        SessionTicket.objects.create(
            attendee=self.c3, session=self.session_a
        )  # no-show

        # Returning: C1 attended the past event.
        self._checkin(self.c1, self.past_session, self.alice, _aware(2025, 1, 1, 9, 0))

        # Session A check-ins.
        self._checkin(
            self.c1,
            self.session_a,
            self.alice,
            _aware(2026, 6, 1, 9, 0),
            cout=_aware(2026, 6, 1, 11, 0),
            checkout_staff=self.alice,
            label=True,
        )  # 120 min stay
        self._checkin(
            self.c2,
            self.session_a,
            self.alice,
            _aware(2026, 6, 1, 9, 30),
            cout=_aware(2026, 6, 1, 10, 30),
            checkout_staff=self.alice,
        )  # 60 min stay
        self._checkin(
            self.c4,
            self.session_a,
            self.bob,
            _aware(2026, 6, 1, 9, 15),
            supervised=True,
        )  # open, supervised

        # Session B check-ins.
        self._checkin(
            self.c1,
            self.session_b,
            self.bob,
            _aware(2026, 6, 2, 9, 0),
            cout=_aware(2026, 6, 2, 9, 30),
            checkout_staff=self.bob,
        )  # 30 min
        self._checkin(
            self.c3,
            self.session_b,
            self.alice,
            _aware(2026, 6, 2, 9, 10),
            cout=_aware(2026, 6, 2, 9, 40),
            checkout_staff=self.alice,
            label=True,
        )  # 30 min

        self.data = build_event_report_data(self.event)

    def _checkin(
        self,
        child,
        session,
        staff,
        cin,
        cout=None,
        supervised=False,
        label=False,
        checkout_staff=None,
    ):
        rec = CheckInRecord.objects.create(
            attendee=child,
            session=session,
            check_in_staff=staff,
            check_out_time=cout,
            check_out_staff=checkout_staff,
            supervised=supervised,
            label_printed=label,
        )
        CheckInRecord.objects.filter(id=rec.id).update(check_in_time=cin)
        return rec

    def test_event_totals(self):
        ev = self.data["event"]
        self.assertEqual(ev["session_count"], 2)
        self.assertEqual(ev["unique_children"], 4)  # C1, C2, C3, C4
        self.assertEqual(ev["total_checkins"], 5)  # 3 in A + 2 in B

    def test_ticketing(self):
        tickets = self.data["event"]["tickets"]
        self.assertEqual(tickets["event_passes_issued"], 2)  # C1, C5
        self.assertEqual(tickets["session_tickets_issued"], 2)  # C2, C3 in A
        self.assertEqual(tickets["event_pass_no_shows"], 1)  # C5 never checked in

    def test_demographics(self):
        demo = self.data["event"]["demographics"]
        self.assertEqual(
            demo["age_buckets"],
            {"0-2": 0, "3-5": 1, "6-8": 1, "9-12": 0, "13+": 1, "unknown": 1},
        )
        self.assertEqual(demo["with_allergies"], 1)  # C1
        self.assertEqual(demo["returning_families"], 1)  # F1 (past event)
        self.assertEqual(demo["new_families"], 2)  # F2, F3

    def test_operations(self):
        ops = self.data["event"]["operations"]
        self.assertEqual(ops["labels_printed"], 2)  # C1 in A, C3 in B
        self.assertEqual(
            ops["checkins_per_staff"],
            [{"staff": "Alice", "count": 3}, {"staff": "Bob", "count": 2}],
        )
        # Completed stays: 120, 60, 30, 30 -> avg 60.0 (C4 open, excluded).
        self.assertEqual(ops["avg_stay_minutes"], 60.0)

    def test_session_a(self):
        a = next(s for s in self.data["sessions"] if s["name"] == "Session A")
        self.assertEqual(a["unique_children"], 3)
        self.assertEqual(a["total_checkins"], 3)
        self.assertEqual(a["peak_concurrent"], 3)  # C1+C4+C2 overlap ~09:30
        self.assertEqual(a["supervised"], 1)  # C4
        self.assertEqual(a["staffed_checkouts"], 2)  # C1, C2
        self.assertEqual(a["session_tickets_issued"], 2)  # C2, C3
        self.assertEqual(a["session_ticket_no_shows"], 1)  # C3
        self.assertEqual(a["labels_printed"], 1)  # C1
        self.assertEqual(a["avg_stay_minutes"], 90.0)  # 120, 60

    def test_session_b(self):
        b = next(s for s in self.data["sessions"] if s["name"] == "Session B")
        self.assertEqual(b["unique_children"], 2)
        self.assertEqual(b["peak_concurrent"], 2)  # C1 and C3 overlap
        self.assertEqual(b["supervised"], 0)
        self.assertEqual(b["session_ticket_no_shows"], 0)
        self.assertEqual(b["avg_stay_minutes"], 30.0)

    def test_generate_persists_snapshot(self):
        report = generate_event_report(self.event, user=self.alice)
        self.assertEqual(report.unique_children, 4)
        self.assertEqual(report.total_checkins, 5)
        self.assertEqual(report.event_name, "Main Event")
        self.assertEqual(report.generated_by, self.alice)
        self.assertEqual(report.data["schema_version"], 1)

    def test_empty_event_avg_stay_is_none(self):
        empty = Event.objects.create(
            name="Empty", start_date=date(2026, 7, 1), end_date=date(2026, 7, 1)
        )
        data = build_event_report_data(empty)
        self.assertEqual(data["event"]["unique_children"], 0)
        self.assertIsNone(data["event"]["operations"]["avg_stay_minutes"])


class ReportApiTest(TestCase):
    def setUp(self):
        self.user = AdminUser.objects.create_user("staff", name="Staff")
        self.event = Event.objects.create(
            name="API Event", start_date=date(2026, 6, 1), end_date=date(2026, 6, 1)
        )
        self.report = generate_event_report(self.event, user=self.user)
        self.client = APIClient()

    def test_requires_authentication(self):
        resp = self.client.get("/api/event-reports/")
        self.assertEqual(resp.status_code, 403)

    def test_list_and_detail(self):
        grant(self.user, COORDINATOR)
        self.client.force_authenticate(self.user)
        resp = self.client.get("/api/event-reports/")
        self.assertEqual(resp.status_code, 200)
        results = resp.data["results"] if isinstance(resp.data, dict) else resp.data
        self.assertEqual(len(results), 1)
        # List view omits the heavy snapshot payload.
        self.assertNotIn("data", results[0])

        detail = self.client.get(f"/api/event-reports/{self.report.id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertIn("data", detail.data)
        self.assertEqual(detail.data["data"]["event"]["name"], "API Event")

    def test_export_csv(self):
        grant(self.user, COORDINATOR)
        self.client.force_authenticate(self.user)
        # Explicit ?fmt=csv: guards against the DRF "format" reserved-param 404.
        resp = self.client.get(
            f"/api/event-reports/{self.report.id}/export/", {"fmt": "csv"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/csv")
        self.assertIn("attachment", resp["Content-Disposition"])
        self.assertIn(b"Event report", resp.content)

    def test_export_csv_is_default(self):
        grant(self.user, COORDINATOR)
        self.client.force_authenticate(self.user)
        resp = self.client.get(f"/api/event-reports/{self.report.id}/export/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/csv")

    def test_export_json(self):
        grant(self.user, COORDINATOR)
        self.client.force_authenticate(self.user)
        resp = self.client.get(
            f"/api/event-reports/{self.report.id}/export/", {"fmt": "json"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/json")
        self.assertIn(".json", resp["Content-Disposition"])

    def test_is_read_only(self):
        grant(self.user, COORDINATOR)
        self.client.force_authenticate(self.user)
        resp = self.client.post("/api/event-reports/", {})
        self.assertEqual(resp.status_code, 405)


class ReportGenerateApiTest(TestCase):
    """The POST that roadmap J6 asked for: take a snapshot without leaving the app.

    Generation used to exist only as a Django admin action and a management
    command, so a Koordinator — who deliberately has no admin access — could not
    refresh the numbers at all.
    """

    def setUp(self):
        self.event = Event.objects.create(
            name="Generate Event",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 2),
        )
        self.client = APIClient()

    def _user(self, username, role=None):
        user = AdminUser.objects.create_user(username, name=username.title())
        if role:
            grant(user, role)
        return user

    def test_coordinator_can_generate(self):
        user = self._user("coordinator", COORDINATOR)
        self.client.force_authenticate(user)
        resp = self.client.post(
            "/api/event-reports/generate/", {"event": str(self.event.id)}
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(EventReport.objects.count(), 1)
        report = EventReport.objects.get()
        self.assertEqual(report.event, self.event)
        # Attribution matters: a snapshot is a record, and "who took it" is
        # part of the record.
        self.assertEqual(report.generated_by, user)
        # The response carries the full snapshot, so the page can show the new
        # report without a second round trip.
        self.assertEqual(resp.data["data"]["event"]["name"], "Generate Event")

    def test_volunteer_is_refused(self):
        """A volunteer holds ``view_eventreport`` but not ``add_``.

        This is the assertion that would catch someone "simplifying" the
        endpoint onto IsAuthenticated later.
        """
        self.client.force_authenticate(self._user("volunteer", VOLUNTEER))
        resp = self.client.post(
            "/api/event-reports/generate/", {"event": str(self.event.id)}
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(EventReport.objects.count(), 0)

    def test_requires_authentication(self):
        resp = self.client.post(
            "/api/event-reports/generate/", {"event": str(self.event.id)}
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(EventReport.objects.count(), 0)

    def test_repeat_generation_appends_a_second_snapshot(self):
        """Snapshots accumulate; they are never overwritten.

        A report records what the numbers were at a moment in time, taken
        before PII is deleted. Collapsing repeats into an ``update_or_create``
        would destroy the earlier picture — the one thing the model exists to
        preserve — so this asserts the append explicitly rather than leaving it
        to be "tidied up" later.
        """
        self.client.force_authenticate(self._user("coordinator", COORDINATOR))
        first = self.client.post(
            "/api/event-reports/generate/", {"event": str(self.event.id)}
        )
        second = self.client.post(
            "/api/event-reports/generate/", {"event": str(self.event.id)}
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(EventReport.objects.count(), 2)
        self.assertNotEqual(first.data["id"], second.data["id"])

    def test_missing_event_is_a_400(self):
        self.client.force_authenticate(self._user("coordinator", COORDINATOR))
        resp = self.client.post("/api/event-reports/generate/", {})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(EventReport.objects.count(), 0)

    def test_malformed_event_id_is_a_400_not_a_500(self):
        self.client.force_authenticate(self._user("coordinator", COORDINATOR))
        resp = self.client.post("/api/event-reports/generate/", {"event": "not-a-uuid"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(EventReport.objects.count(), 0)

    def test_unknown_event_is_a_404(self):
        self.client.force_authenticate(self._user("coordinator", COORDINATOR))
        resp = self.client.post(
            "/api/event-reports/generate/",
            {"event": "00000000-0000-0000-0000-000000000000"},
        )
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(EventReport.objects.count(), 0)
