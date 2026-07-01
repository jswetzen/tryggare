from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import Prefetch
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from families.models import Attendee, Parent
from events.models import Session

from .eligibility import parent_checkin_gate_error
from .audit import log_audit
from .models import AuditLog, CheckInRecord
from .serializers import (
    AuditLogSerializer,
    CheckInRecordSerializer,
    PrintQueueSerializer,
)


class CheckInRecordViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing check-in/check-out records.
    Requires authentication.
    """

    queryset = CheckInRecord.objects.select_related(
        "attendee", "session", "check_in_staff", "check_out_staff", "qr_code"
    ).all()
    serializer_class = CheckInRecordSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["attendee", "session", "check_in_staff", "check_out_staff"]
    ordering = ["-check_in_time"]

    @action(detail=False, methods=["post"])
    def check_in(self, request):
        """
        Check in an attendee (child or parent) to a session.
        Parents: check-in only (no label, no checkout coupling, no multi-session block).
        Children: full existing behaviour.
        """
        attendee_id = request.data.get("child") or request.data.get("attendee")
        session_id = request.data.get("session")
        supervised = request.data.get("supervised", False)

        if not attendee_id or not session_id:
            return Response(
                {"error": _("Both child and session are required")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            attendee = Attendee.objects.get(id=attendee_id)
            session = Session.objects.get(id=session_id)
        except (Attendee.DoesNotExist, Session.DoesNotExist):
            return Response(
                {"error": _("Child or session not found")},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Django MTI does not downcast automatically: Attendee.objects.get()
        # returns a base Attendee even when a Parent row exists, so a plain
        # isinstance(attendee, Parent) is always False. Resolve the concrete
        # Parent explicitly so parent-specific rules (ticket gate, no label, no
        # multi-session block) actually apply.
        parent = Parent.objects.filter(pk=attendee.pk).first()
        if parent is not None:
            attendee = parent
        is_parent = parent is not None

        if is_parent:
            # Parent check-in: gated by the session's parent_checkin_policy,
            # not a hardcoded ticket requirement. No multi-session blocking.
            gate_error = parent_checkin_gate_error(attendee, session)
            if gate_error:
                return Response(
                    {"error": gate_error}, status=status.HTTP_400_BAD_REQUEST
                )
            existing = CheckInRecord.objects.filter(
                attendee=attendee, session=session, check_out_time__isnull=True
            ).first()
            if existing:
                return Response(
                    {"error": _("Parent is already checked in to this session")},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            # Child check-in: enforce single-session rule
            existing = CheckInRecord.objects.filter(
                attendee=attendee, session=session, check_out_time__isnull=True
            ).first()
            if existing:
                return Response(
                    {"error": _("Child is already checked in to this session")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            other_sessions = (
                CheckInRecord.objects.filter(
                    attendee=attendee, check_out_time__isnull=True
                )
                .exclude(session=session)
                .select_related("session")
            )
            for record in other_sessions:
                if not record.supervised:
                    return Response(
                        {"error": _("Child has active check-in to another session")},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if (
                    record.session.is_active
                    and record.session.end_time > timezone.now()
                ):
                    return Response(
                        {"error": _("Child still in active supervised session")},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        # Create check-in record. Parents never get a label.
        record = CheckInRecord.objects.create(
            attendee=attendee,
            session=session,
            check_in_staff=request.user,
            label_printed=is_parent,  # mark as already "printed" so parent never enters print queue
            supervised=supervised,
        )

        # Allocate QR code for this check-in
        from .qr_utils import allocate_code_for_checkin

        qr_code = allocate_code_for_checkin(record)

        # Update last participation dates
        now = timezone.now()
        attendee.last_participation_date = now
        attendee.family.last_participation_date = now
        attendee.save()
        attendee.family.save()

        # Log the action
        log_audit(
            request,
            action="check_in",
            entity_type="CheckInRecord",
            entity_id=str(record.id),
            details={
                "child_id": str(attendee.id),
                "child_name": f"{attendee.first_name} {attendee.last_name}",
                "session_id": str(session.id),
                "session_name": session.name,
                "supervised": supervised,
                "is_parent": is_parent,
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
                    "child_id": str(attendee.id),
                    "child_name": attendee.first_name,
                    "child_last_name": attendee.last_name,
                    "session_id": str(session.id),
                    "session_name": session.name,
                    "check_in_time": record.check_in_time.isoformat(),
                    "qr_code": qr_code.code,
                    "supervised": supervised,
                    "is_parent": is_parent,
                    "allergies": getattr(attendee, "allergies", "") or "",
                    "notes": getattr(attendee, "notes", "") or "",
                    "parents": [
                        {
                            "id": str(p.id),
                            "name": p.name,
                            "phone": p.phone or "",
                            "email": p.email or "",
                            "relationship_type": p.relationship_type,
                        }
                        for p in attendee.family.parents.all()
                    ],
                },
            },
        )

        serializer = self.get_serializer(record)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def check_out(self, request, pk=None):
        """Check out a child from a session"""
        record = self.get_object()

        # Parents are check-in only (no label, no checkout — by design). See the
        # matching MTI-downcast note on check_in above for why pk lookup is needed.
        if Parent.objects.filter(pk=record.attendee_id).exists():
            return Response(
                {"error": _("Parents are check-in only and cannot be checked out")},
                status=status.HTTP_400_BAD_REQUEST,
            )

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

        # Release the QR code (starts 24h grace period)
        from .qr_utils import release_code_for_checkout

        release_code_for_checkout(record)

        # Log the action
        log_audit(
            request,
            action="check_out",
            entity_type="CheckInRecord",
            entity_id=str(record.id),
            details={
                "child_id": str(record.attendee.id),
                "child_name": f"{record.attendee.first_name} {record.attendee.last_name}",
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
                    "child_id": str(record.attendee.id),
                    "child_name": f"{record.attendee.first_name} {record.attendee.last_name}",
                    "session_id": str(record.session.id),
                    "session_name": record.session.name,
                    "check_out_time": record.check_out_time.isoformat(),
                    "picked_up_by": picked_up_by,
                },
            },
        )

        serializer = self.get_serializer(record)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def undo_checkout(self, request, pk=None):
        """Undo a recent check-out (within 5 minutes)"""
        from datetime import timedelta

        record = self.get_object()

        if not record.check_out_time:
            return Response(
                {"error": _("Child is not checked out")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if check-out was within the last 5 minutes
        time_since_checkout = timezone.now() - record.check_out_time
        if time_since_checkout > timedelta(minutes=5):
            return Response(
                {"error": _("Cannot undo - too much time has passed (max 5 minutes)")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Undo the check-out
        record.check_out_time = None
        record.check_out_staff = None
        record.picked_up_by = ""
        record.save()

        # Re-activate the QR code if it exists
        if hasattr(record, "qr_code") and record.qr_code:
            record.qr_code.released_at = None
            record.qr_code.save()

        # Log the action
        log_audit(
            request,
            action="undo_checkout",
            entity_type="CheckInRecord",
            entity_id=str(record.id),
            details={
                "child_id": str(record.attendee.id),
                "child_name": f"{record.attendee.first_name} {record.attendee.last_name}",
                "session_id": str(record.session.id),
                "session_name": record.session.name,
            },
        )

        # Broadcast undo event via WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "checkins_broadcast",
            {
                "type": "checkout_undone",
                "data": {
                    "record_id": str(record.id),
                    "child_id": str(record.attendee.id),
                    "child_name": f"{record.attendee.first_name} {record.attendee.last_name}",
                    "session_id": str(record.session.id),
                    "session_name": record.session.name,
                },
            },
        )

        serializer = self.get_serializer(record)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def undo(self, request, pk=None):
        """
        Undo a recent check-in (within 5 minutes).
        Deletes the check-in record if it's still active (not checked out)
        and was created within the allowed time window.
        """
        from datetime import timedelta

        record = self.get_object()

        # Validate that child hasn't been checked out yet
        if record.check_out_time is not None:
            return Response(
                {"error": _("Cannot undo: child already checked out")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate time window (5 minutes = 300 seconds)
        time_elapsed = timezone.now() - record.check_in_time
        if time_elapsed > timedelta(minutes=5):
            return Response(
                {"error": _("Cannot undo: check-in was more than 5 minutes ago")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Store details before deletion for logging and broadcasting
        child_id = str(record.attendee.id)
        child_name = f"{record.attendee.first_name} {record.attendee.last_name}"
        session_id = str(record.session.id)
        session_name = record.session.name
        record_id = str(record.id)

        # Log the action before deleting the record
        log_audit(
            request,
            action="undo_checkin",
            entity_type="CheckInRecord",
            entity_id=record_id,
            details={
                "child_id": child_id,
                "child_name": child_name,
                "session_id": session_id,
                "session_name": session_name,
            },
        )

        # Delete the check-in record
        record.delete()

        # Broadcast undo check-in event via WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "checkins_broadcast",
            {
                "type": "checkin_undone",
                "data": {
                    "record_id": record_id,
                    "child_id": child_id,
                    "child_name": child_name,
                    "session_id": session_id,
                    "session_name": session_name,
                },
            },
        )

        return Response(
            {"success": True, "message": _("Check-in successfully undone")},
            status=status.HTTP_200_OK,
        )

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


class PrintQueueViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for managing label print queue.
    Shows all checked-in children who need labels printed.
    """

    serializer_class = PrintQueueSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Get all unprintable check-ins (checked in, not printed, not checked out).

        For supervised check-ins, only the is_active flag matters - administrators
        have full control to keep printing labels as long as the session is marked
        active, regardless of the scheduled end_time.
        """
        from django.db import models as db_models

        from families.models import Parent as ParentModel

        # Exclude parent attendees — parents are check-in only, never get labels
        parent_ids = ParentModel.objects.values_list("attendee_ptr_id", flat=True)

        return (
            CheckInRecord.objects.filter(
                label_printed=False,
                check_out_time__isnull=True,
            )
            .exclude(attendee_id__in=parent_ids)
            .filter(
                # Standard check-ins (not supervised) OR supervised in active session
                db_models.Q(supervised=False)
                | db_models.Q(supervised=True, session__is_active=True)
            )
            .select_related(
                "attendee", "attendee__family", "session", "check_in_staff", "qr_code"
            )
            .prefetch_related(
                Prefetch(
                    "attendee__family__attendees",
                    queryset=Parent.objects.all(),
                    to_attr="parents",
                ),
                "print_jobs__printer",
            )
            .order_by("-check_in_time")
        )

    @action(detail=False, methods=["post"])
    def mark_printed(self, request):
        """Mark one or more check-ins as printed"""
        checkin_ids = request.data.get("checkin_ids", [])

        if not checkin_ids:
            return Response(
                {"error": _("No check-in IDs provided")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update records
        updated = CheckInRecord.objects.filter(
            id__in=checkin_ids,
            check_out_time__isnull=True,  # Only if still checked in
        ).update(
            label_printed=True,
            label_printed_at=timezone.now(),
            label_printed_by=request.user,
        )

        # Log the action
        for checkin_id in checkin_ids[:updated]:  # Only log actually updated records
            try:
                record = CheckInRecord.objects.get(id=checkin_id)
                log_audit(
                    request,
                    action="label_printed",
                    entity_type="CheckInRecord",
                    entity_id=str(checkin_id),
                    details={
                        "child_id": str(record.attendee.id),
                        "child_name": f"{record.attendee.first_name} {record.attendee.last_name}",
                        "session_id": str(record.session.id),
                        "session_name": record.session.name,
                    },
                )
            except CheckInRecord.DoesNotExist:
                pass

        return Response(
            {"message": _(f"{updated} labels marked as printed"), "count": updated}
        )

    @action(detail=True, methods=["get"])
    def print_page(self, request, pk=None):
        """
        Returns HTML page optimized for printing a single label on Brother QL-54.3mm.
        Opens in browser for direct printing.
        """
        from django.shortcuts import render, get_object_or_404
        import qrcode
        import io
        import base64

        checkin = get_object_or_404(
            CheckInRecord.objects.select_related("attendee", "session", "qr_code"),
            pk=pk,
        )

        # Get the QR code string
        qr_code_str = (
            checkin.qr_code.code
            if hasattr(checkin, "qr_code") and checkin.qr_code
            else "INVALID"
        )

        # Generate QR code as base64 data URL
        # Use Level L (7% error correction) for minimal complexity
        # Labels are printed in controlled environment, high redundancy not needed
        qr = qrcode.QRCode(
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=1,
        )
        qr.add_data(f"http://{request.get_host()}/qr/{qr_code_str}")
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        qr_data_url = (
            f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
        )

        from printing.views import LABEL_DIMENSIONS, DEFAULT_LABEL_DIMENSIONS

        label = request.GET.get("label", "")
        dims = LABEL_DIMENSIONS.get(label, DEFAULT_LABEL_DIMENSIONS)

        return render(
            request,
            "print_label.html",
            {
                "checkin": checkin,
                "qr_url": qr_data_url,
                "w_mm": dims["w_mm"],
                "h_mm": dims["h_mm"],
            },
        )

    @action(detail=True, methods=["post"])
    def mark_single_printed(self, request, pk=None):
        """
        Mark a single check-in as printed.
        Creates audit log entry.
        """
        from django.shortcuts import get_object_or_404

        checkin = get_object_or_404(
            CheckInRecord.objects.select_related("attendee", "session"),
            pk=pk,
            check_out_time__isnull=True,  # Only if still checked in
        )

        # Update record
        checkin.label_printed = True
        checkin.label_printed_at = timezone.now()
        checkin.label_printed_by = request.user
        checkin.save()

        # Log the action
        log_audit(
            request,
            action="label_printed",
            entity_type="CheckInRecord",
            entity_id=str(checkin.id),
            details={
                "child_id": str(checkin.attendee.id),
                "child_name": f"{checkin.attendee.first_name} {checkin.attendee.last_name}",
                "session_id": str(checkin.session.id),
                "session_name": checkin.session.name,
            },
        )

        serializer = self.get_serializer(checkin)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def recently_printed(self, request):
        """
        Get recently printed labels (last 50).
        Shows only checked-in (not checked out) records.
        """
        from django.db import models as db_models

        recent = (
            CheckInRecord.objects.filter(
                label_printed=True,
                check_out_time__isnull=True,  # Still checked in
            )
            .filter(
                # Standard check-ins (not supervised) OR supervised in active session
                db_models.Q(supervised=False)
                | db_models.Q(
                    supervised=True,
                    session__is_active=True,
                    session__end_time__gt=timezone.now(),
                )
            )
            .select_related(
                "attendee", "attendee__family", "session", "check_in_staff", "qr_code"
            )
            .prefetch_related(
                Prefetch(
                    "attendee__family__attendees",
                    queryset=Parent.objects.all(),
                    to_attr="parents",
                )
            )
            .order_by("-check_in_time")[:50]
        )

        serializer = self.get_serializer(recent, many=True)
        return Response(serializer.data)
