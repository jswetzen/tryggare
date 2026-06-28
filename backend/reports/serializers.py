from rest_framework import serializers

from .models import EventReport


class EventReportListSerializer(serializers.ModelSerializer):
    generated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = EventReport
        fields = [
            "id",
            "event",
            "event_name",
            "event_start_date",
            "event_end_date",
            "generated_at",
            "generated_by_name",
            "unique_children",
            "total_checkins",
        ]
        read_only_fields = fields

    def get_generated_by_name(self, obj) -> str | None:
        if obj.generated_by is None:
            return None
        return obj.generated_by.name or obj.generated_by.username


class EventReportDetailSerializer(EventReportListSerializer):
    class Meta(EventReportListSerializer.Meta):
        fields = [*EventReportListSerializer.Meta.fields, "data"]
        read_only_fields = fields
