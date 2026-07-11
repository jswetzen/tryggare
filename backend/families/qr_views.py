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


def _resolve_child_safety_fields(checkin):
    """Resolve the concrete Child (if any) for a check-in's attendee and
    return (child_or_none, allergies, notes).

    Django MTI does not downcast checkin.attendee (it is a base Attendee, so
    isinstance(attendee, Child) is always False); resolve the concrete Child
    explicitly so child safety info is not silently dropped. Shared by
    qr_info and qr_reveal_safety_info so this subtlety only lives once.
    """
    from families.models import Child as ChildModel

    child = ChildModel.objects.filter(pk=checkin.attendee.pk).first()
    if child is None:
        return None, "", ""
    return child, child.allergies or "", child.notes or ""


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

    # Staff (authenticated) see allergy/medical-notes text directly, same as
    # every other staff-facing view. An anonymous caller (the common case —
    # this endpoint is reached by scanning a physical label, no login) only
    # gets a boolean signalling whether there's anything to reveal; the text
    # itself is only ever served through qr_reveal_safety_info, a distinct,
    # throttled, individually audited action — see that view's docstring for
    # why. This is what makes the Art. 9(2)(c) "vital interests" basis this
    # anonymous path relies on attach to a real, logged access event instead
    # of blanket ambient exposure on every page load (DPIA §2, §4).
    is_staff_viewer = bool(getattr(request.user, "is_authenticated", False))

    if child is not None:
        attendee_data = {
            "id": str(child.id),
            "first_name": child.first_name,
            "last_name": child.last_name,
            "birthdate": str(child.birthdate) if child.birthdate else None,
            "allergies": allergies if is_staff_viewer else None,
            "notes": notes if is_staff_viewer else None,
            "has_safety_info": has_safety_info,
            "is_parent": False,
        }
    else:
        attendee_data = {
            "id": str(attendee.id),
            "first_name": attendee.first_name,
            "last_name": attendee.last_name,
            "birthdate": None,
            "allergies": allergies if is_staff_viewer else None,
            "notes": notes if is_staff_viewer else None,
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
