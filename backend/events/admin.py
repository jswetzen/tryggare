from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.core.exceptions import ObjectDoesNotExist
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
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

# reports.services is the single source of truth for whole-year age (the
# age_at_event column below). A module-level import is safe here even though
# EventAdmin.generate_report defers its own reports.services import: admin
# modules are only imported by autodiscover, long after the app registry has
# finished loading every app's models.
from reports.services import age_on

from .services import duplicate_extra_to_event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "start_date",
        "end_date",
        "parent_checkin_policy_default",
        "price",
        "registration_window_status",
        "registration_link",
    )
    list_filter = ("parent_checkin_policy_default",)
    search_fields = ("name",)
    actions = ("generate_report",)

    # No event-management UI exists in the frontend yet (just checkin/checkout/
    # printing/reports), so Django admin is the only place staff can grab a
    # given event's public registration URL.
    @admin.display(description="Registration page")
    def registration_link(self, obj):
        url = f"{settings.FRONTEND_BASE_URL}/register/{obj.id}/"
        return format_html('<a href="{0}" target="_blank">Open</a>', url)

    def view_on_site(self, obj):
        return f"{settings.FRONTEND_BASE_URL}/register/{obj.id}/"

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


class TicketTypeListFilter(admin.RelatedFieldListFilter):
    """Ticket-type sidebar filter that builds its options in one query.

    The stock RelatedFieldListFilter renders each option via
    ``str(TicketType)``, which interpolates the type's *event* name — one
    extra query per option, every changelist load. Measured at 1 query per
    ticket type; pre-joining the event makes the whole sidebar flat.
    """

    def field_choices(self, field, request, model_admin):
        return [
            (obj.pk, str(obj))
            for obj in TicketType.objects.select_related("event").order_by(
                "event__name", "sort_order", "name"
            )
        ]


class TicketTriageMixin:
    """Shared changelist columns for EventTicketAdmin and SessionTicketAdmin.

    Exists so a coordinator can answer "is this named child on the right
    ticket type?" from a single screen. Before this, neither changelist
    carried a ticket_type column at all, so pairing a child's age with the
    ticket they hold meant opening tickets one at a time and cross-
    referencing birthdates by hand.

    Subclasses implement `_event_for()`: EventTicket owns its event
    directly, SessionTicket only reaches one through its session.
    """

    def _event_for(self, obj):
        raise NotImplementedError

    @admin.display(description=_("Family"), ordering="attendee__family__last_name")
    def family(self, obj):
        # Deliberately the raw last_name, not str(Family): Family.__str__ /
        # display_name fall back to querying self.parents when last_name is
        # blank, which would be an extra query on every row.
        return obj.attendee.family.last_name or None

    @admin.display(description=_("Age at event"))
    def age_at_event(self, obj):
        # Not sortable — computed in Python, with no DB expression to order
        # by. birthdate lives on the Child subclass, not on the Attendee a
        # ticket points at, so a parent's ticket legitimately has no age.
        try:
            child = obj.attendee.child
        except ObjectDoesNotExist:
            return None
        event = self._event_for(obj)
        if event is None:
            return None
        return age_on(child.birthdate, event.start_date)

    @admin.display(
        description=_("Registration status"), ordering="registration__status"
    )
    def registration_status(self, obj):
        # Null on staff-created and imported tickets — those never came
        # through public self-serve registration.
        if obj.registration_id is None:
            return None
        return obj.registration.get_status_display()


@admin.register(EventTicket)
class EventTicketAdmin(TicketTriageMixin, admin.ModelAdmin):
    """
    Admin interface for event tickets (passes).
    """

    list_display = (
        "attendee",
        "family",
        "age_at_event",
        "event",
        "ticket_type",
        "registration_status",
        "external_ticket_code",
    )
    list_filter = ("event", ("ticket_type", TicketTypeListFilter))
    search_fields = (
        "attendee__first_name",
        "attendee__last_name",
        "attendee__family__last_name",
        "external_ticket_code",
        "event__name",
    )
    # attendee__child: birthdate is on the Child subclass (multi-table
    # inheritance), so without this join age_at_event costs a query per row.
    # ticket_type__event: TicketType.__str__ interpolates its event's name.
    list_select_related = (
        "attendee",
        "attendee__family",
        "attendee__child",
        "event",
        "ticket_type",
        "ticket_type__event",
        "registration",
    )
    autocomplete_fields = ["attendee", "event"]

    def _event_for(self, obj):
        return obj.event


@admin.register(SessionTicket)
class SessionTicketAdmin(TicketTriageMixin, admin.ModelAdmin):
    """
    Admin interface for session tickets.
    """

    list_display = (
        "attendee",
        "family",
        "age_at_event",
        "session",
        "event",
        "ticket_type",
        "registration_status",
        "external_ticket_code",
    )
    list_filter = ("session__event", ("ticket_type", TicketTypeListFilter))
    search_fields = (
        "attendee__first_name",
        "attendee__last_name",
        "attendee__family__last_name",
        "external_ticket_code",
        "session__name",
        "session__event__name",
    )
    # session__event: needed by both the `event` column and Session.__str__.
    list_select_related = (
        "attendee",
        "attendee__family",
        "attendee__child",
        "session",
        "session__event",
        "ticket_type",
        "ticket_type__event",
        "registration",
    )
    autocomplete_fields = ["attendee", "session"]

    @admin.display(description=_("Event"), ordering="session__event")
    def event(self, obj):
        return obj.session.event

    def _event_for(self, obj):
        return obj.session.event


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
        if cleaned_data.get(
            "kind"
        ) == TicketType.Kind.SESSION_BUNDLE and not cleaned_data.get("sessions"):
            raise forms.ValidationError(
                _("A session-bundle ticket type must cover at least one session.")
            )
        requires_ticket_type = cleaned_data.get("requires_ticket_type")
        if requires_ticket_type is not None:
            event = cleaned_data.get("event")
            if event is not None and requires_ticket_type.event_id != event.id:
                raise forms.ValidationError(
                    {
                        "requires_ticket_type": _(
                            "The required ticket type must belong to the same event."
                        )
                    }
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
        "requires_ticket_type",
        "max_per_required",
    )
    list_filter = ("event", "applies_to", "kind", "is_hidden", "is_active")
    search_fields = ("name", "event__name")
    autocomplete_fields = ["event", "requires_ticket_type"]
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


class DuplicateExtraToEventForm(forms.Form):
    target_event = forms.ModelChoiceField(
        queryset=Event.objects.order_by("-start_date"),
        label=_("Target event"),
    )


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
        "reuse_badge",
    )
    list_filter = ("event", "applies_to", "per_attendee", "is_active")
    search_fields = ("name", "event__name")
    autocomplete_fields = ["event", "session"]
    inlines = [ExtraChoiceInline]
    actions = ["duplicate_to_event"]
    exclude = ("cloned_from",)
    readonly_fields = ("lineage_display",)

    @admin.display(description=_("Reuse"))
    def reuse_badge(self, obj):
        count = len(obj.lineage_siblings())
        return f"Duplicated ({count})" if count else "—"

    @admin.display(description=_("Clone lineage"))
    def lineage_display(self, obj):
        if obj.pk is None:
            return "—"
        lines = []
        if obj.cloned_from:
            lines.append(
                format_html(
                    'Cloned from <a href="{}">{}</a> ({})',
                    reverse("admin:events_extra_change", args=[obj.cloned_from_id]),
                    obj.cloned_from.name,
                    obj.cloned_from.event.name,
                )
            )
        siblings = obj.lineage_siblings()
        if siblings:
            links = format_html_join(
                mark_safe(", "),
                '<a href="{}">{} ({})</a>',
                (
                    (
                        reverse("admin:events_extra_change", args=[s.id]),
                        s.name,
                        s.event.name,
                    )
                    for s in siblings
                ),
            )
            lines.append(format_html("Also used at: {}", links))
        if not lines:
            return _("Not duplicated elsewhere.")
        return format_html_join(mark_safe("<br>"), "{}", ((line,) for line in lines))

    @admin.action(description=_("Duplicate to another event…"))
    def duplicate_to_event(self, request, queryset):
        if "apply" in request.POST:
            form = DuplicateExtraToEventForm(request.POST)
            if form.is_valid():
                target_event = form.cleaned_data["target_event"]
                count = queryset.count()
                for extra in queryset:
                    duplicate_extra_to_event(extra, target_event)
                self.message_user(
                    request,
                    _("Duplicated %(count)d extra(s) to '%(event)s'.")
                    % {"count": count, "event": target_event.name},
                    messages.SUCCESS,
                )
                return None
        else:
            form = DuplicateExtraToEventForm()

        context = {
            **self.admin_site.each_context(request),
            "title": _("Duplicate extras to another event"),
            "queryset": queryset,
            "form": form,
            "opts": self.model._meta,
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
        }
        return TemplateResponse(
            request,
            "admin/events/extra/duplicate_confirmation.html",
            context,
        )


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
