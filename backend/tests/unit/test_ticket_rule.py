"""
The merged, server-enforced ticket rule (owner decision 2026-10-01).

``Session.ticket_rule`` (open / children / all, blank inherits
``Event.ticket_rule_default``) plus ``Session.adults_not_checked_in`` replaced the
old ``requires_ticket`` (children only, UI-enforced) and
``parent_checkin_policy`` (adults only), whose columns migration 0025 dropped. ``Attendee.has_ticket_for(session)``
is the single helper the gate asks.

Every row of the matrix is asserted through BOTH entry points, because they are
two separate code paths that must agree: the ``check_in`` view action and the
generic ``POST /api/checkins/`` (``CheckInRecordSerializer.validate``).

Also covered: migration 0022 (six combinations, event-default inheritance,
forward-then-reverse on EFFECTIVE behaviour), migration 0025 (the columns are
dropped and its reverse re-adds them), the serializer no longer exposing the
old derived fields, and the check-out PATCH that must never be refused.
"""

import importlib
import uuid
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.roles import COORDINATOR, VOLUNTEER, grant
from checkins.models import CheckInRecord
from events.models import Event, EventTicket, Session, SessionTicket
from families.models import Child, Family, Parent
from registrations.models import Registration
from registrations.tokens import generate_verification_token, hash_token

Rule = Session.TicketRule
Status = Registration.Status

CHECKIN_URL = reverse("checkin-check-in")
CHECKIN_LIST_URL = reverse("checkin-list")

OPEN, CHILDREN, ALL = Rule.OPEN, Rule.CHILDREN, Rule.ALL


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _event(name="E", **extra):
    today = timezone.now().date()
    return Event.objects.create(name=name, start_date=today, end_date=today, **extra)


def _session(event, rule="", adults_not_checked_in=False, name="S"):
    now = timezone.now()
    return Session.objects.create(
        name=name,
        event=event,
        start_time=now,
        end_time=now + timedelta(hours=2),
        is_active=True,
        ticket_rule=rule,
        adults_not_checked_in=adults_not_checked_in,
    )


def _user(role=VOLUNTEER, name=None):
    name = name or f"door-{uuid.uuid4().hex[:8]}"
    user = get_user_model().objects.create_user(username=name)
    return grant(user, role)


def _client(user=None):
    client = APIClient()
    client.user = user or _user()
    client.force_authenticate(user=client.user)
    return client


def _child(name="Kid"):
    return Child.objects.create(
        first_name=name, last_name="C", family=Family.objects.create(last_name="F")
    )


def _adult(name="Adult"):
    return Parent.objects.create(
        first_name=name, last_name="P", family=Family.objects.create(last_name="F")
    )


def _guardian(event, status=Status.CONFIRMED):
    adult = _adult("Guardian")
    registration = Registration.objects.create(
        event=event,
        family=adult.family,
        contact_email="g@example.com",
        verification_token_hash=hash_token(generate_verification_token()),
        status=status,
    )
    registration.guardian_only_parents.add(adult)
    return adult


def _via_view(client, attendee, session):
    return client.post(
        CHECKIN_URL,
        {"child": str(attendee.id), "session": str(session.id)},
        format="json",
    ).status_code


def _via_serializer(client, attendee, session):
    return client.post(
        CHECKIN_LIST_URL,
        {
            "child": str(attendee.id),
            "session": str(session.id),
            "check_in_staff": client.user.pk,
        },
        format="json",
    ).status_code


ENTRY_POINTS = pytest.mark.parametrize(
    "enter", [_via_view, _via_serializer], ids=["view", "serializer"]
)
RULES = pytest.mark.parametrize("rule", [OPEN, CHILDREN, ALL])


def _ok(status_code):
    return status_code == 201


# ---------------------------------------------------------------------------
# The matrix
# ---------------------------------------------------------------------------

# who -> (open, children, all) with "adults_not_checked_in" OFF.
MATRIX = {
    "child_with_ticket": (True, True, True),
    "child_without_ticket": (True, False, False),
    "ticketed_adult": (True, True, True),
    "ticketless_adult": (True, True, False),
    "guardian_only_confirmed": (True, True, True),
    # An unconfirmed registration is refused by the registration gate in every
    # column, whatever the rule says.
    "guardian_only_unconfirmed": (False, False, False),
}
ADULTS = {
    "ticketed_adult",
    "ticketless_adult",
    "guardian_only_confirmed",
    "guardian_only_unconfirmed",
}


def _actor(who, event, session):
    if who == "child_with_ticket":
        child = _child()
        SessionTicket.objects.create(attendee=child, session=session)
        return child
    if who == "child_without_ticket":
        return _child()
    if who == "ticketed_adult":
        adult = _adult()
        EventTicket.objects.create(attendee=adult, event=event)
        return adult
    if who == "ticketless_adult":
        return _adult()
    if who == "guardian_only_confirmed":
        return _guardian(event, Status.CONFIRMED)
    if who == "guardian_only_unconfirmed":
        return _guardian(event, Status.PENDING_VERIFICATION)
    raise AssertionError(who)


@pytest.mark.django_db
class TestMatrix:
    @ENTRY_POINTS
    @pytest.mark.parametrize("who", list(MATRIX))
    @pytest.mark.parametrize("rule_index,rule", list(enumerate([OPEN, CHILDREN, ALL])))
    def test_checkbox_off(self, enter, who, rule_index, rule):
        event = _event()
        session = _session(event, rule)
        attendee = _actor(who, event, session)

        status_code = enter(_client(), attendee, session)

        expected = MATRIX[who][rule_index]
        assert _ok(status_code) == expected, (who, rule, status_code)
        assert (
            CheckInRecord.objects.filter(attendee_id=attendee.id).exists() == expected
        )

    @ENTRY_POINTS
    @pytest.mark.parametrize("who", list(MATRIX))
    @pytest.mark.parametrize("rule_index,rule", list(enumerate([OPEN, CHILDREN, ALL])))
    def test_checkbox_on(self, enter, who, rule_index, rule):
        """Every adult is refused in every column (guardians included); the
        children follow the same table as with the checkbox off."""
        event = _event()
        session = _session(event, rule, adults_not_checked_in=True)
        attendee = _actor(who, event, session)

        status_code = enter(_client(), attendee, session)

        expected = False if who in ADULTS else MATRIX[who][rule_index]
        assert _ok(status_code) == expected, (who, rule, status_code)

    @ENTRY_POINTS
    def test_blank_session_rule_inherits_the_event_default(self, enter):
        event = _event(ticket_rule_default=CHILDREN)
        session = _session(event, "")
        assert session.effective_ticket_rule == CHILDREN
        assert not _ok(enter(_client(), _child(), session))

    @ENTRY_POINTS
    def test_explicit_session_rule_beats_the_event_default(self, enter):
        event = _event(ticket_rule_default=ALL)
        session = _session(event, OPEN)
        assert _ok(enter(_client(), _child(), session))

    @ENTRY_POINTS
    def test_child_refusal_says_so(self, enter):
        event = _event()
        session = _session(event, CHILDREN)
        client = _client()
        response = client.post(
            CHECKIN_URL if enter is _via_view else CHECKIN_LIST_URL,
            {
                "child": str(_child().id),
                "session": str(session.id),
                "check_in_staff": client.user.pk,
            },
            format="json",
        )
        assert response.status_code == 400
        assert "does not have a ticket for this session" in str(response.data)


# ---------------------------------------------------------------------------
# What counts as "a ticket for this session"
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestHasTicketFor:
    def test_event_ticket_for_this_event_counts(self):
        event = _event()
        session = _session(event)
        child = _child()
        EventTicket.objects.create(attendee=child, event=event)
        assert child.has_ticket_for(session)

    def test_session_ticket_for_this_session_counts(self):
        session = _session(_event())
        child = _child()
        SessionTicket.objects.create(attendee=child, session=session)
        assert child.has_ticket_for(session)

    def test_no_ticket_at_all(self):
        assert not _child().has_ticket_for(_session(_event()))

    @ENTRY_POINTS
    @pytest.mark.parametrize("who", ["child", "adult"])
    def test_a_ticket_for_another_event_never_satisfies(self, enter, who):
        event = _event("This")
        other = _event("Other")
        session = _session(event, ALL)
        attendee = _child() if who == "child" else _adult()
        EventTicket.objects.create(attendee=attendee, event=other)
        SessionTicket.objects.create(
            attendee=attendee, session=_session(other, ALL, name="Elsewhere")
        )

        assert attendee.has_ticket is True  # the unscoped helper is fooled...
        assert not attendee.has_ticket_for(session)  # ...the scoped one is not.
        assert not _ok(enter(_client(), attendee, session))

    @ENTRY_POINTS
    @pytest.mark.parametrize("who", ["child", "adult"])
    def test_a_ticket_for_a_sibling_session_never_satisfies(self, enter, who):
        event = _event()
        session = _session(event, ALL, name="Wanted")
        sibling = _session(event, ALL, name="Sibling")
        attendee = _child() if who == "child" else _adult()
        SessionTicket.objects.create(attendee=attendee, session=sibling)

        assert not attendee.has_ticket_for(session)
        assert not _ok(enter(_client(), attendee, session))
        assert _ok(enter(_client(), attendee, sibling))


# ---------------------------------------------------------------------------
# Check-out must never be refused; door-assign must keep working
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCheckoutAndDoorAssign:
    def _checked_in_child_then_ticket_removed(self):
        event = _event()
        session = _session(event, CHILDREN)
        child = _child()
        ticket = SessionTicket.objects.create(attendee=child, session=session)
        user = _user()
        client = _client(user)
        assert _via_view(client, child, session) == 201
        ticket.delete()
        record = CheckInRecord.objects.get(attendee_id=child.id)
        return client, user, record, session

    def test_checkout_patch_is_not_blocked_when_the_ticket_was_removed(self):
        client, user, record, _ = self._checked_in_child_then_ticket_removed()

        response = client.patch(
            reverse("checkin-detail", args=[record.id]),
            {"check_out_time": timezone.now().isoformat(), "check_out_staff": user.pk},
            format="json",
        )

        assert response.status_code == 200, response.data
        record.refresh_from_db()
        assert record.check_out_time is not None

    def test_check_out_action_is_not_blocked_either(self):
        client, _, record, _ = self._checked_in_child_then_ticket_removed()
        response = client.post(reverse("checkin-check-out", args=[record.id]), {})
        assert response.status_code == 200, response.data

    def test_undo_checkout_reopens_without_the_gate(self):
        """Accepted trade-off, documented in the view: undo_checkout reopens a
        record the door legitimately created minutes ago and does not re-run
        the ticket gate."""
        client, _, record, _ = self._checked_in_child_then_ticket_removed()
        client.post(reverse("checkin-check-out", args=[record.id]), {})
        response = client.post(reverse("checkin-undo-checkout", args=[record.id]), {})
        assert response.status_code == 200, response.data

    def test_patch_that_moves_the_record_to_a_ticketed_session_is_gated(self):
        """On a PATCH, `attendee`/`session` may be absent from validated data;
        when `session` IS present and differs from the instance the gate runs
        against the instance's attendee."""
        client, _, record, session = self._checked_in_child_then_ticket_removed()
        other = _session(session.event, ALL, name="Other")

        response = client.patch(
            reverse("checkin-detail", args=[record.id]),
            {"session": str(other.id)},
            format="json",
        )

        assert response.status_code == 400
        assert "ticket" in str(response.data).lower()

    def test_patch_that_leaves_the_session_alone_is_not_gated(self):
        client, _, record, session = self._checked_in_child_then_ticket_removed()
        response = client.patch(
            reverse("checkin-detail", args=[record.id]),
            {"session": str(session.id)},
            format="json",
        )
        assert response.status_code == 200, response.data

    def test_assigning_a_ticket_at_the_door_then_checking_in_succeeds(self):
        """The check-in UI posts /event-tickets/ (or /session-tickets/) and
        then check_in. Staff-created tickets carry registration=None, so the
        gate passes as soon as the ticket exists."""
        event = _event()
        session = _session(event, CHILDREN)
        child = _child()
        coordinator = _client(_user(COORDINATOR, "coord"))

        assert _via_view(coordinator, child, session) == 400

        made = coordinator.post(
            reverse("event-ticket-list"),
            {"child": str(child.id), "event": str(event.id)},
            format="json",
        )
        assert made.status_code == 201, made.data
        assert _via_view(coordinator, child, session) == 201

    def test_assigning_a_session_ticket_at_the_door_then_checking_in_succeeds(self):
        event = _event()
        session = _session(event, ALL)
        adult = _adult()
        coordinator = _client(_user(COORDINATOR, "coord2"))

        assert _via_view(coordinator, adult, session) == 400
        made = coordinator.post(
            reverse("session-ticket-list"),
            {"child": str(adult.id), "session": str(session.id)},
            format="json",
        )
        assert made.status_code == 201, made.data
        assert _via_view(coordinator, adult, session) == 201


# ---------------------------------------------------------------------------
# Session serializer: new fields, derived read-only compatibility fields
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSessionSerializer:
    def _get(self, session):
        return _client().get(reverse("session-detail", args=[session.id])).data

    @pytest.mark.parametrize(
        "rule,adults_off",
        [
            (OPEN, False),
            (CHILDREN, False),
            (ALL, False),
            (OPEN, True),
            (CHILDREN, True),
            (ALL, True),
        ],
    )
    def test_exposes_the_rule_and_the_adults_flag(self, rule, adults_off):
        session = _session(_event(), rule, adults_not_checked_in=adults_off)
        data = self._get(session)
        assert data["ticket_rule"] == rule
        assert data["effective_ticket_rule"] == rule
        assert data["adults_not_checked_in"] is adults_off
        # The derived legacy fields are gone from the payload.
        assert "requires_ticket" not in data
        assert "effective_parent_checkin_policy" not in data

    def test_effective_rule_resolves_the_event_default(self):
        session = _session(_event(ticket_rule_default=ALL), "")
        data = self._get(session)
        assert data["ticket_rule"] == ""
        assert data["effective_ticket_rule"] == ALL

    def test_legacy_fields_in_a_request_are_ignored(self):
        session = _session(_event(), OPEN)
        coordinator = _client(_user(COORDINATOR, "coord3"))
        response = coordinator.patch(
            reverse("session-detail", args=[session.id]),
            {"requires_ticket": True, "parent_checkin_policy": "disabled"},
            format="json",
        )
        assert response.status_code == 200
        session.refresh_from_db()
        assert session.effective_ticket_rule == OPEN
        assert session.adults_not_checked_in is False

    def test_filter_by_ticket_rule(self):
        event = _event()
        _session(event, CHILDREN, name="a")
        _session(event, OPEN, name="b")
        response = _client().get(reverse("session-list"), {"ticket_rule": "children"})
        rows = (
            response.data["results"]
            if isinstance(response.data, dict)
            else response.data
        )
        names = [row["name"] for row in rows]
        assert names == ["a"]


# ---------------------------------------------------------------------------
# Migrations 0022 (fold) and 0025 (drop the old columns)
#
# The old columns no longer exist on the real models, so these tests walk the
# real schema BACK to 0024 (which is also the proof that 0025's reverse
# re-adds both columns), build rows through the historical model registry
# for that state, run 0022's forward/reverse against it, and migrate forward
# to the leaf again afterwards. Needs a transactional DB: DDL plus a flush.
# ---------------------------------------------------------------------------

migration = importlib.import_module(
    "events.migrations.0022_fold_ticket_controls_into_ticket_rule"
)

BEFORE_DROP = ("events", "0024_ticket_door_grant_permissions")


def _session_columns():
    with connection.cursor() as cursor:
        return {
            column.name
            for column in connection.introspection.get_table_description(
                cursor, Session._meta.db_table
            )
        }


@pytest.fixture
def legacy_apps():
    """The model registry as it was at 0024: the old columns exist."""
    executor = MigrationExecutor(connection)
    executor.migrate([BEFORE_DROP])
    try:
        yield MigrationExecutor(connection).loader.project_state([BEFORE_DROP]).apps
    finally:
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())


def _old_event(apps, name="E", **extra):
    today = timezone.now().date()
    return apps.get_model("events", "Event").objects.create(
        name=name, start_date=today, end_date=today, **extra
    )


def _old_session(apps, event, requires_ticket, policy, name="old"):
    """A session as the OLD columns describe it (the new ones left at their
    defaults, as they are when 0022 starts)."""
    now = timezone.now()
    return apps.get_model("events", "Session").objects.create(
        name=name,
        event=event,
        start_time=now,
        end_time=now + timedelta(hours=1),
        requires_ticket=requires_ticket,
        parent_checkin_policy=policy,
    )


def _reload(apps, row):
    manager = type(row).objects
    if hasattr(row, "event_id"):  # a Session: resolve its event default too
        manager = manager.select_related("event")
    return manager.get(pk=row.pk)


def _effective_ticket_rule(session):
    return session.ticket_rule or session.event.ticket_rule_default


def _effective_adult_policy(session):
    return session.parent_checkin_policy or session.event.parent_checkin_policy_default


# (requires_ticket, effective policy) -> (rule, adults_not_checked_in)
SIX = [
    (False, "open", "open", False),
    (True, "open", "children", False),
    (True, "ticket_required", "all", False),
    (False, "ticket_required", "all", False),  # LOSSY
    (False, "disabled", "open", True),
    (True, "disabled", "children", True),
]


@pytest.mark.django_db(transaction=True)
class TestMigration0025:
    def test_the_old_columns_are_gone_at_the_leaf(self):
        columns = _session_columns()
        assert "requires_ticket" not in columns
        assert "parent_checkin_policy" not in columns
        assert {"ticket_rule", "adults_not_checked_in"} <= columns

    def test_reverse_re_adds_both_columns(self, legacy_apps):
        columns = _session_columns()
        assert {"requires_ticket", "parent_checkin_policy"} <= columns
        # Rows can be created with the old defaults, so a backwards migrate
        # leaves a usable table.
        session = _old_session(legacy_apps, _old_event(legacy_apps), False, "")
        assert session.requires_ticket is False
        assert session.parent_checkin_policy == ""

    def test_forward_migrates_cleanly_with_rows_present(self, legacy_apps):
        _old_session(legacy_apps, _old_event(legacy_apps), True, "disabled")
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        assert "requires_ticket" not in _session_columns()
        assert Session.objects.count() == 1


@pytest.mark.django_db(transaction=True)
class TestMigration0022:
    def _forward(self, apps):
        migration.forward(apps, None)

    def _reverse(self, apps):
        migration.reverse(apps, None)

    @pytest.mark.parametrize("rc,policy,rule,adults_off", SIX)
    def test_each_combination_maps_as_decided(
        self, legacy_apps, rc, policy, rule, adults_off
    ):
        session = _old_session(legacy_apps, _old_event(legacy_apps), rc, policy)
        self._forward(legacy_apps)
        session = _reload(legacy_apps, session)
        assert _effective_ticket_rule(session) == rule
        assert session.adults_not_checked_in is adults_off

    def test_a_rule_equal_to_the_event_default_is_left_blank_else_explicit(
        self, legacy_apps
    ):
        event = _old_event(legacy_apps)  # old default policy: open -> new default: open
        same = _old_session(legacy_apps, event, False, "open", "same")
        differs = _old_session(legacy_apps, event, True, "open", "differs")
        self._forward(legacy_apps)
        event = _reload(legacy_apps, event)
        assert event.ticket_rule_default == "open"
        assert _reload(legacy_apps, same).ticket_rule == ""
        assert _reload(legacy_apps, differs).ticket_rule == "children"

    @pytest.mark.parametrize(
        "old_default,new_default",
        [("open", "open"), ("ticket_required", "all"), ("disabled", "open")],
    )
    def test_event_default_mapping(self, legacy_apps, old_default, new_default):
        event = _old_event(legacy_apps, parent_checkin_policy_default=old_default)
        self._forward(legacy_apps)
        assert _reload(legacy_apps, event).ticket_rule_default == new_default

    def test_sessions_inheriting_the_event_default_policy(self, legacy_apps):
        """Blank policy resolves through the event's OLD default before mapping."""
        ticketed = _old_event(
            legacy_apps, "T", parent_checkin_policy_default="ticket_required"
        )
        disabled = _old_event(
            legacy_apps, "D", parent_checkin_policy_default="disabled"
        )
        t_free = _old_session(legacy_apps, ticketed, False, "", "t_free")  # LOSSY
        t_children = _old_session(legacy_apps, ticketed, True, "", "t_children")
        d_free = _old_session(legacy_apps, disabled, False, "", "d_free")
        d_children = _old_session(legacy_apps, disabled, True, "", "d_children")
        self._forward(legacy_apps)
        t_free, t_children, d_free, d_children = (
            _reload(legacy_apps, s) for s in (t_free, t_children, d_free, d_children)
        )

        assert _effective_ticket_rule(t_free) == "all"
        assert t_free.ticket_rule == ""  # equals the event's new default
        assert _effective_ticket_rule(t_children) == "all"
        assert _effective_ticket_rule(d_free) == "open"
        assert d_free.adults_not_checked_in is True
        assert _effective_ticket_rule(d_children) == "children"
        assert d_children.ticket_rule == "children"  # differs from "open"
        assert d_children.adults_not_checked_in is True

    def test_the_lossy_case_is_printed_and_logged(self, legacy_apps, capsys, caplog):
        event = _old_event(legacy_apps, "Lossy Event")
        _old_session(legacy_apps, event, False, "ticket_required", "Lossy Session")
        _old_session(legacy_apps, event, True, "ticket_required", "Fine Session")
        with caplog.at_level("WARNING"):
            self._forward(legacy_apps)
        printed = capsys.readouterr().out
        assert "Lossy Event" in printed and "Lossy Session" in printed
        assert "Fine Session" not in printed
        logged = caplog.text
        assert "Lossy Session" in logged and "Lossy Event" in logged

    def test_the_old_columns_are_left_untouched_by_the_forward_step(self, legacy_apps):
        session = _old_session(legacy_apps, _old_event(legacy_apps), True, "disabled")
        self._forward(legacy_apps)
        session = _reload(legacy_apps, session)
        assert session.requires_ticket is True
        assert session.parent_checkin_policy == "disabled"

    def test_forward_then_reverse_preserves_effective_behaviour(self, legacy_apps):
        """Effective behaviour, not field equality: (F, ticket_required)
        comes back as (T, ticket_required) and an event default of disabled
        comes back as open plus an explicit disabled per session."""
        ticketed = _old_event(
            legacy_apps, "T", parent_checkin_policy_default="ticket_required"
        )
        disabled = _old_event(
            legacy_apps, "D", parent_checkin_policy_default="disabled"
        )
        plain = _old_event(legacy_apps, "P")
        sessions = []
        for event in (ticketed, disabled, plain):
            for rc in (False, True):
                for policy in ("", "open", "disabled", "ticket_required"):
                    sessions.append(
                        _old_session(
                            legacy_apps,
                            event,
                            rc,
                            policy,
                            f"{event.name}-{rc}-{policy}",
                        )
                    )

        def old_behaviour(session):
            # What the OLD code enforced for (children, adults).
            return session.requires_ticket, _effective_adult_policy(session)

        before = {s.pk: old_behaviour(_reload(legacy_apps, s)) for s in sessions}

        self._forward(legacy_apps)
        self._reverse(legacy_apps)

        for session in sessions:
            session = _reload(legacy_apps, session)
            old_children, old_adults = before[session.pk]
            children, adults = old_behaviour(session)
            # Children: needed a ticket before -> still do. The only change is
            # the chosen LOSSY one: adults-with-ticket + free children now also
            # makes children need a ticket.
            if old_adults == "ticket_required":
                assert children is True
            else:
                assert children == old_children
            assert adults == old_adults
            # The reverse writes an explicit policy on every session.
            assert session.parent_checkin_policy in (
                "open",
                "disabled",
                "ticket_required",
            )

    def test_reverse_of_a_disabled_event_default_is_open_plus_explicit_disabled(
        self, legacy_apps
    ):
        event = _old_event(legacy_apps, "D", parent_checkin_policy_default="disabled")
        session = _old_session(legacy_apps, event, False, "")
        self._forward(legacy_apps)
        self._reverse(legacy_apps)
        event = _reload(legacy_apps, event)
        session = _reload(legacy_apps, session)
        assert event.parent_checkin_policy_default == "open"
        assert session.parent_checkin_policy == "disabled"
        assert session.requires_ticket is False

    def test_local_dev_shape_is_a_no_op_on_behaviour(self, legacy_apps):
        """The 8 sessions in the local dev DB: all (False, '', open) with an
        event default of open."""
        event = _old_event(legacy_apps)
        sessions = [
            _old_session(legacy_apps, event, False, "", f"s{i}") for i in range(8)
        ]
        self._forward(legacy_apps)
        for session in sessions:
            session = _reload(legacy_apps, session)
            assert session.ticket_rule == ""
            assert _effective_ticket_rule(session) == "open"
            assert session.adults_not_checked_in is False


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Admin: new fields editable, dead controls not shown
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAdmin:
    def _admin_client(self):
        from django.test import Client

        user = get_user_model().objects.create_superuser(
            username=f"root-{uuid.uuid4().hex[:8]}", password="x"
        )
        client = Client()
        client.force_login(user)
        return client

    def test_session_change_form_edits_the_new_fields_only(self):
        session = _session(_event(), CHILDREN)
        response = self._admin_client().get(
            reverse("admin:events_session_change", args=[session.pk])
        )
        html = response.content.decode()
        assert response.status_code == 200
        assert 'name="ticket_rule"' in html
        assert 'name="adults_not_checked_in"' in html
        assert 'name="requires_ticket"' not in html
        assert 'name="parent_checkin_policy"' not in html

    def test_event_change_form_edits_the_new_default_only(self):
        event = _event()
        response = self._admin_client().get(
            reverse("admin:events_event_change", args=[event.pk])
        )
        html = response.content.decode()
        assert response.status_code == 200
        assert 'name="ticket_rule_default"' in html
        assert 'name="parent_checkin_policy_default"' not in html

    def test_changelists_render(self):
        _session(_event(), ALL)
        client = self._admin_client()
        assert client.get(reverse("admin:events_session_changelist")).status_code == 200
        assert client.get(reverse("admin:events_event_changelist")).status_code == 200
