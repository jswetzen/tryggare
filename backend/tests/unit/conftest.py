import pytest

from tests.support import NON_MANIFEST_STORAGES


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """Guarantee the three seeded role groups (Volontär/Koordinator/
    Administratör) exist for the whole pytest session, independent of the
    physical test database's history.

    ``pytest.ini`` sets ``--reuse-db``, so ``test_checkins`` can outlive many
    separate test runs, including ``manage.py test`` runs elsewhere in the
    repo. Several suites use ``TransactionTestCase``/``LiveServerTestCase``
    (e.g. ``printing/tests/test_ws_auth.py``), which flush *all* tables
    between tests — that deletes the rows ``accounts/migrations/
    0003_seed_roles.py`` created, but flush does not replay data migrations,
    so nothing recreates them. If that kind of run is ever interrupted (an
    unscoped ``manage.py test`` hangs on Selenium and gets killed) before its
    own teardown drops the test database, the now-groupless database is what
    ``--reuse-db`` hands to the next pytest session — see the incident this
    fixture was added for, where 20 tests in tests/unit/test_parent_checkin.py
    failed with ``Group.DoesNotExist``.

    Rebuilding via a full ``migrate`` here would work but is slower and
    duplicates 0003's own idempotency; instead this reuses the exact same
    permission tables the migration reads (``accounts.roles``) so the tests
    and the real role definitions can never drift apart. get_or_create makes
    it a no-op on a database where the groups are already intact.
    """
    from django.contrib.auth.models import Group, Permission

    from accounts.roles import ROLE_NAMES, ROLE_PERMISSIONS, split_permission

    with django_db_blocker.unblock():
        for name in ROLE_NAMES:
            group, created = Group.objects.get_or_create(name=name)
            if not created:
                continue
            wanted = [
                split_permission(label) for label in sorted(ROLE_PERMISSIONS[name])
            ]
            found = []
            for app_label, codename in wanted:
                permission = Permission.objects.filter(
                    content_type__app_label=app_label, codename=codename
                ).first()
                if permission is not None:
                    found.append(permission)
            group.permissions.set(found)

    return django_db_setup


@pytest.fixture(autouse=True)
def _non_manifest_staticfiles(settings):
    """Every pytest test under tests/unit/ that renders a full admin template
    (index, login, changelist) pulls in {% static %} tags for
    admin/css/base.css etc. The project's real STORAGES (config/settings/base.py)
    uses whitenoise's CompressedManifestStaticFilesStorage, which resolves
    {% static %} through a staticfiles.json manifest built by `collectstatic`
    — a step the test environment never runs, so any manifest-backed lookup
    raises ValueError.

    Hoisted here (originally module-local to test_admin_i18n.py) so every
    admin-rendering test under tests/unit/ gets it automatically instead of
    each new test file rediscovering the same error. See tests/support.py for
    the unittest-TestCase equivalent, needed because `manage.py test` doesn't
    share this conftest.
    """
    settings.STORAGES = NON_MANIFEST_STORAGES
