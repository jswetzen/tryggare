from rest_framework import serializers

from .models import EventImportConfig, ImportProvider, ImportRun


class ImportProviderSerializer(serializers.ModelSerializer):
    username = serializers.CharField(write_only=True, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    has_credentials = serializers.BooleanField(read_only=True)

    class Meta:
        model = ImportProvider
        fields = [
            "id",
            "name",
            "login_url",
            "export_url",
            "export_body",
            "has_credentials",
            "username",
            "password",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "has_credentials", "created_at", "updated_at"]

    def create(self, validated_data):
        username = validated_data.pop("username", "")
        password = validated_data.pop("password", "")
        provider = ImportProvider(**validated_data)
        if username or password:
            from .encryption import encrypt_credentials
            provider.credentials = encrypt_credentials(username, password)
        provider.save()
        return provider

    def update(self, instance, validated_data):
        username = validated_data.pop("username", None)
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        # Only update credentials if both fields explicitly provided
        if username is not None and password is not None:
            from .encryption import encrypt_credentials
            instance.credentials = encrypt_credentials(username, password)
        instance.save()
        return instance


class EventImportConfigSerializer(serializers.ModelSerializer):
    provider_id = serializers.UUIDField(
        source="provider.id", read_only=True, allow_null=True, default=None
    )
    provider_name = serializers.CharField(
        source="provider.name", read_only=True, allow_null=True, default=None
    )

    class Meta:
        model = EventImportConfig
        fields = [
            "id",
            "event",
            "field_mappings",
            "provider_id",
            "provider_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "provider_id", "provider_name", "created_at", "updated_at"]


class ImportRunListSerializer(serializers.ModelSerializer):
    triggered_by_name = serializers.CharField(
        source="triggered_by.username", read_only=True, default=None
    )

    class Meta:
        model = ImportRun
        fields = [
            "id",
            "config",
            "triggered_by",
            "triggered_by_name",
            "status",
            "started_at",
            "finished_at",
            "source_file_name",
            "summary",
        ]
        read_only_fields = fields


class ImportRunSerializer(ImportRunListSerializer):
    """Full detail including per-booking log entries."""

    class Meta(ImportRunListSerializer.Meta):
        fields = ImportRunListSerializer.Meta.fields + ["log"]
        read_only_fields = fields
