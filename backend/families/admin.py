import json

from django.contrib import admin, messages
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _

from config.admin import HiddenFromIndexAdmin
from registrations.admin import (
    RecoverableChangelistMixin,
    format_balance,
    render_balance,
)
from registrations.models import Payment, Registration

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


class RegistrationInline(admin.TabularInline):
    """Read-only jump-off point from a family to its registrations and
    their balances — the dead end the increment's evidence calls out:
    "having found a family, you are at a dead end and must go back to a
    different changelist and search again by hand." Editing a registration
    still goes through RegistrationAdmin (status transitions are
    service-function-only there); this is for finding the right one and
    seeing what's owed."""

    model = Registration
    fk_name = "family"
    extra = 0
    fields = ("reference_code", "event", "status", "balance_display")
    readonly_fields = fields
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("event", "payment")
            .annotate(
                **{
                    Payment.BALANCE_ANNOTATION: Payment.balance_expression(
                        prefix="payment__"
                    )
                }
            )
        )

    @admin.display(description=_("Balance"))
    def balance_display(self, obj):
        # Deliberately still format_balance(), not render_balance() — the
        # designer called this inline shippable as-is and "the strongest
        # thing in the increment"; it inherits the sv-SE grouping fix
        # because format_balance's own internals changed, but its layout
        # and two-state (owed/settled) rendering are untouched by this
        # round on purpose.
        annotated = getattr(obj, Payment.BALANCE_ANNOTATION, None)
        if annotated is not None:
            return format_balance(annotated)
        payment = getattr(obj, "payment", None)
        return format_balance(payment.balance) if payment else "—"


@admin.register(Family)
class FamilyAdmin(RecoverableChangelistMixin, admin.ModelAdmin):
    # R6: the raw UUID used to be the first column and the only link,
    # wrapping to three lines, while "Nyström" sat next to it as inert
    # text. Dropped from list_display (it stays in search_fields — a
    # bookmarked/typed ``?id__exact=`` link still resolves); last_name is
    # the link now.
    list_display = (
        "last_name",
        "events_display",
        "balance_display",
        "last_participation_date",
        "anonymized_at",
    )
    list_display_links = ("last_name",)
    # A volunteer holding only a surname, or only a child's first name,
    # needs both to work — last_name is on Family, but a child/parent's own
    # first/last name lives on Attendee (the multi-table-inheritance base
    # both Parent and Child share), so `attendees__*` reaches both without
    # duplicating this per subclass.
    search_fields = ("id", "last_name", "attendees__first_name", "attendees__last_name")
    list_filter = ("last_participation_date", "anonymized_at")
    actions = ["export_as_json", "export_as_csv", "erase_families"]
    inlines = [ParentInline, ChildInline, RegistrationInline]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related("registrations__event")
            # A correlated Subquery composed from two of them (see
            # Payment.family_balance_subquery), not a join-based Sum — this
            # queryset's own search_fields join attendees__*, a
            # multi-valued relation, on top of registrations already being
            # one-to-many from Family. A join-based Sum here would
            # double-count exactly like R1, one relation further up.
            .annotate(**{Payment.BALANCE_ANNOTATION: Payment.family_balance_subquery()})
        )

    @admin.display(description=_("Balance"), ordering=Payment.BALANCE_ANNOTATION)
    def balance_display(self, obj):
        return render_balance(getattr(obj, Payment.BALANCE_ANNOTATION, None))

    @admin.display(description=_("Registered for"))
    def events_display(self, obj):
        # Two families can share a surname (the increment's planted
        # Nyström pair) — the events they're registered for are the
        # cheapest discriminator to show right on the results row, without
        # opening either one. Prefetched above so this is zero extra
        # queries per row.
        names = sorted({r.event.name for r in obj.registrations.all()})
        return ", ".join(names) if names else "—"

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
