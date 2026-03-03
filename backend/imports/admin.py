from django.contrib import admin

from .models import EventImportConfig, ImportRun


@admin.register(EventImportConfig)
class EventImportConfigAdmin(admin.ModelAdmin):
    list_display = ["event", "created_at", "updated_at"]
    readonly_fields = ["id", "created_at", "updated_at"]
    search_fields = ["event__name"]


@admin.register(ImportRun)
class ImportRunAdmin(admin.ModelAdmin):
    list_display = ["config", "status", "triggered_by", "started_at", "finished_at", "source_file_name"]
    readonly_fields = ["id", "started_at", "finished_at", "log", "summary"]
    list_filter = ["status"]
    search_fields = ["config__event__name", "source_file_name"]
