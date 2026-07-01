"""Shared helper for writing AuditLog entries with request context attached."""

from .models import AuditLog


def get_client_ip(request):
    """Best-effort client IP, preferring the reverse proxy's forwarded header."""
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_audit(request, *, action, entity_type, entity_id, details=None):
    """Create an AuditLog entry, attaching user/IP/session from the request.

    ``request.user`` may be anonymous (e.g. the public QR endpoint) — in that
    case ``user`` is left null rather than raising.
    """
    user = getattr(request, "user", None)
    if user is not None and not getattr(user, "is_authenticated", False):
        user = None
    session = getattr(request, "session", None)
    session_id = getattr(session, "session_key", None) if session else None

    return AuditLog.objects.create(
        user=user,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        source_ip=get_client_ip(request),
        session_id=session_id,
    )
