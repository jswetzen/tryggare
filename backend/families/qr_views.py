"""
Public QR code endpoint - does not require authentication.
Only returns data when child is actively checked in (privacy-first).
"""

from django.conf import settings
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from checkins.audit import log_audit
from checkins.qr_utils import get_code_for_active_checkin


@api_view(["GET"])
@permission_classes([AllowAny])
def privacy_info(request):
    """
    Public endpoint exposing the operator-configured data-controller details.

    The privacy page and QR-page notice read this so each self-hosting operator
    can supply their own controller name/contact without a rebuild.
    """
    return Response(
        {
            "controller_name": settings.DATA_CONTROLLER_NAME,
            "contact_email": settings.DATA_CONTROLLER_CONTACT_EMAIL,
            "controller_url": settings.DATA_CONTROLLER_URL,
            "privacy_policy_url": settings.PRIVACY_POLICY_URL,
            "retention_days": settings.DATA_RETENTION_DAYS,
        }
    )


def _viewer_may_read_health_text(request, entity_type):
    """Mirror ``SafetyInfoDisclosureMixin.viewer_may_read_health_text`` (see
    ``families/serializers.py``) for this unauthenticated-by-default endpoint.

    Being logged in used to be sufficient on its own — any authenticated
    caller got the raw allergy/medical text on every GET, with no reveal
    step and no per-view audit row, unlike the check-in screen's own staff
    API (see that mixin's docstring for why that split exists). The line is
    the same one the check-in path uses: a viewer who can already change the
    field must see it (an edit form that hides its own value isn't one), so
    ``change_child``/``change_parent`` is what unmasks it here too. Anyone
    else — anonymous or authenticated — goes through ``qr_reveal_safety_info``,
    which writes ``qr_safety_info_revealed`` and, for a logged-in caller,
    attributes that row to them (``log_audit`` already does this).
    """
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    perm = (
        "families.change_child" if entity_type == "Child" else "families.change_parent"
    )
    return user.has_perm(perm)


def _resolve_child_safety_fields(checkin):
    """Resolve the concrete Child or Parent for a check-in's attendee and
    return (child_or_none, allergies, notes).

    Django MTI does not downcast checkin.attendee (it is a base Attendee, so
    isinstance(attendee, Child) is always False); resolve the concrete
    subclass explicitly so safety info is not silently dropped. The Parent
    branch matters here specifically: before it existed, an anonymous or
    authenticated caller's reveal/GET of a checked-in *parent* always got
    empty allergies/notes regardless of what was actually on the Parent
    record — the attendee-shaped ("parents carry these fields too, and an
    adult's allergy is not less sensitive") design intent was undermined by
    this function only ever looking at Child. Shared by qr_info and
    qr_reveal_safety_info so this subtlety only lives once.
    """
    from families.models import Child as ChildModel
    from families.models import Parent as ParentModel

    child = ChildModel.objects.filter(pk=checkin.attendee.pk).first()
    if child is not None:
        return child, child.allergies or "", child.notes or ""

    parent = ParentModel.objects.filter(pk=checkin.attendee.pk).first()
    if parent is not None:
        return None, parent.allergies or "", parent.notes or ""

    return None, "", ""


@api_view(["GET"])
@permission_classes([AllowAny])
def qr_info(request, code):
    """
    Public endpoint to retrieve child information by QR code.

    Privacy: Only returns data when child is ACTIVELY checked in.
    If checked out or code invalid, returns 404.

    Args:
        code: The short alphanumeric QR code (e.g., "A3B7K")

    Returns:
        - Child information if actively checked in
        - 404 if code invalid or child not checked in
    """
    qr_code = get_code_for_active_checkin(code)

    if qr_code is None:
        return Response(
            {"error": _("QR code not found or child is not currently checked in")},
            status=status.HTTP_404_NOT_FOUND,
        )

    checkin = qr_code.checkin_record
    attendee = checkin.attendee

    # Get parent information. Name + phone are sufficient for in-person
    # pickup matching; email is not needed here and its exposure on an
    # unauthenticated endpoint was a documented DPIA risk (R7).
    parents = attendee.family.parents.all()
    parent_info = [
        {
            "id": str(p.id),
            "name": p.name,
            "phone": p.phone or "",
            "relationship_type": p.relationship_type,
        }
        for p in parents
    ]

    # Deliberate: allergies/notes are resolved here regardless of
    # health_consent_status, including "needs_reconfirmation" (quarantined
    # pre-consent data). A safety decision, not an oversight — see DPIA §4
    # "Quarantine display policy".
    child, allergies, notes = _resolve_child_safety_fields(checkin)
    has_safety_info = bool(allergies) or bool(notes)

    # A viewer who may already change this attendee's record (change_child /
    # change_parent — Koordinator and above) sees the text directly, same as
    # the check-in screen's staff API: an edit form that hides its own value
    # isn't one. Everyone else — anonymous scanner or a logged-in volunteer
    # with only view access — gets a boolean signalling whether there's
    # anything to reveal; the text itself is only ever served through
    # qr_reveal_safety_info, a distinct, individually audited action (see
    # that view's docstring). This is what makes the Art. 9(2)(c) "vital
    # interests" basis this anonymous path relies on attach to a real, logged
    # access event instead of blanket ambient exposure on every page load
    # (DPIA §2, §4) — and it closes the same hole for the authenticated path,
    # which used to unmask on login alone with no reveal step and no audit
    # row of its own.
    entity_type = "Child" if child is not None else "Parent"
    may_read_health_text = _viewer_may_read_health_text(request, entity_type)

    if child is not None:
        attendee_data = {
            "id": str(child.id),
            "first_name": child.first_name,
            "last_name": child.last_name,
            "birthdate": str(child.birthdate) if child.birthdate else None,
            "allergies": allergies if may_read_health_text else None,
            "notes": notes if may_read_health_text else None,
            "has_safety_info": has_safety_info,
            "is_parent": False,
        }
    else:
        attendee_data = {
            "id": str(attendee.id),
            "first_name": attendee.first_name,
            "last_name": attendee.last_name,
            "birthdate": None,
            "allergies": allergies if may_read_health_text else None,
            "notes": notes if may_read_health_text else None,
            "has_safety_info": has_safety_info,
            "is_parent": True,
        }

    data = {
        "qr_code": qr_code.code,
        "checkin_record_id": str(checkin.id),
        "child": attendee_data,
        "current_session": {
            "id": str(checkin.session.id),
            "name": checkin.session.name,
            "check_in_time": checkin.check_in_time.isoformat(),
        },
        "parents": parent_info,
        "family_id": str(attendee.family.id),
        "supervised": checkin.supervised,
    }

    log_audit(
        request,
        action="qr_viewed",
        entity_type="Child" if child is not None else "Parent",
        entity_id=str(attendee.id),
        details={"qr_code": qr_code.code},
    )

    return Response(data)


class QRSafetyInfoRevealThrottle(AnonRateThrottle):
    """Deliberately tighter than qr_info's own (unscoped, generic "anon"
    10/minute) rate: revealing special-category health text is a rarer,
    more deliberate act than loading the page, and is the actual point at
    which the Art. 9(2)(c) vital-interests basis attaches (see DPIA §4).
    """

    scope = "qr_safety_info_reveal"


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([QRSafetyInfoRevealThrottle])
def qr_reveal_safety_info(request, code):
    """
    Public endpoint to reveal a checked-in child's allergy/emergency-medical
    text on explicit request.

    Split out from qr_info (GET) so loading the page and revealing the
    special-category fields are two distinguishable events: qr_info logs
    qr_viewed on every load regardless of who's looking; this endpoint logs
    qr_safety_info_revealed only when someone actually asks to see the
    allergy/notes text. This endpoint doesn't change WHO can see the data —
    both endpoints are AllowAny, and the checked-in-child scoping via
    get_code_for_active_checkin is the real access control — it only turns
    an ambient page load into a deliberate, individually logged act, which
    is what the Art. 9(2)(c) vital-interests basis this anonymous path
    relies on is meant to attach to (see DPIA §2/§4).

    Shared verbatim by a logged-in volunteer whose qr_info GET was masked
    (they lack change_child/change_parent — see
    _viewer_may_read_health_text): AllowAny here doesn't widen who reaches
    them past qr_info's own masking, and log_audit attributes the row to
    request.user whenever one is authenticated, so their reveal is named in
    the audit trail exactly like the check-in screen's reveal-safety-info.
    QRSafetyInfoRevealThrottle (AnonRateThrottle) only throttles anonymous
    callers, so a logged-in volunteer's reveals aren't rate-limited by it.

    Applies the same quarantine display policy as qr_info (DPIA §4): text
    is returned regardless of health_consent_status, including
    needs_reconfirmation — the safety rationale for showing possibly-
    unconfirmed data applies at least as strongly to an anonymous/emergency
    access as to routine staff viewing.
    """
    qr_code = get_code_for_active_checkin(code)

    if qr_code is None:
        return Response(
            {"error": _("QR code not found or child is not currently checked in")},
            status=status.HTTP_404_NOT_FOUND,
        )

    checkin = qr_code.checkin_record
    child, allergies, notes = _resolve_child_safety_fields(checkin)

    log_audit(
        request,
        action="qr_safety_info_revealed",
        entity_type="Child" if child is not None else "Parent",
        entity_id=str(checkin.attendee.id),
        details={
            "qr_code": qr_code.code,
            "had_allergies": bool(allergies),
            "had_notes": bool(notes),
        },
    )

    return Response({"allergies": allergies, "notes": notes})
