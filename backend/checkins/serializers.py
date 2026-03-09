from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import serializers

from families.serializers import ParentSerializer
from .models import AuditLog, CheckInRecord


class CheckInRecordSerializer(serializers.ModelSerializer):
    child_name = serializers.SerializerMethodField()
    session_name = serializers.CharField(source="session.name", read_only=True)
    check_in_staff_name = serializers.CharField(source="check_in_staff.name", read_only=True)
    check_out_staff_name = serializers.CharField(
        source="check_out_staff.name", read_only=True, allow_null=True
    )

    class Meta:
        model = CheckInRecord
        fields = [
            "id",
            "child",
            "child_name",
            "session",
            "session_name",
            "check_in_time",
            "check_out_time",
            "picked_up_by",
            "check_in_staff",
            "check_in_staff_name",
            "check_out_staff",
            "check_out_staff_name",
            "supervised",
        ]
        read_only_fields = ["id", "check_in_time"]

    def get_child_name(self, obj):
        return f"{obj.child.first_name} {obj.child.last_name}"

    def validate(self, data):
        """Validate one child in one session at a time rule with supervised check-in support"""
        child = data.get("child")
        session = data.get("session")

        if child and session:
            # Check for active check-in to SAME session
            same_session = CheckInRecord.objects.filter(
                child=child,
                session=session,
                check_out_time__isnull=True
            ).exclude(id=self.instance.id if self.instance else None)

            if same_session.exists():
                raise serializers.ValidationError(
                    _("This child is already checked in to this session.")
                )

            # Check for active check-ins to OTHER sessions
            other_sessions = CheckInRecord.objects.filter(
                child=child,
                check_out_time__isnull=True
            ).exclude(session=session).select_related('session')

            for record in other_sessions:
                # Standard check-ins always block
                if not record.supervised:
                    raise serializers.ValidationError(
                        _("Child has active check-in to another session.")
                    )

                # Supervised: only block if BOTH is_active AND end_time not passed
                if record.session.is_active and record.session.end_time > timezone.now():
                    raise serializers.ValidationError(
                        _("Child still in active supervised session.")
                    )

        return data


class PrintQueueSerializer(serializers.ModelSerializer):
    """Serializer for print queue - shows unprintable check-ins"""
    child_name = serializers.CharField(source='child.first_name', read_only=True)
    child_last_name = serializers.CharField(source='child.last_name', read_only=True)
    qr_code = serializers.SerializerMethodField()
    session_name = serializers.CharField(source='session.name', read_only=True)
    parents = ParentSerializer(source='child.family.parents', many=True, read_only=True)
    allergies = serializers.CharField(source='child.allergies', read_only=True)
    notes = serializers.CharField(source='child.notes', read_only=True)
    print_job = serializers.SerializerMethodField()

    class Meta:
        model = CheckInRecord
        fields = [
            'id',
            'child_name',
            'child_last_name',
            'qr_code',
            'session_name',
            'check_in_time',
            'parents',
            'allergies',
            'notes',
            'label_printed',
            'print_job',
        ]

    def get_qr_code(self, obj):
        """Get the QR code for this check-in record."""
        if hasattr(obj, 'qr_code') and obj.qr_code:
            return obj.qr_code.code
        return None

    def get_print_job(self, obj):
        """Get the most recent print job for this check-in, if any."""
        job = obj.print_jobs.select_related('printer').first()
        if not job:
            return None
        return {
            'id': str(job.id),
            'printer': str(job.printer.id) if job.printer else None,
            'printer_name': job.printer.name if job.printer else None,
            'status': job.status,
        }


class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.name", read_only=True)

    class Meta:
        model = AuditLog
        fields = ["id", "timestamp", "user", "user_name", "action", "entity_type", "entity_id", "details"]
        read_only_fields = ["id", "timestamp"]
