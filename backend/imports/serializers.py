from rest_framework import serializers

from .models import EventImportConfig, ImportRun


class EventImportConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventImportConfig
        fields = ["id", "event", "field_mappings", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


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
