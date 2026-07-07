from rest_framework import serializers

from .models import Child, Family, Parent
from .services import create_family_with_members


class ParentSerializer(serializers.ModelSerializer):
    name = serializers.ReadOnlyField()
    ticket_type = serializers.SerializerMethodField()
    ticket_details = serializers.SerializerMethodField()
    is_checked_in = serializers.SerializerMethodField()
    active_checkin_id = serializers.SerializerMethodField()

    class Meta:
        model = Parent
        fields = [
            "id",
            "first_name",
            "last_name",
            "name",
            "phone",
            "email",
            "relationship_type",
            "last_participation_date",
            "family",
            "ticket_type",
            "ticket_details",
            "is_checked_in",
            "active_checkin_id",
        ]
        read_only_fields = [
            "id",
            "name",
            "last_participation_date",
            "ticket_type",
            "ticket_details",
            "is_checked_in",
            "active_checkin_id",
        ]

    def get_ticket_type(self, obj: Parent) -> str | None:
        t = obj.get_ticket_type()
        return t if t != "none" else None

    def get_ticket_details(self, obj: Parent) -> dict | None:
        if not obj.has_ticket:
            return None
        return obj.get_ticket_details()

    def get_is_checked_in(self, obj: Parent) -> bool:
        if hasattr(obj, "active_checkins"):
            return len(obj.active_checkins) > 0
        from checkins.models import CheckInRecord

        return CheckInRecord.objects.filter(
            attendee=obj, check_out_time__isnull=True
        ).exists()

    def get_active_checkin_id(self, obj: Parent) -> str | None:
        if hasattr(obj, "active_checkins"):
            return str(obj.active_checkins[0].id) if obj.active_checkins else None
        from checkins.models import CheckInRecord

        record = CheckInRecord.objects.filter(
            attendee=obj, check_out_time__isnull=True
        ).first()
        return str(record.id) if record else None


class ChildSerializer(serializers.ModelSerializer):
    ticket_type = serializers.SerializerMethodField()
    ticket_details = serializers.SerializerMethodField()
    is_checked_in = serializers.SerializerMethodField()
    active_checkin_id = serializers.SerializerMethodField()

    class Meta:
        model = Child
        fields = [
            "id",
            "first_name",
            "last_name",
            "birthdate",
            "allergies",
            "notes",
            "health_consent_status",
            "health_consent_by",
            "health_consent_at",
            "health_consent_notice_version",
            "last_participation_date",
            "family",
            "ticket_type",
            "ticket_details",
            "is_checked_in",
            "active_checkin_id",
        ]
        read_only_fields = [
            "id",
            "health_consent_status",
            "health_consent_by",
            "health_consent_at",
            "health_consent_notice_version",
            "last_participation_date",
            "ticket_type",
            "ticket_details",
            "is_checked_in",
            "active_checkin_id",
        ]

    def get_ticket_type(self, obj: Child) -> str:
        """
        Get the type of ticket the child has.

        Returns:
            str: 'event', 'session', or 'none'
        """
        return obj.get_ticket_type()

    def get_ticket_details(self, obj: Child) -> dict:
        """
        Get detailed information about the child's tickets.

        Returns:
            dict: Ticket details including event_tickets and session_tickets lists
        """
        return obj.get_ticket_details()

    def get_is_checked_in(self, obj: Child) -> bool:
        """
        Check if the child has an active check-in (not checked out).

        Returns:
            bool: True if child has an active check-in, False otherwise
        """
        # Use prefetched active_checkins if available (Family viewset uses this)
        if hasattr(obj, "active_checkins"):
            return len(obj.active_checkins) > 0

        # Use prefetched checkin_records if available (Child viewset uses this)
        # This uses the standard relationship name and filters in Python
        if (
            hasattr(obj, "_prefetched_objects_cache")
            and "checkin_records" in obj._prefetched_objects_cache
        ):
            checkin_records = obj.checkin_records.all()
            return any(record.check_out_time is None for record in checkin_records)

        # Fallback: query if not prefetched
        from checkins.models import CheckInRecord

        active_checkin = CheckInRecord.objects.filter(
            attendee=obj, check_out_time__isnull=True
        ).first()
        return active_checkin is not None

    def get_active_checkin_id(self, obj: Child) -> str | None:
        """
        Get the ID of the active check-in record if any.

        Returns:
            str: The check-in record ID, or None if not checked in
        """
        # Use prefetched active_checkins if available (Family viewset uses this)
        if hasattr(obj, "active_checkins") and len(obj.active_checkins) > 0:
            return str(obj.active_checkins[0].id)

        # Use prefetched checkin_records if available (Child viewset uses this)
        # This uses the standard relationship name and filters in Python
        if (
            hasattr(obj, "_prefetched_objects_cache")
            and "checkin_records" in obj._prefetched_objects_cache
        ):
            checkin_records = obj.checkin_records.all()
            for record in checkin_records:
                if record.check_out_time is None:
                    return str(record.id)
            return None

        # Fallback: query if not prefetched
        from checkins.models import CheckInRecord

        active_checkin = CheckInRecord.objects.filter(
            attendee=obj, check_out_time__isnull=True
        ).first()
        return str(active_checkin.id) if active_checkin else None


class FamilySerializer(serializers.ModelSerializer):
    parents = ParentSerializer(many=True, read_only=True)
    children = ChildSerializer(many=True, read_only=True)
    display_name = serializers.ReadOnlyField()

    class Meta:
        model = Family
        fields = [
            "id",
            "last_name",
            "last_participation_date",
            "parents",
            "children",
            "display_name",
            "external_booking_id",
        ]
        read_only_fields = [
            "id",
            "last_participation_date",
            "display_name",
            "external_booking_id",
        ]


class FamilyDetailSerializer(serializers.ModelSerializer):
    """Extended serializer with full nested data for detail views"""

    parents = ParentSerializer(many=True, read_only=True)
    children = ChildSerializer(many=True, read_only=True)
    display_name = serializers.ReadOnlyField()

    class Meta:
        model = Family
        fields = [
            "id",
            "last_name",
            "last_participation_date",
            "parents",
            "children",
            "display_name",
            "external_booking_id",
        ]
        read_only_fields = [
            "id",
            "last_participation_date",
            "display_name",
            "external_booking_id",
        ]


class ParentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating parents (without family field)"""

    class Meta:
        model = Parent
        fields = [
            "id",
            "first_name",
            "last_name",
            "phone",
            "email",
            "relationship_type",
        ]
        read_only_fields = ["id"]


class ChildCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating children (without family field)"""

    health_consent_status = serializers.ChoiceField(
        choices=[
            Child.HealthConsentStatus.NOT_APPLICABLE,
            Child.HealthConsentStatus.GRANTED,
            Child.HealthConsentStatus.DECLINED,
        ],
        default=Child.HealthConsentStatus.NOT_APPLICABLE,
    )

    class Meta:
        model = Child
        fields = [
            "id",
            "first_name",
            "last_name",
            "birthdate",
            "allergies",
            "notes",
            "health_consent_status",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        """
        Health text is only ever stored once consent is granted — a
        declined/undecided status must not carry allergy/medical text even
        if the client sent some (enforced server-side, not just trusted from
        the UI).
        """
        status = attrs.get(
            "health_consent_status", Child.HealthConsentStatus.NOT_APPLICABLE
        )
        if status != Child.HealthConsentStatus.GRANTED:
            attrs["allergies"] = None
            attrs["notes"] = None
        return attrs


class FamilyCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new family with nested parents and children"""

    parents = ParentCreateSerializer(many=True)
    children = ChildCreateSerializer(many=True)
    display_name = serializers.ReadOnlyField()

    class Meta:
        model = Family
        fields = ["id", "last_name", "parents", "children", "display_name"]
        read_only_fields = ["id", "display_name"]

    def validate(self, data):
        """A family is a household of attendees — it can be all-parents,
        all-children, or mixed, but not empty."""
        if not data.get("parents") and not data.get("children"):
            raise serializers.ValidationError(
                "A family needs at least one parent or child"
            )
        return data

    def create(self, validated_data):
        """Create family with nested parents and children.

        Whoever is present at registration attests to the health-data consent
        decision — see create_family_with_members's docstring for why "first
        parent listed" is the right default here specifically (no separate
        attestor picker in the staff UI).
        """
        return create_family_with_members(
            last_name=validated_data.get("last_name", ""),
            parents_data=validated_data.pop("parents"),
            children_data=validated_data.pop("children"),
        )
