from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import AdminUser
from assistant.models import LLMProvider
from events.event_spec import apply, example_spec
from events.spec_test_support import at_now
from events.models import Event
from registrations.models import Registration
from families.models import Family


# The hashed-staticfiles manifest is absent in tests and irrelevant here.
@override_settings(
    FRONTEND_BASE_URL="http://fe.test",
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    },
)
class OpenAssistantLinkTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        with at_now():
            cls.event = apply(example_spec())[0]
        cls.staff = AdminUser.objects.create_superuser("adm", "pw12345")

    def setUp(self):
        LLMProvider.objects.update_or_create(
            pk=LLMProvider.SINGLETON_PK, defaults={"enabled": True}
        )
        self.client.force_login(self.staff)

    def page(self):
        with at_now():
            return self.client.get(
                reverse("admin:events_event_change", args=[self.event.pk])
            )

    @property
    def url(self):
        return f"http://fe.test/events/{self.event.pk}/setup"

    def test_link_shown_for_an_eligible_event(self):
        r = self.page()
        self.assertContains(r, f'href="{self.url}"')
        self.assertContains(r, "Open assistant")

    def test_hidden_when_provider_disabled(self):
        LLMProvider.objects.update(enabled=False)
        self.assertNotContains(self.page(), "/setup")

    def test_hidden_when_event_has_registrations(self):
        Registration.objects.create(
            event=self.event,
            family=Family.objects.create(last_name="P"),
            contact_email="p@example.com",
            verification_token_hash="x",
        )
        self.assertNotContains(self.page(), self.url)

    def test_hidden_without_the_assistant_permissions(self):
        # Can open the change page (change perm) but lacks add/delete on the spec models.
        from django.contrib.auth.models import Permission

        user = AdminUser.objects.create_user("lim", "pw12345", is_staff=True)
        user.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="events",
                codename__in=["view_event", "change_event"],
            )
        )
        self.client.force_login(user)
        r = self.page()
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, self.url)

    def test_not_on_the_add_form(self):
        r = self.client.get(reverse("admin:events_event_add"))
        self.assertNotContains(r, "Open assistant")
