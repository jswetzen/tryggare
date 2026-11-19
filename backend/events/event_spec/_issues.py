"""Issues and the exception that carries them; imported by every other module here."""

from django.utils.translation import gettext_lazy as _

# What each kind of row is called in a message.
NOUNS = {
    "sessions": _("session"),
    "ticket_types": _("ticket type"),
    "extras": _("extra"),
    "promo_codes": _("promo code"),
}


def issue(path: str, code: str, message) -> dict:
    return {"path": path, "code": code, "message": str(message)}


class SpecError(Exception):
    """The spec was refused; nothing was written. ``errors`` are validate()'s issues."""

    def __init__(self, errors: list[dict], warnings: list[dict] | None = None):
        super().__init__("; ".join(f"{e['path']}: {e['message']}" for e in errors))
        self.errors = errors
        self.warnings = warnings or []
