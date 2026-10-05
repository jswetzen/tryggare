"""Give existing Volontär / Koordinator / Administratör groups the door ticket grant.

Owner decision 2026-10-01: a Volontär may admit a ticketless child (or adult)
at the check-in desk. The permissions are ``events.grant_eventticket_at_door``
and ``events.grant_sessionticket_at_door`` (see ``events/models.py`` and
``accounts/roles.py``); they are checked only by the ``.../grant/`` actions the
desk calls, never by Django admin or the general ticket ``POST``.

Why a migration at all: editing ``roles.py`` only changes what a *fresh*
database gets. 0003 is create-if-absent and never syncs (its docstring explains
why an organisation's own edits must survive), so every environment that has
already seeded its groups would keep a Volontär who cannot grant. As 0003 says,
adding a permission to a shipped role needs its own narrow migration; this is it.

Which groups: Volontär, and also Koordinator and Administratör, because
``roles.py`` defines those as supersets of Volontär -- leaving them out would
make a Koordinator strictly *less* able at the door than the volunteer they
supervise. Groups are matched by literal name and only ever *added to*: a group
that was renamed or deleted is left alone, and nothing is created.

The codenames are written out here (not read from ``roles.py``) for the reason
0004 gives: a migration must keep meaning what it meant when it was written.
``accounts/tests_roles.py`` asserts this list and ``roles.py`` agree.

**Permission rows must be materialised first.** ``create_permissions`` normally
runs from ``post_migrate``, *after* this migration, so on an existing database
the two new ``Permission`` rows would not exist yet when we look them up and the
migration would silently grant nothing. Same trap 0003 documents; same fix.

Reversible: backwards removes the two permissions from those groups.
"""

from django.db import migrations

GROUP_NAMES = ("Volontär", "Koordinator", "Administratör")

DOOR_PERMISSIONS = (
    ("events", "grant_eventticket_at_door"),
    ("events", "grant_sessionticket_at_door"),
)


def _ensure_permission_rows(schema_editor):
    from django.apps import apps as global_apps
    from django.contrib.auth.management import create_permissions

    create_permissions(
        global_apps.get_app_config("events"),
        verbosity=0,
        using=schema_editor.connection.alias,
    )


def _permissions(apps, db):
    Permission = apps.get_model("auth", "Permission")
    found = []
    for app_label, codename in DOOR_PERMISSIONS:
        permission = (
            Permission.objects.using(db)
            .filter(content_type__app_label=app_label, codename=codename)
            .first()
        )
        if permission is not None:
            found.append(permission)
    return found


def forwards(apps, schema_editor):
    _ensure_permission_rows(schema_editor)
    db = schema_editor.connection.alias
    Group = apps.get_model("auth", "Group")
    permissions = _permissions(apps, db)
    for group in Group.objects.using(db).filter(name__in=GROUP_NAMES):
        group.permissions.add(*permissions)


def backwards(apps, schema_editor):
    db = schema_editor.connection.alias
    Group = apps.get_model("auth", "Group")
    permissions = _permissions(apps, db)
    for group in Group.objects.using(db).filter(name__in=GROUP_NAMES):
        group.permissions.remove(*permissions)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_revoke_koordinator_import_delete"),
        ("events", "0024_ticket_door_grant_permissions"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
