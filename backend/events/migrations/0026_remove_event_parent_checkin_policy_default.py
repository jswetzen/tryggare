"""Drop the deprecated ``Event.parent_checkin_policy_default`` column.

Superseded by ``Event.ticket_rule_default`` (+ ``Session.adults_not_checked_in``)
in 0021/0022; nothing has read it since. Follows 0025, which dropped the
Session columns.

REVERSE. Re-adds the column with its old default (``open``). The VALUES are not
restored here; walking back through 0022 re-derives them from the new fields.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("events", "0025_remove_session_requires_ticket_parent_checkin_policy"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="event",
            name="parent_checkin_policy_default",
        ),
    ]
