import json

from django.contrib import admin, messages
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _

from config.admin import HiddenFromIndexAdmin

from .dsar import (
    build_family_export,
    family_export_to_csv,
    scrub_audit_logs_for_children,
)
from .models import Attendee, Child, Family, Parent


class ParentInline(admin.TabularInline):
    model = Parent
    fk_name = "family"
    extra = 1
    fields = ("first_name", "last_name", "relationship_type", "phone", "email")
    show_change_link = True


class ChildInline(admin.TabularInline):
    model = Child
    fk_name = "family"
    extra = 1
    fields = ("first_name", "last_name", "birthdate")
    show_change_link = True


@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display = ("id", "last_name", "last_participation_date", "anonymized_at")
    search_fields = ("id", "last_name")
    list_filter = ("last_participation_date", "anonymized_at")
    actions = ["export_as_json", "export_as_csv", "erase_families"]
    inlines = [ParentInline, ChildInline]

    # Django admin actions carry NO permission check of their own: by default
    # they run for anyone who can view the changelist. That would make the two
    # DSAR permissions (families/models.py Meta) enforceable on the API and
    # bypassable in the admin — which is worse than not having them, because
    # the API test suite would report the boundary as held.
    def has_export_family_dsar_permission(self, request):
        return request.user.has_perm("families.export_family_dsar")

    def has_erase_family_dsar_permission(self, request):
        return request.user.has_perm("families.erase_family_dsar")

    @admin.action(
        description=_("Export selected families (JSON, GDPR access request)"),
        permissions=["export_family_dsar"],
    )
    def export_as_json(self, request, queryset):
        exports = [build_family_export(family) for family in queryset]
        payload = exports[0] if len(exports) == 1 else exports
        response = HttpResponse(
            json.dumps(payload, indent=2), content_type="application/json"
        )
        response["Content-Disposition"] = 'attachment; filename="family-export.json"'
        return response

    @admin.action(
        description=_("Export selected families (CSV, GDPR access request)"),
        permissions=["export_family_dsar"],
    )
    def export_as_csv(self, request, queryset):
        # CSV is single-family oriented; export the first selected family.
        family = queryset.first()
        if family is None:
            self.message_user(request, _("No family selected."), level=messages.WARNING)
            return
        csv_data = family_export_to_csv(build_family_export(family))
        response = HttpResponse(csv_data, content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="family-{family.id}.csv"'
        )
        return response

    @admin.action(
        description=_("Erase selected families (GDPR right to erasure)"),
        permissions=["erase_family_dsar"],
    )
    def erase_families(self, request, queryset):
        from checkins.audit import log_audit

        count = 0
        for family in queryset:
            child_ids = [str(c.id) for c in family.children.all()]
            log_audit(
                request,
                action="dsar_erasure",
                entity_type="Family",
                entity_id=str(family.id),
                details={"child_count": len(child_ids)},
            )
            scrub_audit_logs_for_children(child_ids)
            family.delete()
            count += 1
        self.message_user(
            request,
            _("Erased %(count)d families (data deleted, audit trail scrubbed).")
            % {"count": count},
            level=messages.SUCCESS,
        )


@admin.register(Attendee)
class AttendeeAdmin(HiddenFromIndexAdmin, admin.ModelAdmin):
    """Multi-table-inheritance base of Child and Parent — every row here is
    already listed under Children or Parents, so the index entry only ever
    duplicated them. Hidden, not unregistered: EventTicketAdmin,
    SessionTicketAdmin and RegistrationExtraAdmin autocomplete against it."""

    list_display = ("first_name", "last_name", "family")
    search_fields = ("first_name", "last_name")
    list_filter = ("last_participation_date",)


@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "relationship_type",
        "family",
        "phone_locked",
        "email_locked",
        "health_consent_status",
    )
    search_fields = ("first_name", "last_name", "email", "phone")
    list_filter = (
        "relationship_type",
        "phone_locked",
        "email_locked",
        "health_consent_status",
    )
    autocomplete_fields = ["family"]


@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "family",
        "birthdate",
        "health_consent_status",
    )
    search_fields = ("first_name", "last_name")
    list_filter = ("last_participation_date", "anonymized_at", "health_consent_status")
    autocomplete_fields = ["family"]
