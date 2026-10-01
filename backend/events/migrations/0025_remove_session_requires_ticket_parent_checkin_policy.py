"""Drop the deprecated ``Session.requires_ticket`` and
``Session.parent_checkin_policy`` columns.

0022 folded them into ``Session.ticket_rule`` + ``Session.adults_not_checked_in``
(0021 added those fields, 0022 carried the data over); since then nothing has
read the old columns. Migrations apply in dependency order (0021 -> 0022 ->
0023 -> 0024 -> this one), so in any database that reaches 0025 the data
migration has already run: the values are carried over before the columns go.

DEPLOY ORDER. Migrate before the new frontend/backend code is served: the
serializer no longer returns ``requires_ticket`` /
``effective_parent_checkin_policy``, and the new frontend does not read them.

RELEASE NOTE, LOSSY CASE. 0022 mapped (requires_ticket=False +
ticket_required) -- adults needed a ticket, children were free -- to rule
``all`` (children now need a ticket too), which is stricter for those
children, and printed/logged every session it touched (logger
``events.migrations``). This migration destroys the columns that could have
been used to re-derive that list, so the release note must name those sessions.

REVERSE. Re-adds both columns with their old defaults (``requires_ticket``
False, ``parent_checkin_policy`` blank, i.e. "inherit the event default"), so
migrating backwards does not crash. The VALUES are not restored here; walking
back further through 0022 re-derives them from ``ticket_rule`` /
``adults_not_checked_in`` (its reverse writes an explicit policy on every
session), so a full reverse round-trips the effective behaviour.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("events", "0024_ticket_door_grant_permissions"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="session",
            name="requires_ticket",
        ),
        migrations.RemoveField(
            model_name="session",
            name="parent_checkin_policy",
        ),
    ]
