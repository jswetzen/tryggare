from django.contrib import admin

from config.admin import HiddenFromIndexAdmin

from .models import AuditLog, CheckInRecord


@admin.register(CheckInRecord)
class CheckInRecordAdmin(HiddenFromIndexAdmin, admin.ModelAdmin):
    """Machine-written by the check-in app; staff read check-ins in that app,
    not here. Hidden from the index, still reachable by URL for debugging."""

    list_display = ("attendee", "session", "check_in_time", "check_out_time")
    list_filter = ("session", "check_in_staff")
    search_fields = ("attendee__first_name", "attendee__last_name", "session__name")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "entity_type", "entity_id", "timestamp", "user")
    list_filter = ("action", "entity_type")
    search_fields = ("entity_id", "user__username")
