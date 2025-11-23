from django.contrib import admin

from .models import AuditLog, CheckInRecord


@admin.register(CheckInRecord)
class CheckInRecordAdmin(admin.ModelAdmin):
    list_display = ("child", "session", "check_in_time", "check_out_time")
    list_filter = ("session", "check_in_staff")
    search_fields = ("child__first_name", "child__last_name", "session__name")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "entity_type", "entity_id", "timestamp", "user")
    list_filter = ("action", "entity_type")
    search_fields = ("entity_id", "user__username")
