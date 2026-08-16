"""Revoke the three import-domain ``delete_*`` permissions from Koordinator.

Decision 6 of the roles review: a Koordinator keeps everything needed to
configure and run an import, but not to delete an import source, an import
run, or a FestivalPro source's own connection config — that's a
wider-blast-radius act than the owner meant to grant, and all three only
ended up in the Koordinator set out of necessity during the roles work
(accounts/0003), not by decision.

``delete_festivalproimportsource`` joined this migration one review pass
after the other two. ``FestivalProImportSource`` is a satellite one-to-one
config row (login/export URL, field mappings) hanging off ``ImportSource``
rather than a subclass of it, so a codename sweep for "the import delete
permissions" that pattern-matched on ``ImportSource``/``ImportRun`` walked
straight past it — same object graph, same act, different model name. See
``accounts/roles.py`` for the fuller reasoning.

Editing ``accounts/roles.py`` alone only changes what a *fresh* database gets.
Every environment that already ran 0003 has a Koordinator group holding these
three permissions right now, and a group's permissions are rows the seed
migration only ever adds to (see 0003's own docstring: create-if-absent,
never sync) — nothing revokes a permission after the fact unless a migration
says so explicitly. Hence this one.

**Reversible**, symmetrically with 0003's own reasoning: forward removes the
three permissions from Koordinator if it holds them; backward re-adds them if
the group still exists and doesn't already hold them. Both directions are
idempotent and a no-op if the Koordinator group has been deleted or renamed
out from under them (an organisation's own edit wins, same as 0003) — this
migration only ever touches a group literally named "Koordinator", never
recreates one.

The three codenames are written out here rather than read from
``accounts.roles.ROLE_PERMISSIONS[COORDINATOR]``, because after this change
that set no longer contains them — there is nothing left to read forwards,
and reading them from the *old* roles.py isn't possible since migrations
don't keep historical snapshots of plain Python modules the way they do of
models. Literal codenames are also what 0003 itself falls back to when a
permission row can't be found, so this isn't a new pattern.
"""

from django.db import migrations

REVOKED_PERMISSIONS = [
    ("imports", "delete_importsource"),
    ("imports", "delete_importrun"),
    ("imports", "delete_festivalproimportsource"),
]

GROUP_NAME = "Koordinator"


def _koordinator_permissions(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    db = schema_editor.connection.alias

    group = Group.objects.using(db).filter(name=GROUP_NAME).first()
    if group is None:
        # Renamed or removed by the organisation; nothing to revoke or restore.
        return None, None

    permissions = []
    for app_label, codename in REVOKED_PERMISSIONS:
        permission = (
            Permission.objects.using(db)
            .filter(content_type__app_label=app_label, codename=codename)
            .first()
        )
        if permission is not None:
            permissions.append(permission)
        # A permission row that doesn't exist (deleted model, fresh install
        # order quirk) is skipped rather than fatal, same tolerance as 0003.

    return group, permissions


def forwards(apps, schema_editor):
    group, permissions = _koordinator_permissions(apps, schema_editor)
    if group is None:
        return
    group.permissions.remove(*permissions)


def backwards(apps, schema_editor):
    group, permissions = _koordinator_permissions(apps, schema_editor)
    if group is None:
        return
    group.permissions.add(*permissions)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_seed_roles"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
