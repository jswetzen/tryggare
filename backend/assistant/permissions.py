"""The one eligibility check for the assistant: consumer, runner and (step 3) views."""

from django.contrib.auth import get_user_model

from events import event_spec
from events.models import Event
from events.services import REPLACE_PERMISSIONS, VIEW_PERMISSIONS

NOT_AUTHENTICATED = "not_authenticated"
PERMISSION_DENIED = "permission_denied"
EVENT_NOT_ELIGIBLE = "event_not_eligible"


def fresh_user(user):
    """Reload: Django caches a user's permissions on the instance, so a long-lived
    connection would never see a revocation."""
    return get_user_model().objects.filter(pk=user.pk, is_active=True).first()


def lacks_permission(user) -> str | None:
    """A reason code, or None. Same bar as the staff spec API: view to read and
    add/change/delete to replace, since a proposal exists to be applied."""
    if user is None or not user.is_authenticated or not user.is_active:
        return NOT_AUTHENTICATED
    if not all(user.has_perm(p) for p in VIEW_PERMISSIONS + REPLACE_PERMISSIONS):
        return PERMISSION_DENIED
    return None


def can_use_assistant(user, event: Event) -> tuple[bool, list[dict]]:
    """``(ok, issues)``; each issue has a ``code`` (the constants above) and a
    ``message``. Pass a user loaded this request (see ``fresh_user``)."""
    reason = lacks_permission(user)
    if reason:
        return False, [{"code": reason, "message": "Not allowed to use the assistant."}]
    blockers = event_spec.apply_blockers(event)
    if blockers:
        return False, [
            {"code": EVENT_NOT_ELIGIBLE, "message": f"{b['message']} [{b['code']}]"}
            for b in blockers
        ]
    return True, []
