from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from django.views.decorators.debug import sensitive_variables

from imports.encryption import InvalidToken, decrypt_text, encrypt_text

from .providers.base import ProviderError

_DEFAULT_PORTS = {"http": 80, "https": 443}


def _origin(url: str) -> tuple:
    try:
        parts = urlsplit((url or "").strip())
        port = parts.port or _DEFAULT_PORTS.get(parts.scheme)
    except ValueError:
        return (None, None, None)
    return (parts.scheme, (parts.hostname or "").lower(), port)


def validate_base_url(value: str) -> None:
    # Not URLField: its validator rejects TLD-less hosts such as a compose
    # service named "ollama".
    parts = urlsplit(value)
    if (
        parts.scheme not in ("http", "https")
        or not parts.hostname
        or parts.query
        or parts.fragment
        or parts.username is not None
        or parts.password is not None
        or "?" in value
        or "#" in value
    ):
        raise ValidationError(
            _("Enter an http:// or https:// address, for example %(example)s."),
            params={"example": "https://api.openai.com/v1"},
            code="invalid_base_url",
        )


class LLMProvider(models.Model):
    """The deployment's one language-model connection (bring your own key)."""

    KIND_OPENAI_COMPATIBLE = "openai_compatible"
    KIND_CHOICES = [(KIND_OPENAI_COMPATIBLE, _("OpenAI-compatible API"))]

    SINGLETON_PK = 1

    kind = models.CharField(
        max_length=32,
        choices=KIND_CHOICES,
        default=KIND_OPENAI_COMPATIBLE,
        verbose_name=_("Provider type"),
    )
    base_url = models.CharField(
        max_length=500,
        blank=True,
        validators=[validate_base_url],
        verbose_name=_("Base URL"),
        help_text=_(
            "The API address including /v1, for example https://api.openai.com/v1, "
            "https://openrouter.ai/api/v1, or http://localhost:11434/v1 for Ollama."
        ),
    )
    api_key_encrypted = models.BinaryField(null=True, blank=True, editable=False)
    model = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("Model"),
        help_text=_("The model the assistant uses."),
    )
    enabled = models.BooleanField(
        default=False,
        verbose_name=_("Enabled"),
        help_text=_("The assistant may only call the provider while this is on."),
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("Updated by"),
    )

    class Meta:
        verbose_name = _("Language model provider")
        verbose_name_plural = _("Language model provider")

    def __str__(self) -> str:
        return str(_("Language model provider"))

    @classmethod
    def load(cls) -> "LLMProvider":
        obj, _created = cls.objects.get_or_create(pk=cls.SINGLETON_PK)
        return obj

    def save(self, *args, **kwargs):
        self.pk = self.SINGLETON_PK
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.enabled:
            missing = {}
            if not self.base_url:
                missing["base_url"] = _("Needed while the provider is enabled.")
            if not self.model:
                missing["model"] = _("Needed while the provider is enabled.")
            if missing:
                raise ValidationError(missing)

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key_encrypted)

    def set_api_key(self, key: str | None) -> None:
        self.api_key_encrypted = encrypt_text(key) if key else None

    @sensitive_variables()
    def get_api_key(self) -> str:
        if not self.api_key_encrypted:
            return ""
        try:
            return decrypt_text(self.api_key_encrypted)
        except InvalidToken:
            raise ProviderError("key_unreadable") from None

    def key_blocked_for(self, new_base_url: str, saved_base_url: str | None = None):
        """True when a key is stored and ``new_base_url`` is another origin
        than the saved one. Pass ``saved_base_url`` once self is mutated."""
        saved = self.base_url if saved_base_url is None else saved_base_url
        return self.has_api_key and _origin(new_base_url) != _origin(saved)

    @sensitive_variables()
    def key_for(self, base_url: str) -> str:
        """The stored key, but only for the stored origin: a caller trying a
        new address must type the key again, so the key cannot be redirected."""
        if _origin(base_url) != _origin(self.base_url):
            return ""
        return self.get_api_key()
