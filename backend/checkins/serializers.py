from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import serializers

from families.models import Parent
from families.serializers import ParentSerializer
from .eligibility import parent_checkin_gate_error, registration_checkin_gate_error
from .models import AuditLog, CheckInRecord


class CheckInRecordSerializer(serializers.ModelSerializer):
    # Keep JSON key "child" for frontend back-compat; reads/writes attendee FK.
    child = serializers.PrimaryKeyRelatedField(
        source="attendee",
        queryset=CheckInRecord._meta.get_field("attendee").related_model.objects.all(),
    )
    child_name = serializers.SerializerMethodField()
    session_name = serializers.CharField(source="session.name", read_only=True)
    check_in_staff_name = serializers.CharField(
        source="check_in_staff.name", read_only=True
    )
    check_out_staff_name = serializers.CharField(
        source="check_out_staff.name", read_only=True, allow_null=True
    )
    qr_code = serializers.SerializerMethodField()

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
            "qr_code",
        ]
        read_only_fields = ["id", "check_in_time"]

    def get_child_name(self, obj):
        return f"{obj.attendee.first_name} {obj.attendee.last_name}"

    def get_qr_code(self, obj):
        """The short QR code for the active check-in, if one is allocated.

        Lets staff open the child's info page (/qr/<code>) when a name tag is
        lost without needing the physical label.
        """
        qr = getattr(obj, "qr_code", None)
        return qr.code if qr else None

    def validate(self, data):
        """Validate one child in one session at a time rule with supervised check-in support"""
        attendee = data.get("attendee")
        session = data.get("session")

        # Django MTI does not downcast, so isinstance(attendee, Parent) is
        # always False here (the PK field resolves to a base Attendee); query
        # the Parent table directly instead.
        parent = Parent.objects.filter(pk=attendee.pk).first() if attendee else None

        if attendee and session:
            # Same gate the check_in view action enforces (checked before
            # branching on parent-vs-child there too), kept here so a plain
            # POST to the generic CheckInRecord endpoint can't bypass it for
            # a child whose registration isn't confirmed yet.
            registration_gate_error = registration_checkin_gate_error(attendee, session)
            if registration_gate_error:
                raise serializers.ValidationError(registration_gate_error)

        if parent is not None:
            # Parents are check-in only — skip multi-session validation, but
            # are still gated by the session's parent_checkin_policy (same
            # gate the check_in view enforces, kept here too so the generic
            # CheckInRecord create/update endpoint can't bypass it).
            if session:
                gate_error = parent_checkin_gate_error(parent, session)
                if gate_error:
                    raise serializers.ValidationError(gate_error)
            return data

        if attendee and session:
            # Check for active check-in to SAME session
            same_session = CheckInRecord.objects.filter(
                attendee=attendee, session=session, check_out_time__isnull=True
            ).exclude(id=self.instance.id if self.instance else None)

            if same_session.exists():
                raise serializers.ValidationError(
                    _("This child is already checked in to this session.")
                )

            # Check for active check-ins to OTHER sessions
            other_sessions = (
                CheckInRecord.objects.filter(
                    attendee=attendee, check_out_time__isnull=True
                )
                .exclude(session=session)
                .select_related("session")
            )

            for record in other_sessions:
                # Standard check-ins always block
                if not record.supervised:
                    raise serializers.ValidationError(
                        _("Child has active check-in to another session.")
                    )

                # Supervised: only block if BOTH is_active AND end_time not passed
                if (
                    record.session.is_active
                    and record.session.end_time > timezone.now()
                ):
                    raise serializers.ValidationError(
                        _("Child still in active supervised session.")
                    )

        return data


class PrintQueueSerializer(serializers.ModelSerializer):
    """Serializer for print queue - shows unprintable check-ins for children only"""

    child_name = serializers.SerializerMethodField()
    child_last_name = serializers.SerializerMethodField()
    qr_code = serializers.SerializerMethodField()
    session_name = serializers.CharField(source="session.name", read_only=True)
    parents = ParentSerializer(
        source="attendee.family.parents", many=True, read_only=True
    )
    allergies = serializers.SerializerMethodField()
    notes = serializers.SerializerMethodField()
    print_job = serializers.SerializerMethodField()

    def get_child_name(self, obj):
        return obj.attendee.first_name

    def get_child_last_name(self, obj):
        return obj.attendee.last_name

    def get_allergies(self, obj):
        return getattr(obj.attendee, "allergies", None)

    def get_notes(self, obj):
        return getattr(obj.attendee, "notes", None)

    class Meta:
        model = CheckInRecord
        fields = [
            "id",
            "child_name",
            "child_last_name",
            "qr_code",
            "session_name",
            "check_in_time",
            "parents",
            "allergies",
            "notes",
            "label_printed",
            "print_job",
        ]

    def get_qr_code(self, obj):
        """Get the QR code for this check-in record."""
        if hasattr(obj, "qr_code") and obj.qr_code:
            return obj.qr_code.code
        return None

    def get_print_job(self, obj):
        """Get the most recent print job for this check-in, if any."""
        job = obj.print_jobs.select_related("printer").first()
        if not job:
            return None
        return {
            "id": str(job.id),
            "printer": str(job.printer.id) if job.printer else None,
            "printer_name": job.printer.name if job.printer else None,
            "status": job.status,
        }


class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "timestamp",
            "user",
            "user_name",
            "action",
            "entity_type",
            "entity_id",
            "details",
            "source_ip",
            "session_id",
        ]
        read_only_fields = ["id", "timestamp"]

    def get_user_name(self, obj):
        return obj.user.name if obj.user else None
