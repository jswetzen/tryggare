"""
Shared test support that isn't specific to one runner.

``manage.py test`` (unittest ``TestCase``, discovered per-app — e.g.
``registrations/tests_registration_changelist.py``) and ``pytest tests/unit/``
are two separate runners that do not share fixtures or conftest.py. Anything
that both need has to be duplicated in a form each runner understands: a
pytest fixture for the pytest side (``tests/unit/conftest.py``), and this
mixin for unittest-style ``TestCase`` classes.
"""

from django.test import override_settings

#: The project's real STORAGES (config/settings/base.py) points "staticfiles"
#: at whitenoise's CompressedManifestStaticFilesStorage, which resolves
#: {% static %} through a staticfiles.json manifest built by `collectstatic`
#: — a step the test environment never runs. Any test that renders a full
#: admin template (index, login, changelist) pulls in {% static %} for
#: admin/css/base.css etc. and raises ValueError: "Missing staticfiles
#: manifest entry". Swapping in plain StaticFilesStorage only changes *how*
#: static URLs are resolved (no hashing/manifest lookup) — it doesn't touch
#: anything a test asserts on.
NON_MANIFEST_STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}


def ensure_role_groups():
    """Recreate the three seeded role groups in the *test* database.

    ``accounts/migrations/0003_seed_roles`` creates Volontär / Koordinator /
    Administratör, but a data migration's rows do not survive the ``flush()``
    that ``TransactionTestCase`` and ``LiveServerTestCase`` perform between
    tests — and a flush does not replay data migrations, so nothing puts them
    back. With ``--reuse-db`` in ``pytest.ini`` and ``--keepdb`` on the Django
    side, that damage is then carried forward into every later run against the
    same physical ``test_checkins`` database. Symptom: a pile of
    ``Group.DoesNotExist`` errors in suites that call ``roles.grant``, with no
    code change to explain them.

    Unlike migration 0003 — which is deliberately create-if-absent so a
    customer's own edits to a group are never stomped — this **always** sets
    the permission set. The reasoning that protects customer customisation does
    not apply to a scratch database, and a group left half-populated by a
    partial flush would otherwise produce a subtler version of the same
    failure. Permissions are read from ``accounts.roles``, the same source the
    migration uses, so the tests cannot drift from the real definitions.

    Idempotent; safe to call on an intact database.
    """
    from django.contrib.auth.models import Group, Permission

    from accounts.roles import ROLE_NAMES, ROLE_PERMISSIONS, split_permission

    for name in ROLE_NAMES:
        group, _ = Group.objects.get_or_create(name=name)
        found = []
        for label in sorted(ROLE_PERMISSIONS[name]):
            app_label, codename = split_permission(label)
            permission = Permission.objects.filter(
                content_type__app_label=app_label, codename=codename
            ).first()
            if permission is not None:
                found.append(permission)
        group.permissions.set(found)


class NonManifestStaticfilesTestCase:
    """Mixin for unittest ``TestCase`` subclasses that render admin templates.

    Usage: ``class MyTests(NonManifestStaticfilesTestCase, TestCase): ...``
    (mixin first, so its setUpClass/tearDownClass participate in the MRO
    alongside TestCase's).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._non_manifest_staticfiles = override_settings(
            STORAGES=NON_MANIFEST_STORAGES
        )
        cls._non_manifest_staticfiles.enable()

    @classmethod
    def tearDownClass(cls):
        cls._non_manifest_staticfiles.disable()
        super().tearDownClass()
