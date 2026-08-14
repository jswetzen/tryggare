"""Seed the three roles (Volontär, Koordinator, Administratör) as Django Groups.

Two properties have to hold at once, and they pull in opposite directions.

**Reversible.** ``migrate accounts 0002`` must undo this cleanly.

**An organisation's own edits must survive.** A deployment that re-ran the seed
and reset each group to its canonical permission set would silently discard a
customer's customisation — and the customisation story is the whole reason
increment 0.4 kept ``auth.Group`` on the admin index. Rolling back an admin's
deliberate edit on the next deploy is worse than never seeding at all, because
it fails quietly and at a time nobody is looking.

The resolution: **create-if-absent, never sync.**

``forwards`` uses ``get_or_create`` on the group name and assigns permissions
*only to groups it actually created*. A group that already exists is left
completely alone — the migration does not add to it, does not remove from it,
and does not compare. This covers all three ways a group can already be there:
an organisation that hand-built a "Volontär" group before upgrading, a
re-application after a rollback, and any future re-seed mechanism.

``backwards`` deletes the three groups by name. That looks blunt, and the
alternative — stripping the seeded permissions but keeping the rows — was
rejected because it does not round-trip: forward would then find the group
present, take the create-if-absent path, and leave a *permissionless* group
behind. Deleting means forward→backward→forward returns to exactly the seeded
state. Reversing a migration is a developer rollback, not a customer operation,
and it is the one place where losing group membership is both expected and
recoverable by re-applying.

Two alternatives considered and rejected:

*A ``post_migrate`` signal.* This is the idiomatic way to keep seed data
present, and it is exactly the shape that re-runs on every deploy. To make it
safe it would need the same create-if-absent guard, at which point it is a
migration with extra steps and no migration record to reason about.

*A marker row / sync-only-what-we-own.* Recording which permissions the seed
granted, then reconciling on each run, would let us add a permission to a role
in a later increment without stomping customer edits. It is genuinely better —
for a product that ships role changes regularly. It also means a schema
addition (the marker), a reconciliation policy for permissions the customer
removed on purpose, and a second source of truth. For three roles that are
described as settled, create-if-absent is the honest amount of machinery.
Adding a permission to a shipped role therefore needs its own explicit,
narrowly-scoped migration; that is a real cost and it is written down here so
the next person meets it as a decision rather than a surprise.
"""

from django.db import migrations

from accounts.roles import ROLE_NAMES, ROLE_PERMISSIONS, split_permission


def _ensure_permission_rows(schema_editor):
    """Materialise ``auth.Permission`` rows before we try to read them.

    ``create_permissions`` normally runs from ``post_migrate``, i.e. *after*
    every migration in the run has finished. On a fresh database this data
    migration would therefore query an empty Permission table and seed three
    groups with nothing in them — the classic silent version of this bug, since
    it only shows up on first install and never in development where the rows
    already exist. Calling it here is idempotent (it skips codenames that are
    already present).
    """
    from django.apps import apps as global_apps
    from django.contrib.auth.management import create_permissions

    for app_config in global_apps.get_app_configs():
        if app_config.models_module is None:
            continue
        create_permissions(
            app_config, verbosity=0, using=schema_editor.connection.alias
        )


def forwards(apps, schema_editor):
    _ensure_permission_rows(schema_editor)

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    db = schema_editor.connection.alias

    for name in ROLE_NAMES:
        group, created = Group.objects.using(db).get_or_create(name=name)
        if not created:
            # Already present: an organisation's edits win over ours. See the
            # module docstring.
            continue

        wanted = [split_permission(label) for label in sorted(ROLE_PERMISSIONS[name])]
        found = []
        for app_label, codename in wanted:
            permission = (
                Permission.objects.using(db)
                .filter(content_type__app_label=app_label, codename=codename)
                .first()
            )
            if permission is not None:
                found.append(permission)
            # A permission that no longer exists is skipped rather than fatal.
            # This migration will still be replayed on fresh databases years
            # from now, and a model deleted in the meantime must not make the
            # whole install unrunnable.

        group.permissions.set(found)


def backwards(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.using(schema_editor.connection.alias).filter(
        name__in=ROLE_NAMES
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_alter_adminuser_created_at_alter_adminuser_is_active_and_more"),
        ("auth", "0012_alter_user_first_name_max_length"),
        # Every app whose permissions the roles reference, so their models (and
        # therefore their content types) exist by the time we look them up.
        ("checkins", "0008_alter_auditlog_options_alter_auditlog_action_and_more"),
        ("events", "0017_alter_ticket_options"),
        ("families", "0016_family_dsar_permissions"),
        ("imports", "0005_alter_importsource_options_and_more"),
        ("printing", "0004_alter_printer_options_alter_printjob_options_and_more"),
        ("registrations", "0006_alter_registration_created_new_family_and_more"),
        ("reports", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
