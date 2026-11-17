"""A Volontär may grant a ticket at the door -- through the grant action only.

Owner decision 2026-10-01. The mechanism (a dedicated ``.../grant/`` action
gated on ``events.grant_*_at_door``, not ``add_*ticket``) is argued in
``accounts/roles.py`` and ``events/views.py``; these tests pin both halves:
the grant works, and it opened nothing else.

The positive case comes first on purpose. A denial test passes trivially against
a broken or missing route, so each denial below sits next to a grant that is
proven to succeed on the same fixtures.
"""

import importlib

from django.contrib.admin.sites import site as admin_site
from django.contrib.auth.models import Group, Permission
from django.db import connection
from decimal import Decimal

from django.test import RequestFactory, TestCase

from accounts.roles import (
    ADMINISTRATOR,
    COORDINATOR,
    ROLE_PERMISSIONS,
    VOLUNTEER,
)
from accounts.tests_roles import RoleFixtureMixin, make_user
from checkins.models import AuditLog
from events.models import Event, EventTicket, SessionTicket, TicketRule
from families.models import Child
from registrations.models import Registration
from registrations.tokens import generate_verification_token, hash_token

GRANT_PERMISSIONS = {
    "events.grant_eventticket_at_door",
    "events.grant_sessionticket_at_door",
}
TICKET_MODELS = ("eventticket", "sessionticket", "ticket")


class VolunteerGrantsAtTheDoorTests(RoleFixtureMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.session.ticket_rule = TicketRule.ALL
        self.session.save()
        # The fixture child already holds an event ticket; this one holds none.
        self.walk_in = Child.objects.create(
            first_name="Nils", last_name="Andersson", family=self.family
        )

    def test_volunteer_can_grant_a_session_ticket(self):
        response = self.as_volunteer().post(
            "/api/session-tickets/grant/",
            {"child": str(self.walk_in.id), "session": str(self.session.id)},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["ticket_type"], "SESSION_TICKET")
        self.assertTrue(
            SessionTicket.objects.filter(
                attendee=self.walk_in, session=self.session
            ).exists()
        )

    def test_volunteer_can_grant_an_event_ticket(self):
        response = self.as_volunteer().post(
            "/api/event-tickets/grant/",
            {"child": str(self.walk_in.id), "session": str(self.session.id)},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["ticket_type"], "EVENT_PASS")
        self.assertTrue(
            EventTicket.objects.filter(attendee=self.walk_in, event=self.event).exists()
        )

    def test_volunteer_can_grant_to_an_adult(self):
        response = self.as_volunteer().post(
            "/api/session-tickets/grant/",
            {"child": str(self.parent.id), "session": str(self.session.id)},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)

    def test_grant_validates_like_any_create(self):
        response = self.as_volunteer().post(
            "/api/session-tickets/grant/", {}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_anonymous_cannot_grant(self):
        for path in ("/api/session-tickets/grant/", "/api/event-tickets/grant/"):
            with self.subTest(path=path):
                self.assertIn(
                    self.client.post(path, {}, format="json").status_code, (401, 403)
                )

    # -- nothing broader ----------------------------------------------------
    def test_grant_proves_the_denials_below_are_real(self):
        """Same user, same fixtures: the grant route is open, the general ones are not."""
        volunteer = self.as_volunteer()
        self.assertEqual(
            volunteer.post(
                "/api/session-tickets/grant/",
                {"child": str(self.walk_in.id), "session": str(self.session.id)},
                format="json",
            ).status_code,
            201,
        )
        general = {"child": str(self.walk_in.id), "session": str(self.session.id)}
        self.assertEqual(
            volunteer.post("/api/session-tickets/", general, format="json").status_code,
            403,
        )

    def test_volunteer_cannot_post_to_the_general_ticket_endpoints(self):
        volunteer = self.as_volunteer()
        for path, body in (
            (
                "/api/event-tickets/",
                {"child": str(self.walk_in.id), "event": str(self.event.id)},
            ),
            (
                "/api/session-tickets/",
                {"child": str(self.walk_in.id), "session": str(self.session.id)},
            ),
            ("/api/tickets/", {}),
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    volunteer.post(path, body, format="json").status_code, 403
                )
        self.assertFalse(EventTicket.objects.filter(attendee=self.walk_in).exists())
        self.assertFalse(SessionTicket.objects.filter(attendee=self.walk_in).exists())

    def test_volunteer_cannot_change_or_delete_a_ticket(self):
        volunteer = self.as_volunteer()
        url = f"/api/event-tickets/{self.event_ticket.id}/"
        self.assertEqual(volunteer.get(url).status_code, 200)
        self.assertEqual(
            volunteer.patch(
                url, {"event": str(self.event.id)}, format="json"
            ).status_code,
            403,
        )
        self.assertEqual(volunteer.delete(url).status_code, 403)
        self.assertTrue(EventTicket.objects.filter(pk=self.event_ticket.pk).exists())

    def test_grant_route_does_not_serve_other_verbs(self):
        volunteer = self.as_volunteer()
        for path in ("/api/session-tickets/grant/", "/api/event-tickets/grant/"):
            with self.subTest(path=path):
                self.assertEqual(volunteer.get(path).status_code, 405)

    def test_volunteer_holds_no_add_change_or_delete_on_ticket_models(self):
        volunteer = ROLE_PERMISSIONS[VOLUNTEER]
        for model in TICKET_MODELS:
            for verb in ("add", "change", "delete"):
                with self.subTest(permission=f"{verb}_{model}"):
                    self.assertNotIn(f"events.{verb}_{model}", volunteer)
                    self.assertFalse(self.volunteer.has_perm(f"events.{verb}_{model}"))

    def test_volunteer_gained_exactly_the_two_grant_permissions(self):
        """The decision changes the volunteer's *write* surface by these two and no more."""
        writes = {
            label
            for label in ROLE_PERMISSIONS[VOLUNTEER]
            if label.split(".", 1)[1].split("_", 1)[0] not in ("view",)
        }
        self.assertLessEqual(GRANT_PERMISSIONS, writes)
        # Everything else the volunteer may write is the pre-existing door set.
        self.assertEqual(
            writes - GRANT_PERMISSIONS,
            {
                "checkins.add_checkinrecord",
                "checkins.change_checkinrecord",
                "printing.add_printjob",
                "printing.change_printjob",
                "registrations.change_registration",
                "registrations.change_payment",
            },
        )

    def test_django_admin_offers_a_volunteer_no_ticket_writes(self):
        """Even with ``is_staff`` forced on, the grant permissions open no admin form."""
        self.volunteer.is_staff = True
        request = RequestFactory().get("/admin/")
        request.user = self.volunteer
        for model in (EventTicket, SessionTicket):
            model_admin = admin_site._registry.get(model)
            if model_admin is None:
                continue
            with self.subTest(model=model.__name__):
                self.assertFalse(model_admin.has_add_permission(request))
                self.assertFalse(model_admin.has_change_permission(request))
                self.assertFalse(model_admin.has_delete_permission(request))


class DoorGrantRefusalTests(RoleFixtureMixin, TestCase):
    """The grant is for the session being checked into, nothing wider."""

    def setUp(self):
        super().setUp()
        self.session.ticket_rule = TicketRule.CHILDREN
        self.session.save()
        self.walk_in = Child.objects.create(
            first_name="Nils", last_name="Andersson", family=self.family
        )

    def post(self, kind, attendee=None, session=None):
        return self.as_volunteer().post(
            f"/api/{kind}-tickets/grant/",
            {
                "child": str((attendee or self.walk_in).id),
                "session": str((session or self.session).id),
            },
            format="json",
        )

    def assertRefused(self, response, code):
        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(response.json()["code"], code)
        self.assertTrue(response.json()["error"])
        self.assertFalse(AuditLog.objects.filter(action="ticket_granted_at_door"))

    def test_happy_path_writes_exactly_one_audit_row(self):
        for kind, model in (("event", EventTicket), ("session", SessionTicket)):
            with self.subTest(kind=kind):
                AuditLog.objects.all().delete()
                model.objects.filter(attendee=self.walk_in).delete()
                self.assertEqual(self.post(kind).status_code, 201)
                rows = AuditLog.objects.filter(action="ticket_granted_at_door")
                self.assertEqual(rows.count(), 1)
                row = rows.get()
                self.assertEqual(row.user, self.volunteer)
                self.assertEqual(row.details["attendee_id"], str(self.walk_in.id))
                self.assertEqual(row.details["session_id"], str(self.session.id))
                self.assertEqual(row.details["event_id"], str(self.event.id))

    def test_event_ticket_event_comes_from_the_session(self):
        other = Event.objects.create(
            name="Annat",
            start_date=self.event.start_date,
            end_date=self.event.end_date,
            price=Decimal("0"),
        )
        response = self.as_volunteer().post(
            "/api/event-tickets/grant/",
            {
                "child": str(self.walk_in.id),
                "session": str(self.session.id),
                "event": str(other.id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(
            EventTicket.objects.filter(attendee=self.walk_in, event=self.event)
        )
        self.assertFalse(EventTicket.objects.filter(event=other))

    def test_inactive_session_is_refused(self):
        self.session.is_active = False
        self.session.save()
        for kind in ("event", "session"):
            with self.subTest(kind=kind):
                self.assertRefused(self.post(kind), "session_not_active")

    def test_open_rule_is_refused(self):
        self.session.ticket_rule = TicketRule.OPEN
        self.session.save()
        for kind in ("event", "session"):
            with self.subTest(kind=kind):
                self.assertRefused(self.post(kind), "ticket_not_required")

    def test_adult_on_children_rule_is_refused(self):
        for kind in ("event", "session"):
            with self.subTest(kind=kind):
                self.assertRefused(self.post(kind, self.parent), "ticket_not_required")

    def test_ticket_of_cancelled_registration_gets_a_coded_error(self):
        registration = Registration.objects.create(
            event=self.event,
            contact_email="x@example.com",
            family=self.family,
            status=Registration.Status.CANCELLED,
        )
        EventTicket.objects.create(
            attendee=self.walk_in, event=self.event, registration=registration
        )
        response = self.post("event")
        self.assertRefused(response, "registration_cancelled")
        self.assertIn("Koordinator", response.json()["error"])
        self.assertEqual(EventTicket.objects.filter(attendee=self.walk_in).count(), 1)

    def _cancel_fixture_registration(self):
        # The fixture family already holds one live registration for the event.
        self.registration.status = Registration.Status.CANCELLED
        self.registration.save()

    def test_cancelled_registration_without_a_ticket_is_refused(self):
        self._cancel_fixture_registration()
        for kind in ("event", "session"):
            with self.subTest(kind=kind):
                response = self.post(kind)
                self.assertRefused(response, "registration_cancelled")
                self.assertIn("Koordinator", response.json()["error"])
                self.assertFalse(EventTicket.objects.filter(attendee=self.walk_in))
                self.assertFalse(SessionTicket.objects.filter(attendee=self.walk_in))

    def test_cancelled_plus_active_registration_may_be_granted(self):
        Registration.objects.create(
            event=self.event,
            contact_email="x@example.com",
            family=self.family,
            status=Registration.Status.CANCELLED,
            verification_token_hash=hash_token(generate_verification_token()),
        )
        for kind in ("event", "session"):
            with self.subTest(kind=kind):
                self.assertEqual(self.post(kind).status_code, 201)
        self.assertEqual(
            AuditLog.objects.filter(action="ticket_granted_at_door").count(), 2
        )

    def test_existing_valid_ticket_is_refused_not_a_500(self):
        SessionTicket.objects.create(attendee=self.walk_in, session=self.session)
        self.assertRefused(self.post("session"), "already_ticketed")


class OtherRolesUnchangedTests(RoleFixtureMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.session.ticket_rule = TicketRule.ALL
        self.session.save()
        self.walk_in = Child.objects.create(
            first_name="Nils", last_name="Andersson", family=self.family
        )

    def test_coordinator_can_still_use_the_general_endpoints(self):
        response = self.as_coordinator().post(
            "/api/session-tickets/",
            {"child": str(self.walk_in.id), "session": str(self.session.id)},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)

    def test_coordinator_can_also_grant_at_the_door(self):
        response = self.as_coordinator().post(
            "/api/event-tickets/grant/",
            {"child": str(self.walk_in.id), "session": str(self.session.id)},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)

    def test_coordinator_and_administrator_keep_every_ticket_permission(self):
        for role in (COORDINATOR, ADMINISTRATOR):
            for model in TICKET_MODELS:
                for verb in ("view", "add", "change", "delete"):
                    with self.subTest(role=role, permission=f"{verb}_{model}"):
                        self.assertIn(f"events.{verb}_{model}", ROLE_PERMISSIONS[role])
            self.assertLessEqual(GRANT_PERMISSIONS, ROLE_PERMISSIONS[role])

    def test_administrator_has_nothing_the_coordinator_lacks_on_tickets(self):
        tickets = lambda role: {  # noqa: E731
            p for p in ROLE_PERMISSIONS[role] if "ticket" in p
        }
        self.assertEqual(tickets(ADMINISTRATOR), tickets(COORDINATOR))


class ExistingDatabaseMigrationTests(TestCase):
    """0005 must reach groups seeded before this decision, without touching others."""

    @classmethod
    def _migration(cls):
        return importlib.import_module(
            "accounts.migrations.0005_grant_door_ticket_permissions"
        )

    def _revoke(self):
        grants = Permission.objects.filter(
            content_type__app_label="events",
            codename__in=[p.split(".")[1] for p in GRANT_PERMISSIONS],
        )
        self.assertEqual(grants.count(), 2)
        for name in (VOLUNTEER, COORDINATOR, ADMINISTRATOR):
            Group.objects.get(name=name).permissions.remove(*grants)
        return grants

    def test_codenames_in_the_migration_match_roles_py(self):
        migration = self._migration()
        in_migration = {f"{app}.{code}" for app, code in migration.DOOR_PERMISSIONS}
        self.assertEqual(in_migration, GRANT_PERMISSIONS)
        self.assertLessEqual(in_migration, ROLE_PERMISSIONS[VOLUNTEER])

    def test_forwards_restores_the_grant_on_a_previously_seeded_database(self):
        from django.apps import apps

        self._revoke()
        volunteer = Group.objects.get(name=VOLUNTEER)
        self.assertFalse(volunteer.permissions.filter(codename__endswith="at_door"))
        with connection.schema_editor() as editor:
            self._migration().forwards(apps, editor)
        for name in (VOLUNTEER, COORDINATOR, ADMINISTRATOR):
            with self.subTest(group=name):
                self.assertEqual(
                    Group.objects.get(name=name)
                    .permissions.filter(codename__endswith="_at_door")
                    .count(),
                    2,
                )

    def test_forwards_is_idempotent_and_leaves_other_groups_alone(self):
        from django.apps import apps

        other = Group.objects.create(name="Kök")
        with connection.schema_editor() as editor:
            self._migration().forwards(apps, editor)
            self._migration().forwards(apps, editor)
        self.assertEqual(other.permissions.count(), 0)
        self.assertEqual(
            Group.objects.get(name=VOLUNTEER).permissions.count(),
            len(ROLE_PERMISSIONS[VOLUNTEER]),
        )

    def test_backwards_removes_only_the_two_grants(self):
        from django.apps import apps

        before = Group.objects.get(name=VOLUNTEER).permissions.count()
        with connection.schema_editor() as editor:
            self._migration().backwards(apps, editor)
        self.assertEqual(
            Group.objects.get(name=VOLUNTEER).permissions.count(), before - 2
        )
        self.assertEqual(make_user("x", VOLUNTEER).has_perm("events.view_event"), True)
