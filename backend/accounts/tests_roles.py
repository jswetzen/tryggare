"""Role tests: seeded groups, per-endpoint authorisation, and the admin scoping.

The 403 tests below are deliberately one-per-endpoint rather than a loop over a
list or a single "volunteer can't write" smoke test. A permission regression
should name the endpoint it broke in the failure line, because that is the whole
diagnosis: "VolunteerIsDeniedTests.test_event_reports_list_is_denied" is a
finished bug report, whereas "test_restricted_endpoints[17]" is the start of an
investigation. It costs repetition and it is worth it.

Each restricted endpoint is asserted from three directions where applicable:

* a Volontär gets 403,
* a Koordinator gets something other than 403 (the positive direction — a test
  suite that only asserts denial passes just as well when the endpoint is
  broken for everyone),
* an anonymous caller is rejected.
"""

from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

from django.contrib.auth.models import Group, Permission
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import AdminUser
from accounts.roles import ADMINISTRATOR, COORDINATOR, ROLE_NAMES, VOLUNTEER
from accounts.roles import ROLE_PERMISSIONS
from checkins.models import AuditLog, CheckInRecord, QRCode
from events.models import Event, EventTicket, Session
from families.models import Child, Family, Parent
from imports.models import FestivalProImportSource, ImportRun, ImportSource
from printing.models import Printer, PrintJob
from registrations.models import Payment, Registration
from registrations.tokens import generate_verification_token, hash_token
from reports.models import EventReport


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


def make_user(username, role=None, *, superuser=False):
    if superuser:
        return AdminUser.objects.create_superuser(username, "pw-12345678")
    user = AdminUser.objects.create_user(username, "pw-12345678", name=username.title())
    if role:
        user.groups.add(Group.objects.get(name=role))
    return user


class RoleFixtureMixin:
    """One event, one family, one live check-in, one of everything else.

    Built in ``setUp`` rather than ``setUpTestData`` because several tests
    mutate group membership and permission caches, and a shared class-level
    user carries a cached ``_perm_cache`` between them.
    """

    def setUp(self):
        super().setUp()
        today = timezone.now().date()
        self.event = Event.objects.create(
            name="Sommarläger 2026",
            start_date=today,
            end_date=today + timedelta(days=4),
            price=Decimal("500.00"),
            registration_opens_at=timezone.now() - timedelta(days=1),
        )
        self.session = Session.objects.create(
            name="Lördag",
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=4),
            is_active=True,
            event=self.event,
        )
        self.family = Family.objects.create(last_name="Andersson")
        self.child = Child.objects.create(
            first_name="Alva", last_name="Andersson", family=self.family
        )
        self.parent = Parent.objects.create(
            first_name="Bea",
            last_name="Andersson",
            family=self.family,
            email="bea@example.com",
        )
        self.event_ticket = EventTicket.objects.create(
            attendee=self.child, event=self.event
        )

        self.staff = make_user("fixture-staff", superuser=True)
        self.checkin = CheckInRecord.objects.create(
            attendee=self.child, session=self.session, check_in_staff=self.staff
        )
        self.qr = QRCode.objects.create(
            code="ABC123", checkin_record=self.checkin, allocated_at=timezone.now()
        )
        self.printer = Printer.objects.create(name="Entrén")
        self.print_job = PrintJob.objects.create(
            checkin=self.checkin, printer=self.printer
        )
        self.audit = AuditLog.objects.create(
            action="qr_viewed", entity_type="Child", entity_id=str(self.child.id)
        )
        self.report = EventReport.objects.create(
            event=self.event,
            event_name=self.event.name,
            event_start_date=self.event.start_date,
            event_end_date=self.event.end_date,
            data={"sessions": []},
        )
        self.registration = Registration.objects.create(
            event=self.event,
            family=self.family,
            contact_email="bea@example.com",
            verification_token_hash=hash_token(generate_verification_token()),
            status=Registration.Status.PENDING_PAYMENT,
            verified_at=timezone.now(),
        )
        self.payment = Payment.objects.create(
            registration=self.registration,
            amount=Decimal("500.00"),
            status=Payment.Status.PENDING,
        )
        self.import_source = ImportSource.objects.create(name="FestivalPro-test")
        self.import_run = ImportRun.objects.create(source=self.import_source)

        self.volunteer = make_user("volontar", VOLUNTEER)
        self.coordinator = make_user("koordinator", COORDINATOR)

        self.client = APIClient()

    def as_volunteer(self):
        client = APIClient()
        client.force_authenticate(self.volunteer)
        return client

    def as_coordinator(self):
        client = APIClient()
        client.force_authenticate(self.coordinator)
        return client


# --------------------------------------------------------------------------
# The seed migration
# --------------------------------------------------------------------------


class SeededRoleTests(TestCase):
    def test_all_three_groups_exist(self):
        self.assertEqual(
            sorted(
                Group.objects.filter(name__in=ROLE_NAMES).values_list("name", flat=True)
            ),
            sorted(ROLE_NAMES),
        )

    def test_each_group_carries_exactly_its_declared_permissions(self):
        for name in ROLE_NAMES:
            with self.subTest(role=name):
                group = Group.objects.get(name=name)
                actual = {
                    f"{perm.content_type.app_label}.{perm.codename}"
                    for perm in group.permissions.select_related("content_type")
                }
                self.assertEqual(actual, set(ROLE_PERMISSIONS[name]))

    def test_seeded_permissions_all_resolved(self):
        """Every codename in the spec matched a real Permission row.

        The migration skips codenames it cannot find rather than crashing (so a
        model deleted years from now cannot make a fresh install unrunnable).
        That tolerance would also silently swallow a typo, so the count is
        pinned here instead.
        """
        for name in ROLE_NAMES:
            with self.subTest(role=name):
                self.assertEqual(
                    Group.objects.get(name=name).permissions.count(),
                    len(ROLE_PERMISSIONS[name]),
                )

    def test_dsar_permissions_exist(self):
        for codename in ("export_family_dsar", "erase_family_dsar"):
            with self.subTest(codename=codename):
                self.assertTrue(
                    Permission.objects.filter(
                        content_type__app_label="families", codename=codename
                    ).exists()
                )

    def test_hierarchy_is_a_strict_superset_chain(self):
        volunteer = ROLE_PERMISSIONS[VOLUNTEER]
        coordinator = ROLE_PERMISSIONS[COORDINATOR]
        administrator = ROLE_PERMISSIONS[ADMINISTRATOR]
        self.assertLess(volunteer, coordinator)
        self.assertLess(coordinator, administrator)

    def test_no_role_can_destroy_the_audit_log_or_mint_a_printer_token(self):
        withheld = {
            "checkins.delete_auditlog",
            "checkins.add_auditlog",
            "checkins.change_auditlog",
            "printing.add_printer",
            "printing.delete_printer",
        }
        for name in ROLE_NAMES:
            with self.subTest(role=name):
                self.assertEqual(ROLE_PERMISSIONS[name] & withheld, frozenset())


class SeedRerunTests(TestCase):
    """The consequential property: an organisation's edits survive a re-run.

    Calling the migration's ``forwards`` again is the closest a test can get to
    "the seed ran a second time" — which is what a ``post_migrate`` hook, a
    re-seed management command, or an unapply/reapply cycle would each do.
    """

    def test_customised_group_is_left_alone(self):
        forwards, _backwards = _seed_functions()
        group = Group.objects.get(name=VOLUNTEER)

        # An organisation decides its volunteers may also read the audit log,
        # and drops a permission it does not want them to have.
        extra = Permission.objects.get(
            content_type__app_label="checkins", codename="view_auditlog"
        )
        removed = Permission.objects.get(
            content_type__app_label="printing", codename="add_printjob"
        )
        group.permissions.add(extra)
        group.permissions.remove(removed)
        customised = set(group.permissions.values_list("pk", flat=True))

        forwards(_historical_apps(), _schema_editor())

        group.refresh_from_db()
        self.assertEqual(
            set(group.permissions.values_list("pk", flat=True)), customised
        )

    def test_rerun_recreates_a_group_an_operator_deleted(self):
        forwards, _backwards = _seed_functions()
        Group.objects.filter(name=COORDINATOR).delete()

        forwards(_historical_apps(), _schema_editor())

        group = Group.objects.get(name=COORDINATOR)
        actual = {
            f"{perm.content_type.app_label}.{perm.codename}"
            for perm in group.permissions.select_related("content_type")
        }
        self.assertEqual(actual, set(ROLE_PERMISSIONS[COORDINATOR]))

    def test_reverse_removes_exactly_the_three_seeded_groups(self):
        _forwards, backwards = _seed_functions()
        Group.objects.create(name="Kökspersonal")  # a customer's fourth role

        backwards(_historical_apps(), _schema_editor())

        self.assertFalse(Group.objects.filter(name__in=ROLE_NAMES).exists())
        self.assertTrue(Group.objects.filter(name="Kökspersonal").exists())

    def test_forward_reverse_forward_round_trips(self):
        forwards, backwards = _seed_functions()
        before = {
            name: set(
                Group.objects.get(name=name).permissions.values_list("pk", flat=True)
            )
            for name in ROLE_NAMES
        }

        backwards(_historical_apps(), _schema_editor())
        forwards(_historical_apps(), _schema_editor())

        after = {
            name: set(
                Group.objects.get(name=name).permissions.values_list("pk", flat=True)
            )
            for name in ROLE_NAMES
        }
        self.assertEqual(after, before)


def _seed_functions():
    """Import the seed migration's forwards/backwards by module path.

    ``0003_seed_roles`` is not a valid Python identifier, so it cannot be
    imported with an ``import`` statement.
    """
    import importlib

    module = importlib.import_module("accounts.migrations.0003_seed_roles")
    return module.forwards, module.backwards


def _historical_apps():
    """The real app registry stands in for the migration's historical one.

    The seed only touches ``auth.Group``/``auth.Permission``, whose historical
    and current states are identical here, and ``apps.get_model`` has the same
    signature either way.
    """
    from django.apps import apps

    return apps


def _schema_editor():
    """Minimal stand-in exposing the one attribute the seed reads."""
    from django.db import connection

    return SimpleNamespace(connection=connection)


# --------------------------------------------------------------------------
# is_staff <-> Administratör membership
# --------------------------------------------------------------------------


class IsStaffSyncTests(TestCase):
    def setUp(self):
        self.user = AdminUser.objects.create_user(
            "nyanstalld", "pw-12345678", name="Ny"
        )

    def test_joining_administrator_grants_is_staff(self):
        self.user.groups.add(Group.objects.get(name=ADMINISTRATOR))
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_staff)

    def test_leaving_administrator_revokes_is_staff(self):
        group = Group.objects.get(name=ADMINISTRATOR)
        self.user.groups.add(group)
        self.user.groups.remove(group)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_staff)

    def test_coordinator_membership_does_not_grant_is_staff(self):
        self.user.groups.add(Group.objects.get(name=COORDINATOR))
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_staff)

    def test_reverse_relation_is_synced_too(self):
        Group.objects.get(name=ADMINISTRATOR).user_set.add(self.user)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_staff)

    def test_superuser_is_never_demoted(self):
        root = AdminUser.objects.create_superuser("root", "pw-12345678")
        root.groups.add(Group.objects.get(name=ADMINISTRATOR))
        root.groups.clear()
        root.refresh_from_db()
        self.assertTrue(root.is_staff)


# --------------------------------------------------------------------------
# The session payload the frontend gates on
# --------------------------------------------------------------------------


class SessionPayloadTests(TestCase):
    def setUp(self):
        self.user = make_user("koord", COORDINATOR)
        self.client = APIClient()

    def test_check_auth_returns_roles_and_permissions(self):
        self.client.force_authenticate(self.user)
        payload = self.client.get(reverse("auth-check")).json()

        self.assertTrue(payload["authenticated"])
        user = payload["user"]
        self.assertEqual(
            set(user),
            {
                "id",
                "username",
                "name",
                "is_staff",
                "is_superuser",
                "roles",
                "permissions",
            },
        )
        self.assertEqual(user["roles"], [COORDINATOR])
        self.assertIn("reports.view_eventreport", user["permissions"])
        self.assertEqual(user["permissions"], sorted(user["permissions"]))

    def test_volunteer_payload_omits_the_permissions_it_lacks(self):
        volunteer = make_user("vol", VOLUNTEER)
        self.client.force_authenticate(volunteer)
        permissions = self.client.get(reverse("auth-check")).json()["user"][
            "permissions"
        ]

        self.assertIn("checkins.add_checkinrecord", permissions)
        self.assertNotIn("reports.view_eventreport", permissions)
        self.assertNotIn("checkins.view_auditlog", permissions)
        self.assertNotIn("families.export_family_dsar", permissions)

    def test_is_staff_no_longer_implies_app_privilege(self):
        """The single meaning ``is_staff`` retains: Django admin, nothing else.

        A Koordinator holds every app permission and is not staff; that pairing
        is exactly what the frontend used to be unable to express.
        """
        self.client.force_authenticate(self.user)
        user = self.client.get(reverse("auth-check")).json()["user"]
        self.assertFalse(user["is_staff"])
        self.assertIn("reports.view_eventreport", user["permissions"])

    def test_login_returns_the_same_shape(self):
        AdminUser.objects.filter(pk=self.user.pk).update(is_active=True)
        self.user.set_password("pw-12345678")
        self.user.save()
        response = self.client.post(
            reverse("auth-login"),
            {"username": self.user.username, "password": "pw-12345678"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.json()["user"]),
            {
                "id",
                "username",
                "name",
                "is_staff",
                "is_superuser",
                "roles",
                "permissions",
            },
        )

    def test_anonymous_check_auth_still_answers(self):
        payload = APIClient().get(reverse("auth-check")).json()
        self.assertFalse(payload["authenticated"])
        self.assertIsNone(payload["user"])


# --------------------------------------------------------------------------
# Volontär is denied — one test per restricted endpoint.
# --------------------------------------------------------------------------


class VolunteerIsDeniedTests(RoleFixtureMixin, TestCase):
    # -- reports -----------------------------------------------------------
    def test_event_reports_list_is_denied(self):
        self.assertEqual(
            self.as_volunteer().get("/api/event-reports/").status_code, 403
        )

    def test_event_reports_detail_is_denied(self):
        self.assertEqual(
            self.as_volunteer()
            .get(f"/api/event-reports/{self.report.id}/")
            .status_code,
            403,
        )

    def test_event_report_export_is_denied(self):
        self.assertEqual(
            self.as_volunteer()
            .get(f"/api/event-reports/{self.report.id}/export/")
            .status_code,
            403,
        )

    # -- audit log ---------------------------------------------------------
    def test_audit_logs_list_is_denied(self):
        self.assertEqual(self.as_volunteer().get("/api/audit-logs/").status_code, 403)

    def test_audit_logs_detail_is_denied(self):
        self.assertEqual(
            self.as_volunteer().get(f"/api/audit-logs/{self.audit.id}/").status_code,
            403,
        )

    # -- DSAR --------------------------------------------------------------
    def test_family_dsar_export_is_denied(self):
        self.assertEqual(
            self.as_volunteer()
            .get(f"/api/families/{self.family.id}/export/")
            .status_code,
            403,
        )

    def test_family_dsar_erase_is_denied(self):
        self.assertEqual(
            self.as_volunteer()
            .post(f"/api/families/{self.family.id}/erase/")
            .status_code,
            403,
        )

    # -- events ------------------------------------------------------------
    def test_event_create_is_denied(self):
        self.assertEqual(
            self.as_volunteer()
            .post("/api/events/", {"name": "X"}, format="json")
            .status_code,
            403,
        )

    def test_event_update_is_denied(self):
        self.assertEqual(
            self.as_volunteer()
            .patch(f"/api/events/{self.event.id}/", {"name": "X"}, format="json")
            .status_code,
            403,
        )

    def test_event_delete_is_denied(self):
        self.assertEqual(
            self.as_volunteer().delete(f"/api/events/{self.event.id}/").status_code, 403
        )

    def test_session_create_is_denied(self):
        self.assertEqual(
            self.as_volunteer()
            .post("/api/sessions/", {"name": "X"}, format="json")
            .status_code,
            403,
        )

    def test_session_activate_is_denied(self):
        self.assertEqual(
            self.as_volunteer()
            .post(f"/api/sessions/{self.session.id}/activate/")
            .status_code,
            403,
        )

    def test_session_deactivate_is_denied(self):
        self.assertEqual(
            self.as_volunteer()
            .post(f"/api/sessions/{self.session.id}/deactivate/")
            .status_code,
            403,
        )

    def test_deprecated_tickets_list_is_denied(self):
        self.assertEqual(self.as_volunteer().get("/api/tickets/").status_code, 403)

    def test_event_ticket_create_is_denied(self):
        self.assertEqual(
            self.as_volunteer()
            .post("/api/event-tickets/", {}, format="json")
            .status_code,
            403,
        )

    def test_session_ticket_create_is_denied(self):
        self.assertEqual(
            self.as_volunteer()
            .post("/api/session-tickets/", {}, format="json")
            .status_code,
            403,
        )

    # -- families ----------------------------------------------------------
    def test_family_create_is_denied(self):
        self.assertEqual(
            self.as_volunteer().post("/api/families/", {}, format="json").status_code,
            403,
        )

    def test_family_update_is_denied(self):
        self.assertEqual(
            self.as_volunteer()
            .patch(
                f"/api/families/{self.family.id}/", {"last_name": "X"}, format="json"
            )
            .status_code,
            403,
        )

    def test_family_delete_is_denied(self):
        self.assertEqual(
            self.as_volunteer().delete(f"/api/families/{self.family.id}/").status_code,
            403,
        )

    def test_parent_create_is_denied(self):
        self.assertEqual(
            self.as_volunteer().post("/api/parents/", {}, format="json").status_code,
            403,
        )

    def test_parent_delete_is_denied(self):
        self.assertEqual(
            self.as_volunteer().delete(f"/api/parents/{self.parent.pk}/").status_code,
            403,
        )

    def test_child_create_is_denied(self):
        self.assertEqual(
            self.as_volunteer().post("/api/children/", {}, format="json").status_code,
            403,
        )

    def test_child_delete_is_denied(self):
        self.assertEqual(
            self.as_volunteer().delete(f"/api/children/{self.child.pk}/").status_code,
            403,
        )

    # -- check-ins ---------------------------------------------------------
    def test_checkin_hard_delete_is_denied(self):
        """Volontär may undo a check-in (a POST action); erasing the row is not
        the same act and is not theirs."""
        self.assertEqual(
            self.as_volunteer().delete(f"/api/checkins/{self.checkin.id}/").status_code,
            403,
        )

    # -- printing ----------------------------------------------------------
    def test_printer_provision_is_denied(self):
        self.assertEqual(
            self.as_volunteer()
            .post("/api/printing/printers/", {"name": "Ny"}, format="json")
            .status_code,
            403,
        )

    def test_printer_rotate_token_is_denied(self):
        self.assertEqual(
            self.as_volunteer()
            .post(f"/api/printing/printers/{self.printer.id}/rotate-token/")
            .status_code,
            403,
        )

    def test_printer_revoke_token_is_denied(self):
        self.assertEqual(
            self.as_volunteer()
            .post(f"/api/printing/printers/{self.printer.id}/revoke-token/")
            .status_code,
            403,
        )

    def test_printer_delete_is_denied(self):
        self.assertEqual(
            self.as_volunteer()
            .delete(f"/api/printing/printers/{self.printer.id}/")
            .status_code,
            403,
        )

    def test_printer_rename_is_denied(self):
        self.assertEqual(
            self.as_volunteer()
            .patch(
                f"/api/printing/printers/{self.printer.id}/",
                {"name": "X"},
                format="json",
            )
            .status_code,
            403,
        )

    # -- imports (now on imports.* permissions, no longer on is_staff) ------
    def test_import_sources_list_is_denied(self):
        self.assertEqual(
            self.as_volunteer().get("/api/imports/sources/").status_code, 403
        )

    def test_import_source_create_is_denied(self):
        self.assertEqual(
            self.as_volunteer()
            .post("/api/imports/sources/", {}, format="json")
            .status_code,
            403,
        )

    def test_import_prefix_discovery_is_denied(self):
        self.assertEqual(
            self.as_volunteer()
            .post("/api/imports/discover-prefixes/", {}, format="json")
            .status_code,
            403,
        )


# --------------------------------------------------------------------------
# The positive direction.
# --------------------------------------------------------------------------


class CoordinatorReachesWhatVolunteerCannotTests(RoleFixtureMixin, TestCase):
    """Every assertion here has a matching denial above.

    Without these, deleting a URL route would make the whole 403 suite pass.
    """

    def test_event_reports_list(self):
        self.assertEqual(
            self.as_coordinator().get("/api/event-reports/").status_code, 200
        )

    def test_event_report_export(self):
        self.assertEqual(
            self.as_coordinator()
            .get(f"/api/event-reports/{self.report.id}/export/")
            .status_code,
            200,
        )

    def test_audit_logs_list(self):
        self.assertEqual(self.as_coordinator().get("/api/audit-logs/").status_code, 200)

    def test_family_dsar_export(self):
        self.assertEqual(
            self.as_coordinator()
            .get(f"/api/families/{self.family.id}/export/")
            .status_code,
            200,
        )

    def test_family_dsar_erase(self):
        response = self.as_coordinator().post(f"/api/families/{self.family.id}/erase/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Family.objects.filter(pk=self.family.pk).exists())

    def test_deprecated_tickets_list(self):
        self.assertEqual(self.as_coordinator().get("/api/tickets/").status_code, 200)

    def test_event_update(self):
        self.assertEqual(
            self.as_coordinator()
            .patch(
                f"/api/events/{self.event.id}/", {"name": "Nytt namn"}, format="json"
            )
            .status_code,
            200,
        )

    def test_session_activate(self):
        self.assertEqual(
            self.as_coordinator()
            .post(f"/api/sessions/{self.session.id}/activate/")
            .status_code,
            200,
        )

    def test_family_update(self):
        self.assertEqual(
            self.as_coordinator()
            .patch(
                f"/api/families/{self.family.id}/",
                {"last_name": "Bergström"},
                format="json",
            )
            .status_code,
            200,
        )

    def test_checkin_hard_delete(self):
        self.assertEqual(
            self.as_coordinator()
            .delete(f"/api/checkins/{self.checkin.id}/")
            .status_code,
            204,
        )

    def test_printer_rename(self):
        self.assertEqual(
            self.as_coordinator()
            .patch(
                f"/api/printing/printers/{self.printer.id}/",
                {"name": "Foajén"},
                format="json",
            )
            .status_code,
            200,
        )

    def test_import_sources_list(self):
        """Koordinator has held every ``imports.*`` grant since the seed; until
        the import API moved off ``IsAdminUser`` they were dead letters,
        because a Koordinator has no Django-admin account by design."""
        self.assertEqual(
            self.as_coordinator().get("/api/imports/sources/").status_code, 200
        )

    def test_import_prefix_discovery(self):
        response = self.as_coordinator().post(
            "/api/imports/discover-prefixes/",
            {"json_string": "{}"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

    def test_import_source_create(self):
        """Create is kept: a Koordinator must be able to configure a source."""
        response = self.as_coordinator().post(
            "/api/imports/sources/", {"name": "Ny källa"}, format="json"
        )
        self.assertEqual(response.status_code, 201)

    def test_import_run_end_to_end(self):
        """Run is kept: this is the capability decision 6 was explicit about
        keeping, precisely so a stale booking feed doesn't sit waiting on an
        administrator's password being shared."""
        response = self.as_coordinator().post(
            f"/api/imports/sources/{self.import_source.id}/run/",
            {"json_string": "{}", "field_mappings": {}},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    def test_coordinator_reaching_imports_is_not_django_admin(self):
        """The two must not travel together again — that was the whole point."""
        self.assertFalse(self.coordinator.is_staff)

    def test_coordinator_still_cannot_mint_a_printer_token(self):
        """The one place Koordinator is *not* a superset of the app.

        Provisioning and token rotation stay with ``is_superuser``; this is the
        assertion that keeps a future "coordinator should have everything"
        tidy-up from quietly reopening it.
        """
        client = self.as_coordinator()
        self.assertEqual(
            client.post(
                "/api/printing/printers/", {"name": "Ny"}, format="json"
            ).status_code,
            403,
        )
        self.assertEqual(
            client.post(
                f"/api/printing/printers/{self.printer.id}/rotate-token/"
            ).status_code,
            403,
        )

    def test_coordinator_cannot_delete_an_import_source(self):
        """Decision 6: import yes, delete no. Create/change/run stay above;
        this is the one grant that moved a tier up to Administratör.

        ``ImportRun`` and ``FestivalProImportSource`` have no corresponding
        case here — the API exposes no delete route for either (only
        ``/sources/<id>/`` has a DELETE verb), so the only way to erase either
        is Django admin, covered under ``CoordinatorImportDeleteAdminTests``
        below.
        """
        response = self.as_coordinator().delete(
            f"/api/imports/sources/{self.import_source.id}/"
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(ImportSource.objects.filter(pk=self.import_source.pk).exists())


class VolunteerCanStillWorkTheDoorTests(RoleFixtureMixin, TestCase):
    """Breaking the door job is the second-worst outcome of this increment.

    (The worst is breaking guest registration, covered below.)
    """

    def test_can_read_the_family_roster(self):
        self.assertEqual(self.as_volunteer().get("/api/families/").status_code, 200)

    def test_can_look_a_family_up_by_ticket_code(self):
        self.assertIn(
            self.as_volunteer().get("/api/families/by-ticket/?code=NOPE").status_code,
            (200, 404),
        )

    def test_can_read_events_and_sessions(self):
        client = self.as_volunteer()
        self.assertEqual(client.get("/api/events/").status_code, 200)
        self.assertEqual(client.get("/api/sessions/active/").status_code, 200)

    def test_can_check_a_child_in(self):
        other = Child.objects.create(
            first_name="Cornelia", last_name="Andersson", family=self.family
        )
        response = self.as_volunteer().post(
            "/api/checkins/check_in/",
            {"child": str(other.pk), "session": str(self.session.id)},
            format="json",
        )
        self.assertNotEqual(response.status_code, 403)

    def test_can_check_a_child_out(self):
        response = self.as_volunteer().post(
            f"/api/checkins/{self.checkin.id}/check_out/",
            {"picked_up_by": "Bea"},
            format="json",
        )
        self.assertNotEqual(response.status_code, 403)

    def test_can_read_the_print_queue(self):
        self.assertEqual(self.as_volunteer().get("/api/print-queue/").status_code, 200)

    def test_can_create_a_print_job(self):
        response = self.as_volunteer().post(
            "/api/printing/jobs/",
            {"checkin_id": str(self.checkin.id)},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    def test_can_reassign_a_print_job(self):
        response = self.as_volunteer().post(
            f"/api/printing/jobs/{self.print_job.id}/assign/",
            {"printer_id": str(self.printer.id)},
            format="json",
        )
        self.assertNotEqual(response.status_code, 403)

    def test_can_see_which_printers_exist(self):
        self.assertEqual(
            self.as_volunteer().get("/api/printing/printers/").status_code, 200
        )

    def test_can_take_payment_at_the_door(self):
        """Explicitly out of scope for restriction: door money stays."""
        response = self.as_volunteer().post(
            reverse("registration-mark-paid", args=[self.registration.id]),
            {"method": Payment.Method.SWISH},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

    def test_can_confirm_despite_balance(self):
        response = self.as_volunteer().post(
            reverse(
                "registration-confirm-despite-balance", args=[self.registration.id]
            ),
            {},
            format="json",
        )
        self.assertNotEqual(response.status_code, 403)


class AnonymousIsRejectedTests(RoleFixtureMixin, TestCase):
    def test_restricted_endpoints_reject_anonymous_callers(self):
        for path in (
            "/api/event-reports/",
            "/api/audit-logs/",
            "/api/families/",
            "/api/events/",
            "/api/checkins/",
            "/api/print-queue/",
            "/api/printing/printers/",
        ):
            with self.subTest(path=path):
                self.assertIn(APIClient().get(path).status_code, (401, 403))


# --------------------------------------------------------------------------
# The public surface. Breaking this is the worst outcome of the increment.
# --------------------------------------------------------------------------


class PublicSurfaceStillPublicTests(RoleFixtureMixin, TestCase):
    """Every ``AllowAny`` endpoint, asserted reachable without a session.

    These are not incidental leftovers: the guest registration flow, the QR page
    a parent scans off a wristband, and the login handshake are all necessarily
    unauthenticated. They are listed one per test so that a future blanket
    "lock everything down" change fails with the name of the guest step it
    broke.
    """

    def test_csrf_token(self):
        self.assertEqual(APIClient().get(reverse("csrf-token")).status_code, 200)

    def test_auth_check(self):
        self.assertEqual(APIClient().get(reverse("auth-check")).status_code, 200)

    def test_login(self):
        response = APIClient().post(
            reverse("auth-login"), {"username": "x", "password": "y"}, format="json"
        )
        self.assertEqual(response.status_code, 401)  # reached the view, not the gate

    def test_privacy_info(self):
        self.assertEqual(APIClient().get(reverse("privacy-info")).status_code, 200)

    def test_qr_info(self):
        self.assertEqual(
            APIClient().get(reverse("qr-info", args=[self.qr.code])).status_code, 200
        )

    def test_qr_reveal_safety_info(self):
        self.assertEqual(
            APIClient()
            .post(reverse("qr-reveal-safety-info", args=[self.qr.code]))
            .status_code,
            200,
        )

    def test_registration_event_info(self):
        self.assertEqual(
            APIClient()
            .get(reverse("registration-event-info", args=[self.event.id]))
            .status_code,
            200,
        )

    def test_registration_submit(self):
        response = APIClient().post(reverse("registration-submit"), {}, format="json")
        self.assertEqual(response.status_code, 400)  # validation, not authorisation

    def test_registration_verify(self):
        response = APIClient().get(reverse("registration-verify", args=["not-a-token"]))
        self.assertNotIn(response.status_code, (401, 403))

    def test_registration_payment_status(self):
        response = APIClient().post(
            reverse("registration-payment-status"), {}, format="json"
        )
        self.assertNotIn(response.status_code, (401, 403))

    def test_validate_promo_code(self):
        response = APIClient().post(
            reverse("registration-validate-promo-code"),
            {"event": str(self.event.id), "code": "NOPE"},
            format="json",
        )
        self.assertNotIn(response.status_code, (401, 403))

    def test_printer_label_page(self):
        """Not DRF: the printer client fetches this with no session at all."""
        response = self.client.get(reverse("print-job-label", args=[self.print_job.id]))
        self.assertNotIn(response.status_code, (401, 403))


# --------------------------------------------------------------------------
# Administratör's Django-admin scoping.
# --------------------------------------------------------------------------

# Same reason as registrations/tests_admin_index.py: the project ships
# WhiteNoise's manifest static storage, which refuses to resolve admin CSS
# unless collectstatic has run. Rendering an admin page is unrelated to
# static-asset hashing.
PLAIN_STATICFILES = override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    }
)


def _available_admin_actions(changelist_response):
    """Action names the rendered changelist actually offers this user.

    Read off the ModelAdmin rather than the rendered form, because Django omits
    the action form entirely when no action is available — which is the very
    case being asserted.
    """
    changelist = changelist_response.context["cl"]
    return set(changelist.model_admin.get_actions(changelist_response.wsgi_request))


@PLAIN_STATICFILES
class AdministratorAdminScopeTests(TestCase):
    """Rendered, not read off the migration.

    A permission list proves what was granted; only the rendered admin proves
    what that adds up to on screen.
    """

    def setUp(self):
        self.admin = AdminUser.objects.create_user(
            "org-admin", "pw-12345678", name="Org Admin"
        )
        self.admin.groups.add(Group.objects.get(name=ADMINISTRATOR))
        self.admin.refresh_from_db()
        self.client.force_login(self.admin)

    def test_group_membership_alone_opens_django_admin(self):
        self.assertTrue(self.admin.is_staff)
        self.assertEqual(self.client.get("/admin/").status_code, 200)

    def test_index_lists_the_screens_the_role_owns(self):
        body = self.client.get("/admin/").content.decode()
        for fragment in (
            "/admin/events/event/",
            "/admin/registrations/registration/",
            "/admin/registrations/payment/",
            "/admin/families/family/",
            "/admin/reports/eventreport/",
            "/admin/checkins/auditlog/",
            "/admin/auth/group/",
            "/admin/accounts/adminuser/",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, body)

    def test_audit_log_is_readable(self):
        self.assertEqual(self.client.get("/admin/checkins/auditlog/").status_code, 200)

    def test_audit_log_cannot_be_deleted(self):
        log = AuditLog.objects.create(
            action="qr_viewed", entity_type="Child", entity_id="x"
        )
        response = self.client.post(
            "/admin/checkins/auditlog/",
            {
                "action": "delete_selected",
                "_selected_action": [str(log.pk)],
                "index": 0,
            },
        )
        self.assertNotEqual(response.status_code, 500)
        self.assertTrue(AuditLog.objects.filter(pk=log.pk).exists())

    def test_audit_log_delete_view_is_forbidden(self):
        log = AuditLog.objects.create(
            action="qr_viewed", entity_type="Child", entity_id="x"
        )
        response = self.client.get(f"/admin/checkins/auditlog/{log.pk}/delete/")
        self.assertIn(response.status_code, (403, 302))
        self.assertTrue(AuditLog.objects.filter(pk=log.pk).exists())

    def test_printer_admin_is_read_only(self):
        """Administratör can see the printers and cannot provision one."""
        response = self.client.get("/admin/printing/printer/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(response.status_code, (200,))
        self.assertIn(
            self.client.get("/admin/printing/printer/add/").status_code, (403, 302)
        )

    def test_printer_token_rotation_is_not_offered_as_an_admin_action(self):
        """The hole this closes: admin actions have no permission check by
        default, so ``rotate_tokens`` would have run for anyone who could open
        the changelist — handing token rotation to the role that is explicitly
        denied it, through a screen rather than an endpoint."""
        Printer.objects.create(name="Entrén")
        response = self.client.get("/admin/printing/printer/")
        actions = _available_admin_actions(response)
        self.assertNotIn("rotate_tokens", actions)
        self.assertNotIn("revoke_tokens", actions)

    def test_printer_token_is_not_shown_to_a_non_superuser(self):
        """Reading the plaintext token is equivalent to holding the credential."""
        printer = Printer.objects.create(name="Foajén")
        body = self.client.get(
            f"/admin/printing/printer/{printer.pk}/change/"
        ).content.decode()
        self.assertNotIn(printer.token, body)

    def test_family_dsar_actions_are_offered(self):
        """The mirror of the printer case: Administratör *is* trusted with
        DSAR, so these actions must still be there."""
        response = self.client.get("/admin/families/family/")
        actions = _available_admin_actions(response)
        self.assertIn("export_as_json", actions)
        self.assertIn("erase_families", actions)

    def test_user_form_hides_is_superuser(self):
        body = self.client.get(
            f"/admin/accounts/adminuser/{self.admin.pk}/change/"
        ).content.decode()
        self.assertIn('name="is_staff"', body)
        self.assertNotIn('name="is_superuser"', body)

    def test_cannot_edit_a_superuser(self):
        """A superuser's record stays visible (an organisation should be able
        to see that we exist) but read-only: being able to reset a superuser's
        password is the same escalation by a slower route."""
        root = AdminUser.objects.create_superuser("root", "pw-12345678")
        response = self.client.get(f"/admin/accounts/adminuser/{root.pk}/change/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_save", response.content.decode())

        posted = self.client.post(
            f"/admin/accounts/adminuser/{root.pk}/change/",
            {"username": "hijacked", "name": "x", "is_active": "on"},
        )
        root.refresh_from_db()
        self.assertEqual(root.username, "root")
        self.assertIn(posted.status_code, (200, 302, 403))

    def test_permission_picker_offers_only_permissions_the_admin_holds(self):
        from accounts.admin import permissions_held_by

        offered = {
            f"{perm.content_type.app_label}.{perm.codename}"
            for perm in permissions_held_by(self.admin)
        }
        self.assertIn("events.change_event", offered)
        self.assertNotIn("checkins.delete_auditlog", offered)
        self.assertNotIn("printing.add_printer", offered)

    def test_cannot_compose_a_group_holding_a_withheld_permission(self):
        """The escalation this closes: build a group with delete_auditlog,
        join it, and the withheld list becomes a suggestion."""
        response = self.client.get("/admin/auth/group/add/")
        self.assertEqual(response.status_code, 200)
        choices = {
            f"{perm.content_type.app_label}.{perm.codename}"
            for perm in response.context["adminform"]
            .form.fields["permissions"]
            .queryset.select_related("content_type")
        }
        self.assertIn("events.change_event", choices)
        self.assertNotIn("checkins.delete_auditlog", choices)
        self.assertNotIn("printing.add_printer", choices)


@PLAIN_STATICFILES
class VolunteerAndCoordinatorHaveNoAdminTests(TestCase):
    def test_volunteer_cannot_reach_django_admin(self):
        user = make_user("vol-admin-test", VOLUNTEER)
        self.client.force_login(user)
        self.assertEqual(self.client.get("/admin/").status_code, 302)

    def test_coordinator_cannot_reach_django_admin(self):
        user = make_user("koord-admin-test", COORDINATOR)
        self.client.force_login(user)
        self.assertEqual(self.client.get("/admin/").status_code, 302)


@PLAIN_STATICFILES
class CoordinatorImportDeleteAdminTests(TestCase):
    """A Koordinator has no ``is_staff`` and gets a 302 at the front door of
    Django admin — ``VolunteerAndCoordinatorHaveNoAdminTests`` above already
    covers that. That alone would make this class redundant if the only
    question were "can a Koordinator reach /admin/". It isn't: the concern
    from c4ea9b2 is that Django admin actions and delete views carry no
    permission check of their own unless one is declared, so the API boundary
    could hold while the admin route stayed open — which the API-only test
    suite would report as closed.

    ``ImportSourceAdmin`` / ``ImportRunAdmin`` are plain ``ModelAdmin``
    subclasses with no custom actions or ``has_delete_permission`` override,
    so Django's own default (``request.user.has_perm("<app>.delete_<model>")``)
    is what's actually doing the work here — same as the audit log case. This
    class exercises that default directly, past the ``is_staff`` front door,
    so a future change to ``is_staff`` handling (or to these ModelAdmins)
    can't reopen deletion without a test failing right here.
    """

    def setUp(self):
        self.user = make_user("koord-staff-test", COORDINATOR)
        # Bypass the normal route to is_staff (Administratör group membership,
        # via the signal in accounts/signals.py) to reach the ModelAdmin's own
        # permission check directly, rather than testing the login wall again.
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])
        self.client.force_login(self.user)

        self.source = ImportSource.objects.create(name="Admin-test källa")
        self.run = ImportRun.objects.create(source=self.source)
        self.festivalpro_config = FestivalProImportSource.objects.create(
            source=self.source,
            login_url="https://example.com/login",
            export_url="https://example.com/export",
        )

    def test_import_source_delete_view_is_forbidden(self):
        response = self.client.get(
            f"/admin/imports/importsource/{self.source.pk}/delete/"
        )
        self.assertIn(response.status_code, (403, 302))
        self.assertTrue(ImportSource.objects.filter(pk=self.source.pk).exists())

    def test_import_source_cannot_be_deleted_via_bulk_action(self):
        response = self.client.post(
            "/admin/imports/importsource/",
            {
                "action": "delete_selected",
                "_selected_action": [str(self.source.pk)],
                "index": 0,
            },
        )
        self.assertNotEqual(response.status_code, 500)
        self.assertTrue(ImportSource.objects.filter(pk=self.source.pk).exists())

    def test_import_run_delete_view_is_forbidden(self):
        response = self.client.get(f"/admin/imports/importrun/{self.run.pk}/delete/")
        self.assertIn(response.status_code, (403, 302))
        self.assertTrue(ImportRun.objects.filter(pk=self.run.pk).exists())

    def test_import_run_cannot_be_deleted_via_bulk_action(self):
        response = self.client.post(
            "/admin/imports/importrun/",
            {
                "action": "delete_selected",
                "_selected_action": [str(self.run.pk)],
                "index": 0,
            },
        )
        self.assertNotEqual(response.status_code, 500)
        self.assertTrue(ImportRun.objects.filter(pk=self.run.pk).exists())

    def test_festivalpro_config_delete_view_is_forbidden(self):
        """The permission this class exists to close: ``FestivalProImportSource``
        doesn't share a codename prefix with ``ImportSource``/``ImportRun``, so
        it was missed on the first pass of decision 6. Same object graph, same
        act — destroying a source's own connection config."""
        response = self.client.get(
            f"/admin/imports/festivalproimportsource/{self.festivalpro_config.pk}/delete/"
        )
        self.assertIn(response.status_code, (403, 302))
        self.assertTrue(
            FestivalProImportSource.objects.filter(
                pk=self.festivalpro_config.pk
            ).exists()
        )

    def test_festivalpro_config_cannot_be_deleted_via_bulk_action(self):
        response = self.client.post(
            "/admin/imports/festivalproimportsource/",
            {
                "action": "delete_selected",
                "_selected_action": [str(self.festivalpro_config.pk)],
                "index": 0,
            },
        )
        self.assertNotEqual(response.status_code, 500)
        self.assertTrue(
            FestivalProImportSource.objects.filter(
                pk=self.festivalpro_config.pk
            ).exists()
        )

    def test_import_source_can_still_be_changed(self):
        """The negative-only version of this test class would pass just as
        well if the whole import admin were broken; this is the matching
        positive — Koordinator (via ``is_staff``) still holds ``change_*``."""
        response = self.client.get(
            f"/admin/imports/importsource/{self.source.pk}/change/"
        )
        self.assertEqual(response.status_code, 200)
