"""The Django test runner, with the seeded role groups guaranteed present.

``pytest tests/unit/`` gets this from a session-scoped ``django_db_setup``
fixture in ``tests/unit/conftest.py``. ``manage.py test`` shares no fixtures
with pytest, so it needs its own hook — and it needs one for the same reason:
both runners point at a database literally named ``test_checkins``, and
``--reuse-db`` / ``--keepdb`` mean that database routinely outlives the run
that created it. Once any ``TransactionTestCase`` has flushed the role groups
away, every later run inherits a database where ``accounts.roles.grant``
raises ``Group.DoesNotExist``.

Hooking ``setup_databases`` rather than ``setup_test_environment`` is
deliberate: the groups have to be written after the database exists and its
migrations have run, and once per run rather than once per test.
"""

from django.test.runner import DiscoverRunner


class RoleSeedingTestRunner(DiscoverRunner):
    def setup_databases(self, **kwargs):
        old_config = super().setup_databases(**kwargs)
        from tests.support import ensure_role_groups

        ensure_role_groups()
        return old_config
