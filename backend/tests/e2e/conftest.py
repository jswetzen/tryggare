"""
Pytest configuration for E2E tests.

E2E tests need to use the live development database because they test
against running frontend/backend services via Selenium.
"""
import pytest


@pytest.fixture(scope='session', autouse=True)
def django_db_setup(django_db_blocker):
    """
    Override pytest-django's database setup to use the live development database.

    E2E tests interact with running services, so they need to share the same
    database. The --reuse-db flag prevents pytest from destroying/recreating it.
    """
    # Allow all database access for E2E tests
    with django_db_blocker.unblock():
        # Ensure migrations are applied
        from django.core.management import call_command
        try:
            call_command('migrate', '--noinput')
        except Exception as e:
            print(f"Warning: Migration check failed: {e}")

        yield
