"""
Public QR code endpoint - does not require authentication
"""
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Child


@api_view(["GET"])
@permission_classes([AllowAny])
def qr_info(request, token):
    """
    Public endpoint to retrieve child information by QR token.
    Used by check-in kiosks to scan QR codes.

    Returns:
        - Child information (name, family, allergies, notes)
        - Current check-in status (if checked in, which session, etc.)
    """
    try:
        child = Child.objects.select_related("family").prefetch_related(
            "checkin_records__session"
        ).get(qr_token=token)
    except Child.DoesNotExist:
        return Response(
            {"error": _("Invalid QR code")},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Get current active check-in if any
    active_checkin = child.checkin_records.filter(check_out_time__isnull=True).select_related(
        "session"
    ).first()

    # Get parent names
    parents = child.family.parents.all()
    parent_names = [p.name for p in parents]

    data = {
        "id": str(child.id),
        "first_name": child.first_name,
        "last_name": child.last_name,
        "birthdate": child.birthdate,
        "allergies": child.allergies,
        "notes": child.notes,
        "family_id": str(child.family.id),
        "parent_names": parent_names,
        "is_checked_in": active_checkin is not None,
    }

    if active_checkin:
        data["current_session"] = {
            "id": str(active_checkin.session.id),
            "name": active_checkin.session.name,
            "check_in_time": active_checkin.check_in_time,
        }

    return Response(data)
