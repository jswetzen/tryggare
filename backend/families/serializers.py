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
        ]
        read_only_fields = ["id", "qr_token", "last_participation_date"]


class FamilySerializer(serializers.ModelSerializer):
    parents = ParentSerializer(many=True, read_only=True)
    children = ChildSerializer(many=True, read_only=True)

    class Meta:
        model = Family
        fields = ["id", "last_participation_date", "parents", "children"]
        read_only_fields = ["id", "last_participation_date"]


class FamilyDetailSerializer(serializers.ModelSerializer):
    """Extended serializer with full nested data for detail views"""

    parents = ParentSerializer(many=True, read_only=True)
    children = ChildSerializer(many=True, read_only=True)

    class Meta:
        model = Family
        fields = ["id", "last_participation_date", "parents", "children"]
        read_only_fields = ["id", "last_participation_date"]


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
        fields = ["id", "parents", "children"]
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
