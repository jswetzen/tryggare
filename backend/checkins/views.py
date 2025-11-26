import uuid
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from families.models import Child
from events.models import Session

from .models import AuditLog, CheckInRecord
from .serializers import AuditLogSerializer, CheckInRecordSerializer


class CheckInRecordViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing check-in/check-out records.
    Requires authentication.
    """

    queryset = CheckInRecord.objects.select_related(
        "child", "session", "check_in_staff", "check_out_staff"
    ).all()
    serializer_class = CheckInRecordSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["child", "session", "check_in_staff", "check_out_staff"]
    ordering = ["-check_in_time"]

    @action(detail=False, methods=["post"])
    def check_in(self, request):
        """
        Check in a child to a session.
        Generates QR token if not already present.
        """
        # Debug CSRF
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"CSRF Debug - Headers: {dict(request.headers)}")
        logger.warning(f"CSRF Debug - Cookies: {request.COOKIES}")
        logger.warning(f"CSRF Debug - User: {request.user}, Authenticated: {request.user.is_authenticated}")

        child_id = request.data.get("child")
        session_id = request.data.get("session")

        if not child_id or not session_id:
            return Response(
                {"error": _("Both child and session are required")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            child = Child.objects.get(id=child_id)
            session = Session.objects.get(id=session_id)
        except (Child.DoesNotExist, Session.DoesNotExist):
            return Response(
                {"error": _("Child or session not found")},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if child is already checked in
        existing = CheckInRecord.objects.filter(
            child=child, session=session, check_out_time__isnull=True
        ).first()

        if existing:
            return Response(
                {"error": _("Child is already checked in to this session")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate QR token if needed
        if not child.qr_token:
            child.qr_token = str(uuid.uuid4())
            child.save()

        # Create check-in record
        record = CheckInRecord.objects.create(
            child=child, session=session, check_in_staff=request.user
        )

        # Update last participation dates
        now = timezone.now()
        child.last_participation_date = now
        child.family.last_participation_date = now
        child.save()
        child.family.save()

        # Log the action
        AuditLog.objects.create(
            user=request.user,
            action="check_in",
            entity_type="CheckInRecord",
            entity_id=str(record.id),
            details={
                "child_id": str(child.id),
                "child_name": f"{child.first_name} {child.last_name}",
                "session_id": str(session.id),
                "session_name": session.name,
            },
        )

        # Broadcast check-in event via WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "checkins_broadcast",
            {
                "type": "child_checked_in",
                "data": {
                    "record_id": str(record.id),
                    "child_id": str(child.id),
                    "child_name": f"{child.first_name} {child.last_name}",
                    "session_id": str(session.id),
                    "session_name": session.name,
                    "check_in_time": record.check_in_time.isoformat(),
                    "qr_token": child.qr_token,
                }
            }
        )

        serializer = self.get_serializer(record)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def check_out(self, request, pk=None):
        """Check out a child from a session"""
        record = self.get_object()

        if record.check_out_time:
            return Response(
                {"error": _("Child is already checked out")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        picked_up_by = request.data.get("picked_up_by", "")

        record.check_out_time = timezone.now()
        record.check_out_staff = request.user
        record.picked_up_by = picked_up_by
        record.save()

        # Log the action
        AuditLog.objects.create(
            user=request.user,
            action="check_out",
            entity_type="CheckInRecord",
            entity_id=str(record.id),
            details={
                "child_id": str(record.child.id),
                "child_name": f"{record.child.first_name} {record.child.last_name}",
                "session_id": str(record.session.id),
                "session_name": record.session.name,
                "picked_up_by": picked_up_by,
            },
        )

        # Broadcast check-out event via WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "checkins_broadcast",
            {
                "type": "child_checked_out",
                "data": {
                    "record_id": str(record.id),
                    "child_id": str(record.child.id),
                    "child_name": f"{record.child.first_name} {record.child.last_name}",
                    "session_id": str(record.session.id),
                    "session_name": record.session.name,
                    "check_out_time": record.check_out_time.isoformat(),
                    "picked_up_by": picked_up_by,
                }
            }
        )

        serializer = self.get_serializer(record)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def active(self, request):
        """Get all active check-ins (not checked out yet)"""
        active_records = self.get_queryset().filter(check_out_time__isnull=True)
        serializer = self.get_serializer(active_records, many=True)
        return Response(serializer.data)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing audit logs.
    Read-only - logs cannot be modified.
    """

    queryset = AuditLog.objects.select_related("user").all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["user", "action", "entity_type"]
    ordering = ["-timestamp"]
