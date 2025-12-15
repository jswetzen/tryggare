from rest_framework import serializers

from .models import Child, Family, Parent


class ParentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parent
        fields = [
            "id",
            "name",
            "phone",
            "email",
            "relationship_type",
            "last_participation_date",
            "family",
        ]
        read_only_fields = ["id", "last_participation_date"]


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
            "last_participation_date",
            "family",
            "ticket_type",
            "ticket_details",
            "is_checked_in",
            "active_checkin_id",
        ]
        read_only_fields = ["id", "last_participation_date", "ticket_type", "ticket_details", "is_checked_in", "active_checkin_id"]

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
        if hasattr(obj, 'active_checkins'):
            return len(obj.active_checkins) > 0

        # Use prefetched checkin_records if available (Child viewset uses this)
        # This uses the standard relationship name and filters in Python
        if hasattr(obj, '_prefetched_objects_cache') and 'checkin_records' in obj._prefetched_objects_cache:
            checkin_records = obj.checkin_records.all()
            return any(record.check_out_time is None for record in checkin_records)

        # Fallback: query if not prefetched
        from checkins.models import CheckInRecord
        active_checkin = CheckInRecord.objects.filter(
            child=obj,
            check_out_time__isnull=True
        ).first()
        return active_checkin is not None

    def get_active_checkin_id(self, obj: Child) -> str | None:
        """
        Get the ID of the active check-in record if any.

        Returns:
            str: The check-in record ID, or None if not checked in
        """
        # Use prefetched active_checkins if available (Family viewset uses this)
        if hasattr(obj, 'active_checkins') and len(obj.active_checkins) > 0:
            return str(obj.active_checkins[0].id)

        # Use prefetched checkin_records if available (Child viewset uses this)
        # This uses the standard relationship name and filters in Python
        if hasattr(obj, '_prefetched_objects_cache') and 'checkin_records' in obj._prefetched_objects_cache:
            checkin_records = obj.checkin_records.all()
            for record in checkin_records:
                if record.check_out_time is None:
                    return str(record.id)
            return None

        # Fallback: query if not prefetched
        from checkins.models import CheckInRecord
        active_checkin = CheckInRecord.objects.filter(
            child=obj,
            check_out_time__isnull=True
        ).first()
        return str(active_checkin.id) if active_checkin else None


class FamilySerializer(serializers.ModelSerializer):
    parents = ParentSerializer(many=True, read_only=True)
    children = ChildSerializer(many=True, read_only=True)
    display_name = serializers.ReadOnlyField()

    class Meta:
        model = Family
        fields = ["id", "last_name", "last_participation_date", "parents", "children", "display_name"]
        read_only_fields = ["id", "last_participation_date", "display_name"]


class FamilyDetailSerializer(serializers.ModelSerializer):
    """Extended serializer with full nested data for detail views"""

    parents = ParentSerializer(many=True, read_only=True)
    children = ChildSerializer(many=True, read_only=True)
    display_name = serializers.ReadOnlyField()

    class Meta:
        model = Family
        fields = ["id", "last_name", "last_participation_date", "parents", "children", "display_name"]
        read_only_fields = ["id", "last_participation_date", "display_name"]


class ParentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating parents (without family field)"""
    class Meta:
        model = Parent
        fields = ["id", "name", "phone", "email", "relationship_type"]
        read_only_fields = ["id"]


class ChildCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating children (without family field)"""
    class Meta:
        model = Child
        fields = ["id", "first_name", "last_name", "birthdate", "allergies", "notes"]
        read_only_fields = ["id"]


class FamilyCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new family with nested parents and children"""

    parents = ParentCreateSerializer(many=True)
    children = ChildCreateSerializer(many=True)
    display_name = serializers.ReadOnlyField()

    class Meta:
        model = Family
        fields = ["id", "last_name", "parents", "children", "display_name"]
        read_only_fields = ["id", "display_name"]

    def validate_parents(self, value):
        """Ensure at least one parent is provided"""
        if not value:
            raise serializers.ValidationError("At least one parent is required")
        return value

    def validate_children(self, value):
        """Ensure at least one child is provided"""
        if not value:
            raise serializers.ValidationError("At least one child is required")
        return value

    def create(self, validated_data):
        """Create family with nested parents and children"""
        parents_data = validated_data.pop('parents')
        children_data = validated_data.pop('children')

        # Create the family
        family = Family.objects.create(**validated_data)

        # Create parents
        for parent_data in parents_data:
            Parent.objects.create(family=family, **parent_data)

        # Create children
        for child_data in children_data:
            Child.objects.create(family=family, **child_data)

        return family
