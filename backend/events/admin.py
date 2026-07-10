from django import forms
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import (
    Event,
    EventTicket,
    Extra,
    ExtraChoice,
    PromoCode,
    Session,
    SessionTicket,
    Ticket,
    TicketType,
)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "start_date",
        "end_date",
        "parent_checkin_policy_default",
        "price",
        "registration_window_status",
    )
    list_filter = ("parent_checkin_policy_default",)
    search_fields = ("name",)
    actions = ("generate_report",)

    @admin.action(description="Generate / refresh report snapshot")
    def generate_report(self, request, queryset):
        # Imported here to avoid a hard import cycle between the apps at load.
        from reports.services import generate_event_report

        for event in queryset:
            report = generate_event_report(event, user=request.user)
            self.message_user(
                request,
                f"Generated report for '{event.name}': "
                f"{report.unique_children} children, "
                f"{report.total_checkins} check-ins.",
            )


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "event",
        "start_time",
        "end_time",
        "is_active",
        "parent_checkin_policy",
        "effective_parent_checkin_policy",
    )
    list_filter = ("is_active", "event", "parent_checkin_policy")
    search_fields = ("name", "event__name")

    @admin.display(description="Effective parent policy")
    def effective_parent_checkin_policy(self, obj):
        return obj.effective_parent_checkin_policy


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    """
    DEPRECATED: Use EventTicketAdmin or SessionTicketAdmin instead.
    """

    list_display = ("type", "attendee", "session")
    list_filter = ("type",)
    search_fields = (
        "attendee__first_name",
        "attendee__last_name",
        "session__name",
    )


@admin.register(EventTicket)
class EventTicketAdmin(admin.ModelAdmin):
    """
    Admin interface for event tickets (passes).
    """

    list_display = ("attendee", "event", "id")
    list_filter = ("event",)
    search_fields = ("attendee__first_name", "attendee__last_name", "event__name")
    autocomplete_fields = ["attendee", "event"]


@admin.register(SessionTicket)
class SessionTicketAdmin(admin.ModelAdmin):
    """
    Admin interface for session tickets.
    """

    list_display = ("attendee", "session", "get_event", "id")
    list_filter = ("session__event",)
    search_fields = (
        "attendee__first_name",
        "attendee__last_name",
        "session__name",
        "session__event__name",
    )
    autocomplete_fields = ["attendee", "session"]

    def get_event(self, obj):
        return obj.session.event

    get_event.short_description = "Event"
    get_event.admin_order_field = "session__event"


class TicketTypeAdminForm(forms.ModelForm):
    """A2: catch a session_bundle TicketType with no sessions attached at
    save time. Must live on the form's clean(), not TicketType.clean() —
    the sessions M2M isn't written to the instance until after save() (via
    form.save_m2m()), so a model-level clean() would see stale/empty state
    on every add and most edits regardless of what was actually submitted.
    cleaned_data, by contrast, reflects the submitted selection immediately.
    See registrations/views.py::_materialize_ticket for the runtime
    backstop this doesn't replace."""

    class Meta:
        model = TicketType
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("kind") == TicketType.Kind.SESSION_BUNDLE and not cleaned_data.get(
            "sessions"
        ):
            raise forms.ValidationError(
                _("A session-bundle ticket type must cover at least one session.")
            )
        return cleaned_data


@admin.register(TicketType)
class TicketTypeAdmin(admin.ModelAdmin):
    form = TicketTypeAdminForm
    list_display = (
        "name",
        "event",
        "price",
        "applies_to",
        "kind",
        "is_hidden",
        "is_active",
        "sort_order",
    )
    list_filter = ("event", "applies_to", "kind", "is_hidden", "is_active")
    search_fields = ("name", "event__name")
    autocomplete_fields = ["event"]
    filter_horizontal = ["sessions"]


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "event",
        "discount_type",
        "discount_value",
        "uses_count",
        "max_uses",
        "is_active",
    )
    list_filter = ("event", "discount_type", "is_active")
    search_fields = ("code", "event__name")
    autocomplete_fields = ["event"]
    filter_horizontal = ["applies_to_ticket_types", "unlocks_ticket_types"]
    readonly_fields = ("uses_count",)


class ExtraChoiceInline(admin.TabularInline):
    model = ExtraChoice
    extra = 1
    fields = ("label", "price_delta", "sort_order", "is_active")


@admin.register(Extra)
class ExtraAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "event",
        "session",
        "price",
        "per_attendee",
        "applies_to",
        "is_active",
        "sort_order",
    )
    list_filter = ("event", "applies_to", "per_attendee", "is_active")
    search_fields = ("name", "event__name")
    autocomplete_fields = ["event", "session"]
    inlines = [ExtraChoiceInline]


@admin.register(ExtraChoice)
class ExtraChoiceAdmin(admin.ModelAdmin):
    """Standalone registration alongside the ExtraAdmin inline above —
    needed so RegistrationExtraAdmin.choice can use autocomplete_fields
    (Django requires the target model have its own registered ModelAdmin
    with search_fields, inlines don't count)."""

    list_display = ("label", "extra", "price_delta", "is_active", "sort_order")
    list_filter = ("extra__event", "is_active")
    search_fields = ("label", "extra__name")
    autocomplete_fields = ["extra"]
