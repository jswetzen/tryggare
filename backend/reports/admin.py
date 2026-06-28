from django.contrib import admin

from .models import EventReport


@admin.register(EventReport)
class EventReportAdmin(admin.ModelAdmin):
    list_display = (
        "event_name",
        "generated_at",
        "unique_children",
        "total_checkins",
        "generated_by",
    )
    list_filter = ("event",)
    search_fields = ("event_name",)
    date_hierarchy = "generated_at"
    readonly_fields = (
        "event",
        "event_name",
        "event_start_date",
        "event_end_date",
        "generated_at",
        "generated_by",
        "unique_children",
        "total_checkins",
        "data",
    )

    def has_add_permission(self, request) -> bool:
        # Reports are produced via the "Generate / refresh report" action on
        # Events or the generate_event_report command, not hand-created.
        return False
