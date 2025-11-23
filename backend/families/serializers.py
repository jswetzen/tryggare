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
