from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from config.admin import HiddenFromIndexAdmin

from .models import FestivalProImportSource, ImportRun, ImportSource


class FestivalProImportSourceInline(admin.StackedInline):
    """The navigable home of the FestivalPro login/export URLs.

    FestivalProImportSourceAdmin is hidden from the index (its rows are
    meaningless away from their ImportSource), so without this inline the
    only way to edit those URLs would be to type an admin URL by hand.
    """

    model = FestivalProImportSource
    max_num = 1
    extra = 0
    readonly_fields = ["id"]
    verbose_name = _("FestivalPro Configuration")
    verbose_name_plural = _("FestivalPro Configuration")

    def get_extra(self, request, obj=None, **kwargs):
        # Offer a blank form only where one belongs: a FestivalPro source
        # that has no config yet. A Planning Center source gets nothing.
        if obj is None:
            return 0
        if obj.provider_type != ImportSource.PROVIDER_FESTIVALPRO:
            return 0
        return 0 if hasattr(obj, "festivalpro_config") else 1


@admin.register(ImportSource)
class ImportSourceAdmin(admin.ModelAdmin):
    inlines = [FestivalProImportSourceInline]
    list_display = [
        "name",
        "provider_type",
        "event",
        "has_credentials",
        "created_at",
        "updated_at",
    ]
    readonly_fields = ["id", "created_at", "updated_at"]
    search_fields = ["name", "event__name"]
    list_filter = ["provider_type"]


@admin.register(FestivalProImportSource)
class FestivalProImportSourceAdmin(HiddenFromIndexAdmin, admin.ModelAdmin):
    """A one-to-one settings row hanging off an ImportSource, meaningless on
    its own. Hidden from the index; still reachable by URL for the rare
    technical setup that edits the FestivalPro URLs."""

    list_display = ["source", "login_url", "export_url"]
    readonly_fields = ["id"]
    search_fields = ["source__name"]


@admin.register(ImportRun)
class ImportRunAdmin(admin.ModelAdmin):
    list_display = [
        "source",
        "status",
        "triggered_by",
        "started_at",
        "finished_at",
        "source_file_name",
    ]
    readonly_fields = ["id", "started_at", "finished_at", "log", "summary"]
    list_filter = ["status"]
    search_fields = ["source__name", "source_file_name"]
