"""Issues and the exception that carries them; imported by every other module here."""


def issue(path: str, code: str, message) -> dict:
    return {"path": path, "code": code, "message": str(message)}


class SpecError(Exception):
    """The spec was refused; nothing was written. ``errors`` are validate()'s issues."""

    def __init__(self, errors: list[dict], warnings: list[dict] | None = None):
        super().__init__("; ".join(f"{e['path']}: {e['message']}" for e in errors))
        self.errors = errors
        self.warnings = warnings or []
