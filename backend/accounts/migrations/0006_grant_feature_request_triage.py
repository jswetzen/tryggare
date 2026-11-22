"""Give existing Koordinator and Administratör groups the feature request triage permissions.

Owner decision 2026-11-22: coordinators may triage feature requests in Django
admin, not only superusers. ``roles.py`` now lists the three codenames for
Koordinator (Administratör is a superset of it). 0003 is create-if-absent and
never syncs, so an environment that already seeded its groups would not get
them from an edit to ``roles.py`` alone. Same reasoning as 0005.

Groups are matched by literal name and only ever *added to*. The codenames are
written out here rather than read from ``roles.py``, so this migration keeps
meaning what it meant when it was written. ``accounts/tests_roles.py`` asserts
this list and ``roles.py`` agree.

Permission rows for ``feature_requests`` are materialised first, because
``create_permissions`` normally runs from ``post_migrate``, after this migration.

Reversible: backwards removes the three permissions from those groups.
"""

from django.db import migrations

GROUP_NAMES = ("Koordinator", "Administratör")

TRIAGE_PERMISSIONS = (
    ("feature_requests", "view_featurerequest"),
    ("feature_requests", "change_featurerequest"),
    ("feature_requests", "view_featurerequestcomment"),
)


def _ensure_permission_rows(schema_editor):
    from django.apps import apps as global_apps
    from django.contrib.auth.management import create_permissions

    create_permissions(
        global_apps.get_app_config("feature_requests"),
        verbosity=0,
        using=schema_editor.connection.alias,
    )


def _permissions(apps, db):
    Permission = apps.get_model("auth", "Permission")
    found = []
    for app_label, codename in TRIAGE_PERMISSIONS:
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
        ("accounts", "0005_grant_door_ticket_permissions"),
        ("feature_requests", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
