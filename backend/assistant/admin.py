from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.debug import sensitive_post_parameters

from .models import LLMProvider
from .providers import ProviderError
from .services import fetch_models


class ModelPickerWidget(forms.TextInput):
    """The model name field, enhanced by JS into a "Load models" button plus a
    dropdown. The text input stays as the submitted value and as the fallback
    for providers that cannot list models."""

    template_name = "assistant/widgets/model_picker.html"

    class Media:
        css = {"all": ["assistant/model_picker.css"]}
        js = ["assistant/model_picker.js"]


class LLMProviderAdminForm(forms.ModelForm):
    api_key = forms.CharField(
        required=False,
        label=_("API key"),
        widget=forms.PasswordInput(
            render_value=False, attrs={"autocomplete": "new-password"}
        ),
    )
    clear_api_key = forms.BooleanField(
        required=False, label=_("Remove the stored API key")
    )

    class Meta:
        model = LLMProvider
        fields = ["kind", "base_url", "api_key", "clear_api_key", "model", "enabled"]
        widgets = {"model": ModelPickerWidget}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_base_url = self.instance.base_url  # _post_clean mutates instance
        self.fields["model"].widget.attrs["data-models-url"] = reverse(
            "admin:assistant_llmprovider_models"
        )
        self.fields["api_key"].help_text = self._api_key_help()

    def _api_key_help(self):
        # A bound, failed form must not contradict the ticked box beside it.
        clear = self.fields["clear_api_key"]
        if self.is_bound and clear.widget.value_from_datadict(
            self.data, self.files, self.add_prefix("clear_api_key")
        ):
            return _("The stored key will be removed when you save.")
        if self.instance.has_api_key:
            return _("A key is stored. Leave empty to keep it.")
        return _("No key is stored. A local Ollama needs none.")

    def clean(self):
        data = super().clean()
        key, clear = data.get("api_key"), data.get("clear_api_key")
        if key and clear:
            self.add_error(
                "api_key",
                _("Either enter a new key or remove the stored one, not both."),
            )
        elif (
            not key
            and not clear
            and "base_url" in data
            and self.instance.key_blocked_for(data["base_url"], self._saved_base_url)
        ):
            self.add_error(
                "api_key",
                _(
                    "Enter the API key again for the new address, "
                    "or remove the stored key."
                ),
            )
        return data


@admin.register(LLMProvider)
class LLMProviderAdmin(admin.ModelAdmin):
    form = LLMProviderAdminForm
    readonly_fields = ["updated_at", "updated_by"]
    fieldsets = [
        (None, {"fields": ["kind", "base_url", "api_key", "clear_api_key"]}),
        (None, {"fields": ["model", "enabled"]}),
        (None, {"fields": ["updated_at", "updated_by"]}),
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # One row per deployment: the list would only ever hold one link.
        provider = LLMProvider.load()
        return redirect("admin:assistant_llmprovider_change", provider.pk)

    def save_model(self, request, obj, form, change):
        if form.cleaned_data.get("clear_api_key"):
            obj.set_api_key(None)
        elif form.cleaned_data.get("api_key"):
            obj.set_api_key(form.cleaned_data["api_key"])
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    def get_urls(self):
        return [
            path(
                "models/",
                self.admin_site.admin_view(self.models_view),
                name="assistant_llmprovider_models",
            ),
            *super().get_urls(),
        ]

    @method_decorator(sensitive_post_parameters("api_key"))
    def models_view(self, request):
        """JSON for the model picker; reads the unsaved form fields."""
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        if not self.has_change_permission(request):
            return JsonResponse({"error": str(_("Permission denied."))}, status=403)
        try:
            models = fetch_models(
                LLMProvider.load(),
                request.POST.get("base_url", ""),
                request.POST.get("api_key", "").strip(),
            )
        except ValidationError as exc:
            return JsonResponse({"error": " ".join(exc.messages)}, status=400)
        except ProviderError as exc:
            return JsonResponse({"error": exc.message, "code": exc.code}, status=502)
        return JsonResponse({"models": models})
