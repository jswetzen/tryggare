from django.contrib import admin

from .models import FestivalProImportSource, ImportRun, ImportSource


@admin.register(ImportSource)
class ImportSourceAdmin(admin.ModelAdmin):
    list_display = ["name", "provider_type", "event", "has_credentials", "created_at", "updated_at"]
    readonly_fields = ["id", "created_at", "updated_at"]
    search_fields = ["name", "event__name"]
    list_filter = ["provider_type"]


@admin.register(FestivalProImportSource)
class FestivalProImportSourceAdmin(admin.ModelAdmin):
    list_display = ["source", "login_url", "export_url"]
    readonly_fields = ["id"]
    search_fields = ["source__name"]


@admin.register(ImportRun)
class ImportRunAdmin(admin.ModelAdmin):
    list_display = ["source", "status", "triggered_by", "started_at", "finished_at", "source_file_name"]
    readonly_fields = ["id", "started_at", "finished_at", "log", "summary"]
    list_filter = ["status"]
    search_fields = ["source__name", "source_file_name"]
