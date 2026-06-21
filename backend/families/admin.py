import json

from django.contrib import admin, messages
from django.http import HttpResponse

from .dsar import (
    build_family_export,
    family_export_to_csv,
    scrub_audit_logs_for_children,
)
from .models import Child, Family, Parent


@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display = ("id", "last_name", "last_participation_date", "anonymized_at")
    search_fields = ("id", "last_name")
    list_filter = ("last_participation_date", "anonymized_at")
    actions = ["export_as_json", "export_as_csv", "erase_families"]

    @admin.action(description="Export selected families (JSON, GDPR access request)")
    def export_as_json(self, request, queryset):
        exports = [build_family_export(family) for family in queryset]
        payload = exports[0] if len(exports) == 1 else exports
        response = HttpResponse(
            json.dumps(payload, indent=2), content_type="application/json"
        )
        response["Content-Disposition"] = 'attachment; filename="family-export.json"'
        return response

    @admin.action(description="Export selected families (CSV, GDPR access request)")
    def export_as_csv(self, request, queryset):
        # CSV is single-family oriented; export the first selected family.
        family = queryset.first()
        if family is None:
            self.message_user(request, "No family selected.", level=messages.WARNING)
            return
        csv_data = family_export_to_csv(build_family_export(family))
        response = HttpResponse(csv_data, content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="family-{family.id}.csv"'
        )
        return response

    @admin.action(description="Erase selected families (GDPR right to erasure)")
    def erase_families(self, request, queryset):
        from checkins.models import AuditLog

        count = 0
        for family in queryset:
            child_ids = [str(c.id) for c in family.children.all()]
            AuditLog.objects.create(
                user=request.user,
                action="dsar_erasure",
                entity_type="Family",
                entity_id=str(family.id),
                details={"last_name": family.last_name, "child_count": len(child_ids)},
            )
            scrub_audit_logs_for_children(child_ids)
            family.delete()
            count += 1
        self.message_user(
            request,
            f"Erased {count} families (data deleted, audit trail scrubbed).",
            level=messages.SUCCESS,
        )


@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ("name", "relationship_type", "family")
    search_fields = ("name", "email", "phone")
    list_filter = ("relationship_type",)


@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "family", "birthdate")
    search_fields = ("first_name", "last_name")
    list_filter = ("last_participation_date", "anonymized_at")
