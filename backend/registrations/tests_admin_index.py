"""Admin index triage (increment 0.4).

The failure this exists to prevent: the admin index listed 27 model entries
across nine unordered app blocks. Several could never answer a volunteer's
question — a model deprecated in its own docstring, an MTI base whose rows
are already listed as its two subclasses, and a model registered *only* so
another admin's autocomplete works. Finding "the ticket screen" meant
reading past all of them.

The fix is ``get_model_perms() -> {}``, not ``admin.site.unregister``. That
distinction is the fragile part: unregistering looks like the "simpler"
version of the same change, and it silently breaks every autocomplete
widget pointing at a hidden model — at runtime, in production, with no
test failing. So the first test below drives Django's real autocomplete
endpoint, which raises PermissionDenied the moment a target model is not in
the registry.
"""

from decimal import Decimal

from django.contrib.admin.sites import site
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from accounts.models import AdminUser
from checkins.models import CheckInRecord
from events.models import Event, Extra, ExtraChoice, Ticket
from families.models import Attendee
from imports.models import FestivalProImportSource, ImportSource
from printing.models import PrintJob

from .models import RegistrationExtra

# The project ships WhiteNoise's manifest static storage, which refuses to
# resolve admin CSS unless collectstatic has run. Rendering an admin page in
# a test is unrelated to static-asset hashing, so swap in the plain backend.
PLAIN_STATICFILES = override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    }
)

# Every model deliberately taken off the index, and why. Kept as data so a
# future "let's just unregister these" refactor trips the registry check
# below rather than only the one autocomplete case.
HIDDEN_MODELS = [
    Ticket,  # deprecated in its own docstring
    Attendee,  # MTI base of Child and Parent
    ExtraChoice,  # registered for RegistrationExtraAdmin's autocomplete
    CheckInRecord,
    FestivalProImportSource,  # reachable as an inline on ImportSourceAdmin
    PrintJob,
]


class ExtraChoiceAutocompleteStillWorksTest(TestCase):
    """``ExtraChoice`` is hidden from the index but must stay registered:
    ``RegistrationExtraAdmin.autocomplete_fields`` includes ``choice``, and
    Django resolves that widget through ``admin.site.get_model_admin()``.
    Unregister it and this endpoint answers 403 instead of the choices."""

    @classmethod
    def setUpTestData(cls):
        cls.user = AdminUser.objects.create_superuser("autocomplete", "pw12345")
        cls.event = Event.objects.create(
            name="Sommarläger 2026",
            start_date="2026-07-01",
            end_date="2026-07-05",
        )
        cls.extra = Extra.objects.create(
            event=cls.event,
            name="T-shirt",
            price=Decimal("150.00"),
            requires_choice=True,
        )
        cls.medium = ExtraChoice.objects.create(extra=cls.extra, label="Medium")
        cls.large = ExtraChoice.objects.create(extra=cls.extra, label="Large")

    def setUp(self):
        self.client.force_login(self.user)

    def _autocomplete(self, term):
        return self.client.get(
            reverse("admin:autocomplete"),
            {
                "app_label": RegistrationExtra._meta.app_label,
                "model_name": RegistrationExtra._meta.model_name,
                "field_name": "choice",
                "term": term,
            },
        )

    def test_autocomplete_endpoint_returns_matching_choices(self):
        """The real endpoint, not the rendered widget: it runs its own
        registry lookup and permission check, and that is what breaks."""
        response = self._autocomplete("Med")
        self.assertEqual(response.status_code, 200, response.content)
        results = response.json()["results"]
        self.assertEqual([r["id"] for r in results], [str(self.medium.id)])
        self.assertIn("Medium", results[0]["text"])

    def test_autocomplete_endpoint_returns_every_choice_for_a_blank_term(self):
        response = self._autocomplete("")
        self.assertEqual(response.status_code, 200, response.content)
        ids = {r["id"] for r in response.json()["results"]}
        self.assertEqual(ids, {str(self.medium.id), str(self.large.id)})

    def test_hidden_models_are_still_in_the_admin_registry(self):
        """Hiding is ``get_model_perms() -> {}``. Unregistering would remove
        these from the registry and take their autocompletes with them."""
        for model in HIDDEN_MODELS:
            with self.subTest(model=model.__name__):
                self.assertIn(model, site._registry)

    def test_hidden_models_report_no_perms_but_keep_view_permission(self):
        """``get_model_perms`` drives only the index. ``has_view_permission``
        is what the autocomplete endpoint and the change views ask, and it
        must still say yes."""
        request = RequestFactory().get("/admin/")
        request.user = self.user
        for model in HIDDEN_MODELS:
            with self.subTest(model=model.__name__):
                model_admin = site._registry[model]
                self.assertEqual(model_admin.get_model_perms(request), {})
                self.assertTrue(model_admin.has_view_permission(request))


@PLAIN_STATICFILES
class AdminIndexTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = AdminUser.objects.create_superuser("indexroot", "pw12345")

    def setUp(self):
        self.client.force_login(self.superuser)

    def _index_models(self):
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 200)
        return {
            (app["app_label"], model["object_name"])
            for app in response.context["app_list"]
            for model in app["models"]
        }

    def _index_app_labels(self):
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 200)
        return [app["app_label"] for app in response.context["app_list"]]

    def test_hidden_models_are_absent_even_for_a_superuser(self):
        """``get_model_perms`` returning {} hides regardless of privilege.
        That is intended: a superuser browsing the index is a volunteer
        coordinator too, and nothing here is a permission decision."""
        listed = self._index_models()
        for model in HIDDEN_MODELS:
            with self.subTest(model=model.__name__):
                self.assertNotIn(
                    (model._meta.app_label, model.__name__),
                    listed,
                )

    def test_auth_group_stays_visible(self):
        """Tenant administrators are Django-admin users scoped by group, so
        Groups is the role-management surface — the one thing on this index
        an organisation needs in order to compose a custom role."""
        self.assertIn(("auth", "Group"), self._index_models())

    def test_models_that_must_stay_visible_are_still_there(self):
        listed = self._index_models()
        for app_label, object_name in [
            ("events", "Event"),
            ("events", "EventTicket"),
            ("events", "SessionTicket"),
            ("events", "Extra"),
            ("families", "Family"),
            ("families", "Child"),
            ("families", "Parent"),
            ("registrations", "Registration"),
            ("registrations", "Payment"),
            # Unhidden on review: the only surface that answers "how many
            # size-M shirts", until the dedicated extras screen ships.
            ("registrations", "RegistrationExtra"),
            ("checkins", "AuditLog"),
            ("imports", "ImportSource"),
            ("printing", "Printer"),
            ("accounts", "AdminUser"),
        ]:
            with self.subTest(model=object_name):
                self.assertIn((app_label, object_name), listed)

    def test_daily_apps_sort_above_setup_and_machinery(self):
        labels = self._index_app_labels()
        for daily in ("events", "registrations"):
            for machinery in ("imports", "printing"):
                with self.subTest(daily=daily, machinery=machinery):
                    self.assertLess(labels.index(daily), labels.index(machinery))

    def test_index_is_branded(self):
        response = self.client.get(reverse("admin:index"))
        content = response.content.decode()
        self.assertIn("Tryggare administration", content)
        self.assertIn("Choose what to manage", content)
        self.assertNotIn("Django administration", content)
        # The browser tab, not only the page body: this surface is
        # customer-facing, so no "Django site admin" anywhere on it.
        self.assertIn("<title>Choose what to manage | Tryggare admin", content)
        self.assertNotIn("Django site admin", content)


@PLAIN_STATICFILES
class FestivalProConfigStaysReachableTest(TestCase):
    """Hiding ``FestivalProImportSource`` from the index removed the only
    navigable route to the FestivalPro login/export URLs. The inline on
    ImportSourceAdmin is what puts it back — without it, editing those URLs
    means typing an admin URL by hand, which is a straight loss of function.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = AdminUser.objects.create_superuser("importer", "pw12345")
        cls.event = Event.objects.create(
            name="Sommarläger 2026",
            start_date="2026-07-01",
            end_date="2026-07-05",
        )
        cls.festivalpro = ImportSource.objects.create(
            name="FestivalPro 2026",
            provider_type=ImportSource.PROVIDER_FESTIVALPRO,
            event=cls.event,
        )
        cls.planningcenter = ImportSource.objects.create(
            name="Planning Center 2026",
            provider_type=ImportSource.PROVIDER_PLANNINGCENTER,
            event=cls.event,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def _change_page(self, source):
        return self.client.get(
            reverse("admin:imports_importsource_change", args=[source.pk])
        )

    def test_existing_config_is_editable_from_its_import_source(self):
        config = FestivalProImportSource.objects.create(
            source=self.festivalpro,
            login_url="https://example.test/login",
            export_url="https://example.test/export",
        )
        response = self._change_page(self.festivalpro)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("https://example.test/export", content)
        self.assertIn(str(config.pk), content)

    def test_a_festivalpro_source_without_config_is_offered_a_blank_form(self):
        response = self._change_page(self.festivalpro)
        self.assertEqual(response.status_code, 200)
        formset = response.context["inline_admin_formsets"][0].formset
        self.assertEqual(len(formset.forms), 1)

    def test_a_non_festivalpro_source_is_not_offered_one(self):
        """A Planning Center source has no FestivalPro config and never
        will — an empty form there is just another confusing field."""
        response = self._change_page(self.planningcenter)
        self.assertEqual(response.status_code, 200)
        formset = response.context["inline_admin_formsets"][0].formset
        self.assertEqual(len(formset.forms), 0)
