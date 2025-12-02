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
        ]
        read_only_fields = ["id", "check_in_time"]

    def get_child_name(self, obj):
        return f"{obj.child.first_name} {obj.child.last_name}"

    def validate(self, data):
        """Validate one child in one session at a time rule"""
        child = data.get("child")
        session = data.get("session")

        if child and session:
            # Check if child already has an active check-in for this session
            active_checkin = CheckInRecord.objects.filter(
                child=child, session=session, check_out_time__isnull=True
            ).exclude(id=self.instance.id if self.instance else None)

            if active_checkin.exists():
                raise serializers.ValidationError(
                    _("This child is already checked in to this session.")
                )

        return data


class PrintQueueSerializer(serializers.ModelSerializer):
    """Serializer for print queue - shows unprintable check-ins"""
    child_name = serializers.CharField(source='child.first_name', read_only=True)
    child_last_name = serializers.CharField(source='child.last_name', read_only=True)
    qr_token = serializers.CharField(source='child.qr_token', read_only=True)
    session_name = serializers.CharField(source='session.name', read_only=True)
    parents = ParentSerializer(source='child.family.parents', many=True, read_only=True)
    allergies = serializers.CharField(source='child.allergies', read_only=True)
    notes = serializers.CharField(source='child.notes', read_only=True)

    class Meta:
        model = CheckInRecord
        fields = [
            'id',
            'child_name',
            'child_last_name',
            'qr_token',
            'session_name',
            'check_in_time',
            'parents',
            'allergies',
            'notes',
            'label_printed',
        ]


class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.name", read_only=True)

    class Meta:
        model = AuditLog
        fields = ["id", "timestamp", "user", "user_name", "action", "entity_type", "entity_id", "details"]
        read_only_fields = ["id", "timestamp"]
