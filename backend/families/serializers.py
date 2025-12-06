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

    class Meta:
        model = Child
        fields = [
            "id",
            "first_name",
            "last_name",
            "birthdate",
            "allergies",
            "notes",
            "qr_token",
            "last_participation_date",
            "family",
            "ticket_type",
            "ticket_details",
        ]
        read_only_fields = ["id", "qr_token", "last_participation_date", "ticket_type", "ticket_details"]

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
        fields = ["name", "phone", "email", "relationship_type"]


class ChildCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating children (without family field)"""
    class Meta:
        model = Child
        fields = ["first_name", "last_name", "birthdate", "allergies", "notes"]


class FamilyCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new family with nested parents and children"""

    parents = ParentCreateSerializer(many=True)
    children = ChildCreateSerializer(many=True)

    class Meta:
        model = Family
        fields = ["id", "last_name", "parents", "children"]
        read_only_fields = ["id"]

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
