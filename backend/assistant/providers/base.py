from django.utils.translation import gettext_lazy as _

MESSAGES = {
    "unreachable": _("Could not reach the provider. Check the base URL."),
    "auth_failed": _("The provider rejected the API key."),
    "models_not_supported": _(
        "The provider does not list its models. Type the model name instead."
    ),
    "http_error": _("The provider answered with an error."),
    "bad_response": _("The provider's answer was not a model list."),
    "address_blocked": _("That address is not allowed."),
    "key_unreadable": _("The stored API key can no longer be read. Enter it again."),
}


class ProviderError(Exception):
    """A failed provider call. The message never contains the key or the
    provider's response body."""

    def __init__(self, code: str, status: int | None = None):
        self.code = code
        self.status = status
        super().__init__(code)

    @property
    def message(self) -> str:
        return str(MESSAGES[self.code])

    def as_dict(self) -> dict:
        # No status: it would let callers probe which ports answer how.
        return {"code": self.code, "message": self.message}
