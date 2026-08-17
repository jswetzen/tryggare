import pytest

from tests.support import NON_MANIFEST_STORAGES


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
