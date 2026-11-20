from unittest import mock

import socket

import requests
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import AdminUser
from tests.support import NonManifestStaticfilesTestCase

from .models import LLMProvider
from .providers import ProviderError, list_models

GET = "assistant.providers.openai_compatible.requests.get"
GETADDRINFO = "assistant.providers.openai_compatible.socket.getaddrinfo"


def _resolves_to(ip):
    return mock.patch(GETADDRINFO, return_value=[(2, 1, 6, "", (ip, 0))])


class PublicDNSMixin:
    # Hosts like "ollama" do not resolve in CI; resolution has its own tests.
    # Runs before the test's own setUp, which does not call super().
    def _pre_setup(self):
        super()._pre_setup()
        patcher = _resolves_to("93.184.216.34")
        patcher.start()
        self.addCleanup(patcher.stop)


def _response(status=200, json_body=None, raw=None):
    response = mock.MagicMock(status_code=status)
    body = raw if raw is not None else __import__("json").dumps(json_body).encode()
    response.iter_content.return_value = [body]
    response.__enter__.return_value = response
    return response


class ListModelsTests(PublicDNSMixin, TestCase):
    def test_parses_sorts_and_dedupes_ids(self):
        body = {"data": [{"id": "b"}, {"id": "a"}, {"id": "b"}, {"x": 1}, "junk"]}
        with mock.patch(GET, return_value=_response(json_body=body)) as get:
            self.assertEqual(list_models("http://ollama:11434/v1/", "sk-1"), ["a", "b"])
        url = get.call_args.args[0]
        kwargs = get.call_args.kwargs
        self.assertEqual(url, "http://ollama:11434/v1/models")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer sk-1")
        self.assertFalse(kwargs["allow_redirects"])

    def test_no_key_sends_no_authorization(self):
        with mock.patch(GET, return_value=_response(json_body={"data": []})) as get:
            list_models("http://localhost:11434/v1")
        self.assertNotIn("Authorization", get.call_args.kwargs["headers"])

    def test_errors_map_to_codes(self):
        cases = [
            (_response(401), "auth_failed"),
            (_response(404), "models_not_supported"),
            (_response(500), "http_error"),
            (_response(302), "http_error"),
            (_response(raw=b"<html>"), "bad_response"),
            (_response(json_body={"data": "nope"}), "bad_response"),
        ]
        for response, code in cases:
            with self.subTest(code=code), mock.patch(GET, return_value=response):
                with self.assertRaises(ProviderError) as ctx:
                    list_models("https://api.example.com/v1", "sk-secret")
                self.assertEqual(ctx.exception.code, code)
                self.assertNotIn("sk-secret", ctx.exception.message)

    def test_unreachable(self):
        with mock.patch(GET, side_effect=requests.ConnectionError("sk-secret")):
            with self.assertRaises(ProviderError) as ctx:
                list_models("https://api.example.com/v1", "sk-secret")
        self.assertEqual(ctx.exception.code, "unreachable")


class AddressAndParsingTests(PublicDNSMixin, TestCase):
    def test_link_local_and_metadata_blocked(self):
        for ip in ["169.254.169.254", "fe80::1", "fd00:ec2::254", "::ffff:169.254.1.1"]:
            with self.subTest(ip=ip), _resolves_to(ip), mock.patch(GET) as get:
                with self.assertRaises(ProviderError) as ctx:
                    list_models("http://metadata.example/v1")
                self.assertEqual(ctx.exception.code, "address_blocked")
                get.assert_not_called()

    def test_private_and_loopback_allowed(self):
        for ip in ["10.0.0.5", "127.0.0.1", "::1"]:
            with self.subTest(ip=ip), _resolves_to(ip):
                with mock.patch(GET, return_value=_response(json_body=[])):
                    self.assertEqual(list_models("http://ollama:11434/v1"), [])

    def test_unresolvable_is_unreachable(self):
        with mock.patch(GETADDRINFO, side_effect=socket.gaierror):
            with self.assertRaises(ProviderError) as ctx:
                list_models("http://nope.invalid/v1")
        self.assertEqual(ctx.exception.code, "unreachable")

    def test_deeply_nested_json_is_bad_response(self):
        raw = b"[" * 100000 + b"]" * 100000
        with mock.patch(GET, return_value=_response(raw=raw)):
            with self.assertRaises(ProviderError) as ctx:
                list_models("https://api.example.com/v1")
        self.assertEqual(ctx.exception.code, "bad_response")

    def test_as_dict_has_no_status(self):
        self.assertNotIn("status", ProviderError("http_error", 500).as_dict())


class ProviderModelTests(PublicDNSMixin, TestCase):
    def test_singleton_and_key_encrypted(self):
        LLMProvider(base_url="x").save()
        provider = LLMProvider.load()  # the row above, not a second one
        self.assertEqual(LLMProvider.objects.count(), 1)
        provider.base_url = "https://api.openai.com/v1"
        provider.set_api_key("sk-secret")
        provider.save()
        stored = LLMProvider.load()
        self.assertNotIn(b"sk-secret", bytes(stored.api_key_encrypted))
        self.assertEqual(stored.get_api_key(), "sk-secret")

    def test_key_only_for_its_own_url(self):
        provider = LLMProvider(base_url="https://api.openai.com/v1")
        provider.set_api_key("sk-secret")
        self.assertEqual(provider.key_for("https://api.openai.com/v1/"), "sk-secret")
        self.assertEqual(provider.key_for("https://evil.example/v1"), "")

    def test_key_origin_comparison(self):
        provider = LLMProvider(base_url="https://API.openai.com/v1")
        provider.set_api_key("sk-secret")
        self.assertEqual(provider.key_for("https://api.openai.com:443/v2"), "sk-secret")
        self.assertFalse(provider.key_blocked_for("https://api.openai.com/other"))
        self.assertTrue(provider.key_blocked_for("http://api.openai.com/v1"))
        self.assertTrue(provider.key_blocked_for("https://api.openai.com:8443/v1"))

    def test_undecryptable_key_raises_key_unreadable(self):
        provider = LLMProvider(api_key_encrypted=b"garbage")
        with self.assertRaises(ProviderError) as ctx:
            provider.get_api_key()
        self.assertEqual(ctx.exception.code, "key_unreadable")

    def test_base_url_rejects_query_fragment_userinfo(self):
        from django.core.exceptions import ValidationError

        for url in [
            "https://a.example/v1?x=1",
            "https://a.example/v1#frag",
            "https://user:pw@a.example/v1",
            "https://user@a.example/v1",
            "https://a.example/v1?",
        ]:
            with self.subTest(url=url), self.assertRaises(ValidationError):
                LLMProvider(base_url=url).full_clean()

    def test_enabled_needs_url_and_model(self):
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError) as ctx:
            LLMProvider(enabled=True).full_clean()
        self.assertEqual(set(ctx.exception.message_dict), {"base_url", "model"})

    def test_base_url_accepts_compose_hostnames_only_http(self):
        from django.core.exceptions import ValidationError

        LLMProvider(base_url="http://ollama:11434/v1").full_clean()
        with self.assertRaises(ValidationError):
            LLMProvider(base_url="file:///etc/passwd").full_clean()


class ProviderAPITests(PublicDNSMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = AdminUser.objects.create_superuser("llmadmin", "pw12345")
        cls.viewer = AdminUser.objects.create_user("llmviewer", "pw12345")
        cls.viewer.user_permissions.add(
            Permission.objects.get(codename="view_llmprovider")
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_key_is_write_only(self):
        response = self.client.patch(
            reverse("llm-provider"),
            {
                "base_url": "https://api.openai.com/v1",
                "api_key": "sk-secret",
                "model": "gpt-5",
                "enabled": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertNotIn("sk-secret", response.content.decode())
        self.assertTrue(response.data["has_api_key"])
        response = self.client.get(reverse("llm-provider"))
        self.assertNotIn("sk-secret", response.content.decode())
        self.assertEqual(LLMProvider.load().updated_by, self.admin)

    def test_blank_key_keeps_and_clear_removes(self):
        provider = LLMProvider.load()
        provider.set_api_key("sk-secret")
        provider.save()
        self.client.patch(reverse("llm-provider"), {"api_key": ""}, format="json")
        self.assertEqual(LLMProvider.load().get_api_key(), "sk-secret")
        self.client.patch(
            reverse("llm-provider"), {"clear_api_key": True}, format="json"
        )
        self.assertFalse(LLMProvider.load().has_api_key)

    def _store_key(self):
        provider = LLMProvider.load()
        provider.base_url = "https://api.openai.com/v1"
        provider.set_api_key("sk-secret")
        provider.save()

    def test_url_change_without_key_is_refused(self):
        self._store_key()
        response = self.client.patch(
            reverse("llm-provider"),
            {"base_url": "https://evil.example/v1"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("api_key", response.data)
        self.assertEqual(LLMProvider.load().base_url, "https://api.openai.com/v1")
        response = self.client.patch(
            reverse("llm-provider"),
            {"base_url": "https://evil.example/v1", "api_key": ""},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_url_change_with_new_key_or_clear_is_accepted(self):
        self._store_key()
        url = reverse("llm-provider")
        response = self.client.patch(
            url,
            {"base_url": "https://other.example/v1", "api_key": "sk-new"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(LLMProvider.load().get_api_key(), "sk-new")
        response = self.client.patch(
            url,
            {"base_url": "https://third.example/v1", "clear_api_key": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(LLMProvider.load().has_api_key)

    def test_same_origin_path_change_keeps_key(self):
        self._store_key()
        response = self.client.patch(
            reverse("llm-provider"),
            {"base_url": "https://api.openai.com:443/v2"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(LLMProvider.load().get_api_key(), "sk-secret")

    def test_key_and_clear_together_refused(self):
        response = self.client.patch(
            reverse("llm-provider"),
            {"api_key": "sk-1", "clear_api_key": True},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("api_key", response.data)

    def test_bad_urls_refused(self):
        for url in [
            "https://a.example/v1?x=1",
            "https://a.example/#f",
            "https://u:p@a.example/v1",
        ]:
            with self.subTest(url=url):
                response = self.client.patch(
                    reverse("llm-provider"), {"base_url": url}, format="json"
                )
                self.assertEqual(response.status_code, 400)

    def test_put_not_allowed(self):
        self.assertEqual(
            self.client.put(reverse("llm-provider"), {}, format="json").status_code,
            405,
        )

    def test_change_only_user_can_get(self):
        user = AdminUser.objects.create_user("llmchanger", "pw12345")
        user.user_permissions.add(Permission.objects.get(codename="change_llmprovider"))
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get(reverse("llm-provider")).status_code, 200)

    def test_unreadable_stored_key_is_502(self):
        provider = LLMProvider.load()
        provider.base_url = "https://api.openai.com/v1"
        provider.api_key_encrypted = b"garbage"
        provider.save()
        response = self.client.post(reverse("llm-provider-models"), {}, format="json")
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.data["errors"][0]["code"], "key_unreadable")

    def test_enable_without_model_is_refused(self):
        response = self.client.patch(
            reverse("llm-provider"), {"enabled": True}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(LLMProvider.load().enabled)

    def test_viewer_can_read_not_write_or_load(self):
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.get(reverse("llm-provider")).status_code, 200)
        self.assertEqual(
            self.client.patch(reverse("llm-provider"), {}, format="json").status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                reverse("llm-provider-models"), {}, format="json"
            ).status_code,
            403,
        )

    def test_load_models_uses_stored_key_only_for_stored_url(self):
        provider = LLMProvider.load()
        provider.base_url = "https://api.openai.com/v1"
        provider.set_api_key("sk-secret")
        provider.save()
        ok = _response(json_body={"data": [{"id": "gpt-5"}]})
        with mock.patch(GET, return_value=ok) as get:
            response = self.client.post(
                reverse("llm-provider-models"), {}, format="json"
            )
        self.assertEqual(response.data, {"models": ["gpt-5"]})
        self.assertEqual(
            get.call_args.kwargs["headers"]["Authorization"], "Bearer sk-secret"
        )

        with mock.patch(GET, return_value=ok) as get:
            self.client.post(
                reverse("llm-provider-models"),
                {"base_url": "https://evil.example/v1"},
                format="json",
            )
        self.assertNotIn("Authorization", get.call_args.kwargs["headers"])

    def test_load_models_provider_error_is_502(self):
        with mock.patch(GET, return_value=_response(401)):
            response = self.client.post(
                reverse("llm-provider-models"),
                {"base_url": "https://api.openai.com/v1", "api_key": "bad"},
                format="json",
            )
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.data["errors"][0]["code"], "auth_failed")

    def test_load_models_bad_url_is_400(self):
        response = self.client.post(
            reverse("llm-provider-models"), {"base_url": "ftp://x"}, format="json"
        )
        self.assertEqual(response.status_code, 400)


class ProviderAdminTests(PublicDNSMixin, NonManifestStaticfilesTestCase, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = AdminUser.objects.create_superuser("llmadmin2", "pw12345")

    def setUp(self):
        LLMProvider.load()
        self.client.force_login(self.admin)

    def test_changelist_redirects_to_the_one_row(self):
        response = self.client.get(reverse("admin:assistant_llmprovider_changelist"))
        self.assertRedirects(
            response,
            reverse("admin:assistant_llmprovider_change", args=[1]),
        )

    def test_change_page_never_renders_the_key(self):
        provider = LLMProvider.load()
        provider.set_api_key("sk-secret")
        provider.save()
        response = self.client.get(
            reverse("admin:assistant_llmprovider_change", args=[1])
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "sk-secret")
        self.assertContains(response, "llm-load-models")
        self.assertContains(response, "<select")
        self.assertContains(response, 'name="model"')

    def test_save_sets_key_and_blank_keeps_it(self):
        url = reverse("admin:assistant_llmprovider_change", args=[1])
        data = {
            "kind": "openai_compatible",
            "base_url": "http://ollama:11434/v1",
            "api_key": "sk-secret",
            "model": "llama3.2",
            "enabled": "on",
        }
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.assertEqual(LLMProvider.load().get_api_key(), "sk-secret")
        data["api_key"] = ""
        self.client.post(url, data)
        self.assertEqual(LLMProvider.load().get_api_key(), "sk-secret")
        data["clear_api_key"] = "on"
        self.client.post(url, data)
        self.assertFalse(LLMProvider.load().has_api_key)

    def test_models_view(self):
        ok = _response(json_body={"data": [{"id": "llama3.2"}]})
        with mock.patch(GET, return_value=ok):
            response = self.client.post(
                reverse("admin:assistant_llmprovider_models"),
                {"base_url": "http://ollama:11434/v1"},
            )
        self.assertEqual(response.json(), {"models": ["llama3.2"]})
        with mock.patch(GET, return_value=_response(401)):
            response = self.client.post(
                reverse("admin:assistant_llmprovider_models"),
                {"base_url": "http://ollama:11434/v1"},
            )
        self.assertEqual(response.status_code, 502)
        self.assertIn("error", response.json())
        with mock.patch(GET, return_value=_response(404)):
            response = self.client.post(
                reverse("admin:assistant_llmprovider_models"),
                {"base_url": "http://ollama:11434/v1"},
            )
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["code"], "models_not_supported")
        self.assertIn("error", response.json())

    def _change_data(self, **over):
        data = {
            "kind": "openai_compatible",
            "base_url": "https://api.openai.com/v1",
            "api_key": "",
            "model": "gpt-5",
        }
        return {**data, **over}

    def _store_key(self):
        provider = LLMProvider.load()
        provider.base_url = "https://api.openai.com/v1"
        provider.set_api_key("sk-secret")
        provider.save()

    def test_url_change_without_key_refused(self):
        self._store_key()
        url = reverse("admin:assistant_llmprovider_change", args=[1])
        response = self.client.post(
            url, self._change_data(base_url="https://evil.example/v1")
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("api_key", response.context["adminform"].form.errors)
        self.assertEqual(LLMProvider.load().base_url, "https://api.openai.com/v1")

    def test_url_change_with_key_or_clear_accepted(self):
        self._store_key()
        url = reverse("admin:assistant_llmprovider_change", args=[1])
        response = self.client.post(
            url,
            self._change_data(base_url="https://other.example/v1", api_key="sk-new"),
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(LLMProvider.load().get_api_key(), "sk-new")
        response = self.client.post(
            url,
            self._change_data(base_url="https://third.example/v1", clear_api_key="on"),
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(LLMProvider.load().has_api_key)

    def test_same_origin_path_change_keeps_key(self):
        self._store_key()
        url = reverse("admin:assistant_llmprovider_change", args=[1])
        response = self.client.post(
            url, self._change_data(base_url="https://api.openai.com/v2")
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(LLMProvider.load().get_api_key(), "sk-secret")

    def test_key_and_clear_together_refused(self):
        url = reverse("admin:assistant_llmprovider_change", args=[1])
        response = self.client.post(
            url, self._change_data(api_key="sk-1", clear_api_key="on")
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("api_key", response.context["adminform"].form.errors)

    def test_key_help_follows_the_ticked_remove_box(self):
        provider = LLMProvider.load()
        provider.set_api_key("sk-1")
        provider.save()
        url = reverse("admin:assistant_llmprovider_change", args=[1])
        response = self.client.post(
            url, self._change_data(api_key="sk-2", clear_api_key="on")
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The stored key will be removed when you save.")
        self.assertNotContains(response, "A key is stored.")
        self.assertContains(self.client.get(url), "A key is stored.")

    def test_models_view_unreadable_key_is_502(self):
        provider = LLMProvider.load()
        provider.base_url = "http://ollama:11434/v1"
        provider.api_key_encrypted = b"garbage"
        provider.save()
        response = self.client.post(
            reverse("admin:assistant_llmprovider_models"),
            {"base_url": "http://ollama:11434/v1"},
        )
        self.assertEqual(response.status_code, 502)
