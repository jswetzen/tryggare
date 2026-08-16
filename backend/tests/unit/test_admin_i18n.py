"""Admin language-switcher tests.

The whole point of the switcher (docs/roadmap conversation, 2026-08-16) is
that it must *override* the browser's Accept-Language header once used, not
just render a control. A test that only checks the <select> is present would
pass on a switcher that does nothing, so every test here drives an actual
request/response cycle through ``django.views.i18n.set_language`` and then
re-requests a page with the *opposite* Accept-Language header to prove the
choice stuck.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

AdminUser = get_user_model()

ADMIN_INDEX_TITLE_EN = "Choose what to manage"
ADMIN_INDEX_TITLE_SV = "Välj vad du vill hantera"


@pytest.fixture(autouse=True)
def _non_manifest_staticfiles(settings):
    """Every test in this module renders a full admin template (index or
    login), which pulls in {% static %} tags for admin/css/base.css etc. The
    project's real STORAGES (config/settings/base.py) uses whitenoise's
    CompressedManifestStaticFilesStorage, which resolves {% static %} through
    a staticfiles.json manifest built by `collectstatic` — a step the test
    environment never runs, so any manifest-backed lookup raises ValueError.

    Swapping in plain StaticFilesStorage here only relaxes *how* static URLs
    are resolved (no hashing/manifest lookup); it does not touch anything
    these tests assert on (i18n behaviour, cookie name, switcher markup), so
    it can't silently mask a broken switcher. Scoped to this module only — no
    established pattern for this existed elsewhere in tests/unit/ to follow.
    """
    settings.STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }


@pytest.fixture
def admin_user(db):
    return AdminUser.objects.create_superuser(
        username="i18n-admin", password="pw12345!", name="I18n Admin"
    )


@pytest.fixture
def client(admin_user):
    c = Client()
    c.login(username="i18n-admin", password="pw12345!")
    return c


def _switch_language(client, language):
    response = client.post(
        reverse("set_language"),
        data={"language": language, "next": "/admin/"},
        HTTP_REFERER="http://testserver/admin/",
    )
    assert response.status_code == 302
    return response


@pytest.mark.django_db
def test_default_accept_language_still_governs_before_any_switch(client):
    """Sanity baseline: with no override, Accept-Language wins as before."""
    response = client.get(reverse("admin:index"), HTTP_ACCEPT_LANGUAGE="en-US")
    assert ADMIN_INDEX_TITLE_EN.encode() in response.content


@pytest.mark.django_db
def test_switching_to_swedish_overrides_english_accept_language(client):
    _switch_language(client, "sv")

    response = client.get(reverse("admin:index"), HTTP_ACCEPT_LANGUAGE="en-US")

    assert ADMIN_INDEX_TITLE_SV.encode() in response.content
    assert ADMIN_INDEX_TITLE_EN.encode() not in response.content


@pytest.mark.django_db
def test_switching_to_english_overrides_swedish_accept_language(client):
    _switch_language(client, "sv")  # start from a non-default state
    _switch_language(client, "en")

    response = client.get(reverse("admin:index"), HTTP_ACCEPT_LANGUAGE="sv-SE")

    assert ADMIN_INDEX_TITLE_EN.encode() in response.content
    assert ADMIN_INDEX_TITLE_SV.encode() not in response.content


@pytest.mark.django_db
def test_language_cookie_shares_the_frontend_spa_cookie_name(client):
    """The SPA's own switcher reads/writes a cookie literally named
    ``django_language`` (frontend/src/lib/i18n/i18n.ts). Django's
    ``set_language`` view writes ``settings.LANGUAGE_COOKIE_NAME``, which
    must stay at its default value for the two switchers to share state."""
    response = _switch_language(client, "sv")
    assert "django_language" in response.cookies
    assert response.cookies["django_language"].value == "sv"


@pytest.mark.django_db
def test_switcher_control_renders_on_the_admin_index(client):
    response = client.get(reverse("admin:index"), HTTP_ACCEPT_LANGUAGE="en-US")
    assert b'id="language-switcher-select"' in response.content
    assert b'value="en"' in response.content
    assert b'value="sv"' in response.content


def test_switcher_control_renders_on_the_login_page(db):
    anonymous_client = Client()
    response = anonymous_client.get(
        reverse("admin:login"), HTTP_ACCEPT_LANGUAGE="en-US"
    )
    assert b'id="language-switcher-select"' in response.content
