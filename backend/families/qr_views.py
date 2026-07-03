"""
Public QR code endpoint - does not require authentication.
Only returns data when child is actively checked in (privacy-first).
"""

from django.conf import settings
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

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

    # Build attendee payload defensively — Child has birthdate/allergies/notes,
    # Parent doesn't. Django MTI does not downcast checkin.attendee (it is a base
    # Attendee, so isinstance(attendee, Child) is always False); resolve the
    # concrete Child explicitly so child safety info is not silently dropped.
    from families.models import Child as ChildModel

    child = ChildModel.objects.filter(pk=attendee.pk).first()
    if child is not None:
        attendee_data = {
            "id": str(child.id),
            "first_name": child.first_name,
            "last_name": child.last_name,
            "birthdate": str(child.birthdate) if child.birthdate else None,
            "allergies": child.allergies or "",
            "notes": child.notes or "",
            "is_parent": False,
        }
    else:
        attendee_data = {
            "id": str(attendee.id),
            "first_name": attendee.first_name,
            "last_name": attendee.last_name,
            "birthdate": None,
            "allergies": "",
            "notes": "",
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
        entity_type="Child",
        entity_id=str(child.id),
        details={"qr_code": qr_code.code},
    )

    return Response(data)
