"""Fold the two overlapping per-session ticket controls into ``ticket_rule``.

Before (owner decision 2026-10-01 merges them): ``Session.requires_ticket``
(children only, enforced only by the check-in UI) and
``Session.parent_checkin_policy`` (blank inherits
``Event.parent_checkin_policy_default``; disabled / open / ticket_required;
adults only). After: one rule, ``ticket_rule`` (open / children / all), plus a
separate fact ``adults_not_checked_in``.

Mapping, with p = the *effective* adult policy (the session's own value, or the
event default when blank) and rc = ``requires_ticket``::

    (rc=F, p=open)             -> open
    (rc=T, p=open)             -> children
    (rc=T, p=ticket_required)  -> all
    (rc=F, p=ticket_required)  -> all                      LOSSY (see below)
    (rc=F, p=disabled)         -> open     + adults_not_checked_in
    (rc=T, p=disabled)         -> children + adults_not_checked_in

``Session.ticket_rule`` is left blank when it equals the event's new default,
otherwise stored explicitly (so an event default can still be changed later
without silently flipping sessions that deliberately differed). Event default:
open -> open, ticket_required -> all, disabled -> open (every session that
inherited "disabled" is given the checkbox instead).

LOSSY CASE. (rc=F, p=ticket_required) meant "adults needed a ticket, children
were free". That combination no longer exists: there is no rule under which
adults need a ticket but children do not. It becomes ``all`` (children now need
a ticket too), which is stricter for the children. This is a chosen trade-off,
not an accident. The forward step therefore prints AND logs (logger
``events.migrations``) every session and event it applied this to. The printed
list can be lost in a Portainer deploy (nobody watches the container output),
so the release note MUST name these sessions: query the log, or re-derive with
``requires_ticket = false`` and an effective ``ticket_required`` policy on the
old columns, which this increment deliberately does not drop.

The old columns stay in place and are read by nothing. Dropping them moves to
the admin increment so a rollback of this release stays cheap.

REVERSE. Resolves a blank ``ticket_rule`` through the event default and writes
an EXPLICIT ``parent_checkin_policy`` on every session: rc = rule in
(children, all); policy = disabled if the checkbox is set, else ticket_required
for ``all``, else open. So (F,ticket_required) comes back as
(T,ticket_required), and an event default of disabled comes back as an event
default of open plus an explicit "disabled" per session. EFFECTIVE behaviour
round-trips; the individual field values need not.
"""

import logging

from django.db import migrations

logger = logging.getLogger(__name__)

# Literal values, not model enums: a migration must not depend on code that
# may later change or disappear.
POLICY_OPEN = "open"
POLICY_DISABLED = "disabled"
POLICY_TICKET_REQUIRED = "ticket_required"

RULE_OPEN = "open"
RULE_CHILDREN = "children"
RULE_ALL = "all"

EVENT_DEFAULT_RULE = {
    POLICY_OPEN: RULE_OPEN,
    POLICY_TICKET_REQUIRED: RULE_ALL,
    POLICY_DISABLED: RULE_OPEN,
}


def session_rule(requires_ticket: bool, policy: str) -> tuple[str, bool, bool]:
    """Return ``(rule, adults_not_checked_in, lossy)`` for one old
    (requires_ticket, effective policy) pair."""
    if policy == POLICY_DISABLED:
        return (RULE_CHILDREN if requires_ticket else RULE_OPEN), True, False
    if policy == POLICY_TICKET_REQUIRED:
        return RULE_ALL, False, not requires_ticket
    return (RULE_CHILDREN if requires_ticket else RULE_OPEN), False, False


def forward(apps, schema_editor):
    Event = apps.get_model("events", "Event")
    Session = apps.get_model("events", "Session")

    lossy = []  # (event name, session name, session id)

    for event in Event.objects.all():
        event_policy = event.parent_checkin_policy_default or POLICY_OPEN
        new_default = EVENT_DEFAULT_RULE.get(event_policy, RULE_OPEN)

        for session in Session.objects.filter(event_id=event.pk):
            policy = session.parent_checkin_policy or event_policy
            rule, adults_off, is_lossy = session_rule(session.requires_ticket, policy)
            session.ticket_rule = "" if rule == new_default else rule
            session.adults_not_checked_in = adults_off
            session.save(update_fields=["ticket_rule", "adults_not_checked_in"])
            if is_lossy:
                lossy.append((event.name, session.name, str(session.pk)))

        event.ticket_rule_default = new_default
        event.save(update_fields=["ticket_rule_default"])

    if lossy:
        header = (
            "events.0022: %d session(s) had adults needing a ticket but children "
            "free (requires_ticket=False + ticket_required); that combination no "
            "longer exists, so children now need a ticket there too (rule 'all'):"
            % len(lossy)
        )
        lines = [
            "  event=%r session=%r id=%s" % (event_name, session_name, session_id)
            for event_name, session_name, session_id in lossy
        ]
        print("\n" + "\n".join([header, *lines]))
        logger.warning("\n".join([header, *lines]))
        for event_name in sorted({row[0] for row in lossy}):
            logger.warning("events.0022: event %r touched by the lossy case", event_name)


def reverse(apps, schema_editor):
    Event = apps.get_model("events", "Event")
    Session = apps.get_model("events", "Session")

    for event in Event.objects.all():
        for session in Session.objects.filter(event_id=event.pk):
            rule = session.ticket_rule or event.ticket_rule_default
            session.requires_ticket = rule in (RULE_CHILDREN, RULE_ALL)
            if session.adults_not_checked_in:
                session.parent_checkin_policy = POLICY_DISABLED
            elif rule == RULE_ALL:
                session.parent_checkin_policy = POLICY_TICKET_REQUIRED
            else:
                session.parent_checkin_policy = POLICY_OPEN
            session.save(update_fields=["requires_ticket", "parent_checkin_policy"])

        event.parent_checkin_policy_default = (
            POLICY_TICKET_REQUIRED
            if event.ticket_rule_default == RULE_ALL
            else POLICY_OPEN
        )
        event.save(update_fields=["parent_checkin_policy_default"])


class Migration(migrations.Migration):
    dependencies = [
        ("events", "0021_ticket_rule_fields"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
