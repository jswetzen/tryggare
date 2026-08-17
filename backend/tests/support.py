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
