from urllib.parse import urlencode

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
from config.admin import HiddenFromIndexAdmin

from .models import (
    AppliesTo,
    Event,
    EventTicket,
    Extra,
    ExtraChoice,
    PromoCode,
    RegistrationWindowStatus,
    Session,
    SessionTicket,
    Ticket,
    TicketRule,
    TicketType,
)

# reports.services is the single source of truth for whole-year age (the
# age_at_event column below). A module-level import is safe here even though
# EventAdmin.generate_report defers its own reports.services import: admin
# modules are only imported by autodiscover, long after the app registry has
# finished loading every app's models.
from reports.services import age_on

# Same reasoning as the reports.services import above: admin modules load at
# autodiscover, so a module-level import of another app's service layer is
# safe. registrations.services imports events.models (not events.admin), so
# this is not a cycle.
from checkins.audit import log_audit

# The single sv-SE money-formatting path (see registrations/admin.py's
# format_balance docstring) — this wizard is the screen the "1050,00" vs
# "10 500,00" one-glyph difference matters most on, so it borrows the same
# helper rather than growing a second one. Safe as a module-level import for
# the same reason the registrations.services import below is: admin modules
# only load at autodiscover, well after every app's models are ready, and
# registrations.admin does not import events.admin (no cycle).
from registrations.admin import format_balance, format_signed_amount
from registrations.services import (
    AGE_MISMATCH_Q,
    UNCHECKABLE_AGE_FIT_Q,
    InvalidPaymentTransition,
    TicketTypeChangeRejected,
    change_attendee_ticket_type,
    plan_ticket_type_change,
    ticket_type_sold_count,
)

from .services import duplicate_extra_to_event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "start_date",
        "end_date",
        "ticket_rule_default",
        "price",
        "registration_window_status_label",
        "registration_link",
    )
    list_filter = ("ticket_rule_default",)
    search_fields = ("name",)
    # Deprecated column, read by nothing: not shown, so nobody sets a dead
    # control. The proper admin redesign (and the column drop) is a later
    # increment.
    exclude = ("parent_checkin_policy_default",)
    actions = ("generate_report",)
    # Explicit fieldsets so the check-in rule gets a block of its own, away
    # from the registration/branding fields. Every editable field must be
    # listed here: unlike ``exclude``, ``fieldsets`` is an allow-list, so a
    # field added to Event later is invisible in admin until it is added.
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "start_date",
                    "end_date",
                    "price",
                    "registration_opens_at",
                    "registration_closes_at",
                    "header_image_url",
                    "accent_color",
                )
            },
        ),
        (_("Check-in rules"), {"fields": ("ticket_rule_default",)}),
    )

    # No event-management UI exists in the frontend yet (just checkin/checkout/
    # printing/reports), so Django admin is the only place staff can grab a
    # given event's public registration URL.
    # The model property returns the raw code ("open", "not_configured"),
    # which the changelist printed verbatim under an English header. Render the
    # translated choice label instead. Not sortable: the status is computed
    # from "now" and two datetimes, so there is no column to order by and a
    # misleading ordering would be worse than none.
    @admin.display(description=_("Registration window status"))
    def registration_window_status_label(self, obj):
        return RegistrationWindowStatus(obj.registration_window_status).label

    @admin.display(description=_("Registration page"))
    def registration_link(self, obj):
        url = f"{settings.FRONTEND_BASE_URL}/register/{obj.id}/"
        return format_html('<a href="{0}" target="_blank">{1}</a>', url, _("Open page"))

    def view_on_site(self, obj):
        return f"{settings.FRONTEND_BASE_URL}/register/{obj.id}/"

    @admin.action(description=_("Generate / refresh report snapshot"))
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
        # The change-link column stays first. The rule columns used to come
        # right after it and, in Swedish at 1280px, pushed Active / Start time
        # / Event off-screen (designer critique, 2026-10-01). Now: identity
        # (name, event), state (active), the resolved rule and the adults
        # flag, then the times, with the raw (mostly blank) override last.
        "name",
        "event",
        "is_active",
        "effective_ticket_rule",
        "adults_not_checked_in",
        "start_time",
        "end_time",
        "ticket_rule",
    )
    list_filter = ("is_active", "event", "ticket_rule", "adults_not_checked_in")
    search_fields = ("name", "event__name")
    # Deprecated columns, read by nothing: not shown, so nobody sets a dead
    # control. The proper admin redesign (and the column drop) is a later
    # increment.
    exclude = ("requires_ticket", "parent_checkin_policy")
    # The two controls that decide who gets checked in here sit in one block:
    # staff evaluating the old layout could not tell them apart, because the
    # ticket rule and the "adults" checkbox were scattered through one flat
    # list. ``fieldsets`` is an allow-list, so the deprecated columns stay off
    # the form without needing ``exclude`` (kept anyway as a second guard).
    fieldsets = (
        (
            None,
            {"fields": ("event", "name", "start_time", "end_time", "is_active")},
        ),
        (
            _("Check-in rules"),
            {"fields": ("ticket_rule", "adults_not_checked_in")},
        ),
    )

    def get_changeform_initial_data(self, request):
        # New sessions start with "adults are not checked in" ticked: most
        # sessions are children's, and an adult check-in is the exception
        # staff should have to opt into. Done here rather than as the model
        # default so existing rows, seed scripts and API/ORM callers keep the
        # old behaviour (False) -- a changed model default would also change
        # what every ``Session.objects.create(...)`` without the field means.
        initial = super().get_changeform_initial_data(request)
        initial.setdefault("adults_not_checked_in", True)
        return initial

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == "ticket_rule":
            # The stored value for "inherit" is "", which Django would label
            # "---------". Say what it does instead. This is the generic label
            # (used on the add form, where no event is known yet);
            # get_form() sharpens it for an existing session.
            kwargs["choices"] = [
                ("", _("Same as the event's default")),
                *TicketRule.choices,
            ]
        return super().formfield_for_choice_field(db_field, request, **kwargs)

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, change=change, **kwargs)
        # ``modelform_factory`` builds fresh field instances on every call, so
        # editing base_fields here cannot leak between requests or languages.
        fields = form.base_fields
        if obj is None:
            # The "pre-ticked" sentence is only true on the add form (see
            # get_changeform_initial_data); on a change page it would
            # contradict the box the user is looking at. So it lives here
            # rather than in the model's help_text.
            if "adults_not_checked_in" in fields:
                field = fields["adults_not_checked_in"]
                field.help_text = "{} {}".format(
                    field.help_text,
                    _(
                        "The box is already ticked when you add a new "
                        "session: untick it for sessions where adults are "
                        "checked in."
                    ),
                )
        elif "ticket_rule" in fields and obj.event_id:
            # Say what "blank" resolves to for THIS session's event, so the
            # coordinator does not have to open the event to find out.
            fields["ticket_rule"].choices = [
                (
                    "",
                    _("Same as the event's default (%(rule)s)")
                    % {"rule": obj.event.get_ticket_rule_default_display()},
                ),
                *TicketRule.choices,
            ]
        return form

    @admin.display(description=_("Effective ticket rule"))
    def effective_ticket_rule(self, obj):
        return TicketRule(obj.effective_ticket_rule).label


@admin.register(Ticket)
class TicketAdmin(HiddenFromIndexAdmin, admin.ModelAdmin):
    """
    DEPRECATED: Use EventTicketAdmin or SessionTicketAdmin instead.

    Hidden from the index (see HiddenFromIndexAdmin): a deprecated model
    two entries below the two that replaced it is pure confusion. Still
    registered so existing rows stay reachable by URL until the model goes.
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


class AgeFitListFilter(admin.SimpleListFilter):
    """ "Åldern passar biljettypen" — the filter R2 (revision round 1) exists
    for. Two coordinator personas each burned ~25 minutes eye-scanning 212
    rows because nothing on the changelist could answer "is this child on
    the right tier?" directly.

    Built entirely from ``AGE_MISMATCH_Q`` / ``UNCHECKABLE_AGE_FIT_Q`` in
    ``registrations.services`` — the same predicate ``_age_warning_for``
    explains row-by-row on the change-ticket-type wizard. Deliberately not
    re-derived here: a filter that computes the mismatch independently of
    the guarded action would eventually disagree with it in front of an
    operator, which is a worse failure than the scan this replaces.
    """

    title = _("Age fits the ticket type")
    parameter_name = "age_fits_ticket_type"

    def lookups(self, request, model_admin):
        return (
            ("no", _("No")),
            ("unknown", _("Cannot be checked")),
            ("yes", _("Yes")),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "no":
            return queryset.filter(AGE_MISMATCH_Q)
        if value == "unknown":
            return queryset.filter(UNCHECKABLE_AGE_FIT_Q)
        if value == "yes":
            return queryset.exclude(AGE_MISMATCH_Q).exclude(UNCHECKABLE_AGE_FIT_Q)
        return queryset


class ChangeTicketTypeForm(forms.Form):
    """Step-1 form for ``EventTicketAdmin.change_ticket_type``.

    The queryset is narrowed to the selected tickets' own event and to
    active types, so the two hard rejections in
    ``plan_ticket_type_change`` are unreachable from this screen rather
    than merely caught by it — the service still enforces both, because
    it is the domain guarantee and this form is only one of its callers.
    """

    ticket_type = forms.ModelChoiceField(
        queryset=TicketType.objects.none(),
        label=_("New ticket type"),
    )
    # Renamed from acknowledge_age_warning (R4/D1, gate review 2026-09-25):
    # one checkbox now covers every warning TicketTypeChangePlan.warnings
    # can carry, not just an age mismatch — capacity joined it the same
    # way age was always handled, a warning to override, never a block
    # (see TicketTypeChangePlan.warnings and _capacity_warning_for in
    # registrations/services.py).
    acknowledge_warnings = forms.BooleanField(
        required=False,
        label=_(
            "I've reviewed the warning(s) above and want to make this change anyway"
        ),
        help_text=_(
            "Covers every warning shown above — an age that doesn't fit the "
            "window, the new type being at or over capacity, or both. Tick "
            "this only if you have checked and the placement is still "
            "correct despite it."
        ),
    )

    def __init__(self, *args, event=None, exclude_ticket_type_ids=(), **kwargs):
        super().__init__(*args, **kwargs)
        # B4: excludes each selected ticket's own *current* type, not just
        # retired ones. plan_ticket_type_change always rejects "already on
        # this type" (see its ticket.ticket_type_id == new_ticket_type.id
        # check) — offering it here is a choice the wizard is guaranteed to
        # bounce back on the very next screen.
        self.fields["ticket_type"].queryset = (
            TicketType.objects.filter(event=event, is_active=True)
            .exclude(id__in=exclude_ticket_type_ids)
            .order_by("sort_order", "name")
        )
        # One money-formatting path (see registrations/admin.py's
        # format_balance) — this used to render the raw Decimal
        # ("700.00"), unlocalised and unitless, next to a step-2 preview
        # that already read "700,00 kr".
        self.fields["ticket_type"].label_from_instance = (
            lambda obj: f"{obj.name} — {format_balance(obj.price)}"
        )


class TicketTypeGuardMixin:
    """Locks ``ticket_type`` on the *change* form and points the operator at
    the guarded ``change_ticket_type`` action instead.

    Why this exists: a 14 August persona test was asked to move a
    13-year-old off the 0-12 ticket. It used this ordinary change form —
    the dropdown was right there, nothing warned it existed a better way —
    and the write went through with no price recompute, no ledger entry,
    and no audit row. ``change_attendee_ticket_type`` (see
    registrations/services.py) already does all three correctly; this
    mixin's whole job is to stop the raw field from being a competing path
    to the same outcome.

    Locked for every user, including superusers — this is a data-integrity
    rule, not a permission. The one case the guarded action genuinely
    cannot express (e.g. a same-price correction with no event at all)
    still has a way out: the Django shell. That is deliberate. A case that
    unusual should be visible and deliberate every time, not something a
    change-form edit quietly slides through.

    Left *editable* on the add form. Creating a ticket is a first-time
    choice — there is no price snapshot, no Payment, and no history yet for
    a raw field edit to desynchronise. Locking it there too would make it
    impossible to enter a staff-created or imported ticket's type in one
    step.

    Revision round 1 (R1): the add form staying open turned out to be a
    second door to the exact write this mixin exists to close. A break-it
    persona deleted an EventTicket and re-added it at a different tier
    through the add form in under two minutes — no
    ``event_ticket_type_changed`` audit row, and the old price carried onto
    the new tier, underbilling by 300 kr. Keeping the add form usable for
    its real job (entering a genuinely new or imported ticket) while closing
    "delete, then re-add differently" meant picking the *other* side of that
    trade: a ticket delete is refund-shaped — real money and a registration
    sit behind it — so it is denied outright, for every user including
    superusers, same as the locked field above. Nothing in the production
    write paths deletes an EventTicket or SessionTicket through admin; only
    test/seed scripts go straight at the ORM, and those already bypass admin
    permissions. A genuine cancellation still has a route: the Django shell,
    deliberately visible and deliberate rather than one click on a
    changelist.

    R4/D1 (product decision + gate review, 2026-09-25): the add form here
    is also the one other place (besides the guest self-serve submission
    in registrations/views.py, and the ticket-type-change wizard below)
    that can put a ticket type over its configured capacity — staff are
    deliberately exempt from the guest-facing hard refusal, the same
    "warn, don't block" stance already established for the age-window
    check on TicketTypeAdmin (``_warn_if_age_window_uncheckable``). See
    ``save_model``/``_warn_if_over_capacity`` below. Change-form saves
    never trigger it: ``ticket_type`` is excluded from that form entirely
    (see ``get_exclude``), so a change-form save can never be the write
    that pushes a type over capacity in the first place.
    """

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj is not None:
            readonly += ["ticket_type_locked"]
        return readonly

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            self._warn_if_over_capacity(request, obj)

    def _warn_if_over_capacity(self, request, obj):
        """Passive, add-form-only warning (R4/D1, 2026-09-25) — never
        blocks the save. ``obj.ticket_type`` is already the *saved* value
        by the time ``save_model`` calls this, so ``ticket_type_sold_count``
        below counts this very row.

        Deliberately a plain ``>`` against ``ticket_type_sold_count``, not
        ``reserve_ticket_type_capacity``'s lock-then-compare: staff are
        never refused here, so there is nothing to gate — only something to
        report after the fact — and a lock protecting a write that cannot
        be rejected would just be pointless contention on a row several
        operators might be adding tickets against at once.
        """
        ticket_type = obj.ticket_type
        if ticket_type is None or ticket_type.capacity is None:
            return
        sold = ticket_type_sold_count(ticket_type)
        if sold > ticket_type.capacity:
            self.message_user(
                request,
                _('"%(name)s" is now over capacity (%(sold)s/%(capacity)s).')
                % {
                    "name": ticket_type.name,
                    "sold": sold,
                    "capacity": ticket_type.capacity,
                },
                level=messages.WARNING,
            )

    def get_exclude(self, request, obj=None):
        exclude = list(super().get_exclude(request, obj) or [])
        if obj is not None:
            # The real ``ticket_type`` field is dropped from the form
            # entirely (rather than left in readonly_fields under its own
            # name) so it can be re-rendered as ``ticket_type_locked``
            # below — see that method for why.
            exclude.append("ticket_type")
        return exclude

    def has_delete_permission(self, request, obj=None):
        # See the class docstring's R1 paragraph: a ticket delete is
        # refund-shaped, and "delete, then re-add at a different tier" is a
        # silent re-tier path with no audit row and a stale price. Denied
        # outright rather than gated on staff/superuser — same stance as the
        # locked field above, this is a data-integrity rule, not a
        # permission level.
        return False

    @admin.display(description=_("Ticket Type"))
    def ticket_type_locked(self, obj):
        """Plain text, not Django's ordinary readonly-FK rendering, folded
        together with the "how to change it" notice into one field/row.

        R3 (revision round 1): a readonly FK renders as a link to
        ``/admin/events/tickettype/<id>/change/`` — the page that edits the
        *tier itself*, for every ticket on it. That is the most link-like
        thing on this page, and it puts an operator who came to re-tier one
        child one click from a far worse write. Naming this field something
        other than ``ticket_type`` and excluding the real field from the
        form (see ``get_exclude``) is what stops Django's auto-link from
        firing at all — it only triggers when the readonly field name
        matches a real ForeignKey field.

        B2: this used to render the current type as one readonly field and
        a second explanatory pseudo-field below it, which read as a routine
        field hint rather than a locked control — a blind-test persona
        backtracked for about a minute here before treating the detour as
        justified. Folded into one row, led with the state ("Locked.") and
        styled as Django's own ``.messagelist .info`` notice rather than a
        plain ``<p class="help">``, so it reads as "this is deliberately
        gated" on first glance instead of a disabled-field error.

        B1: the link used to land on the bare changelist — 666 tickets deep,
        with no way to find the one the operator came from. It now carries
        the attendee's name through as ``?q=`` (the same field this admin's
        own ``search_fields`` already indexes), so the ticket that prompted
        the visit is on the page that loads, not buried in it.
        """
        if obj.ticket_type_id is None:
            current = self.get_empty_value_display()
        else:
            current = str(obj.ticket_type)

        changelist_url = reverse(
            f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_changelist"
        )
        query_term = (obj.attendee.last_name or obj.attendee.first_name).strip()
        if query_term:
            changelist_url = f"{changelist_url}?{urlencode({'q': query_term})}"

        notice = format_html(
            '<ul class="messagelist" style="margin:6px 0 0;padding:0;">'
            '<li class="info" style="margin:0;">{0} <a href="{1}">{2}</a></li>'
            "</ul>",
            _(
                "Locked. A tier change needs the guided flow so it's "
                "priced correctly and logged."
            ),
            changelist_url,
            _(
                "Open %(attendee)s’s filtered ticket list, tick it, and "
                "choose “Change ticket type…”."
            )
            % {"attendee": str(obj.attendee)},
        )
        return format_html("{0}{1}", current, notice)


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

    @admin.display(description=_("Age at event"), ordering="attendee__child__birthdate")
    def age_at_event(self, obj):
        # Sortable by birthdate: age-at-a-fixed-start is monotone in
        # birthdate only *within one event* (two events with different
        # start dates turn the same birthdate into two different ages), so
        # this ordering is only meaningful once the changelist is filtered
        # to a single event. It is still the right default — "get me
        # oldest-first" is the shape coordinators actually want, and
        # sorting a raw date column costs nothing extra a computed-in-Python
        # column couldn't offer at all. birthdate lives on the Child
        # subclass, not on the Attendee a ticket points at, so a parent's
        # ticket legitimately has no age.
        try:
            child = obj.attendee.child
        except ObjectDoesNotExist:
            return None
        event = self._event_for(obj)
        if event is None:
            return None
        return age_on(child.birthdate, event.start_date)

    @admin.display(description=_("Ticket Type"), ordering="ticket_type__name")
    def ticket_type_name(self, obj):
        """R8 (revision round 1, designer finding F2): ``TicketType.__str__``
        prefixes the event name ("Sommarläger 2027 - Ungdom 13-17"), which
        at 1280px pushes this 985px table past its 631px scroller and
        truncates "Biljettyp" — the one column the whole triage job depends
        on — mid-word. The event name is redundant here anyway: both
        changelists carry an event filter, and once filtered to one event
        every row's event is the same value repeated 212 times."""
        if obj.ticket_type_id is None:
            return self.get_empty_value_display()
        return obj.ticket_type.name

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
class EventTicketAdmin(TicketTriageMixin, TicketTypeGuardMixin, admin.ModelAdmin):
    """
    Admin interface for event tickets (passes).
    """

    list_display = (
        "attendee",
        "family",
        "age_at_event",
        "ticket_type_name",
        "registration_status",
        "external_ticket_code",
    )
    list_filter = ("event", ("ticket_type", TicketTypeListFilter), AgeFitListFilter)
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
    actions = ["change_ticket_type"]

    def _event_for(self, obj):
        return obj.event

    @admin.action(description=_("Change ticket type…"))
    def change_ticket_type(self, request, queryset):
        """The safe version of editing ``ticket_type`` on the change form.

        Two intermediate steps rather than the single one
        ``ExtraAdmin.duplicate_to_event`` needs, for one reason: the price
        difference and the age warning cannot be computed until a target
        type has been picked, and showing them *after* the write would
        defeat the point. Step 1 picks the type, step 2 shows what it will
        do to each family's balance and to the age fit, step 3 commits.

        Scoped to one event per run. A TicketType belongs to exactly one
        event, so a mixed selection has no single legal answer — and
        silently correcting only the matching half is precisely the class of
        half-done admin write this whole increment exists to remove.
        """
        tickets = list(
            queryset.select_related(
                "attendee",
                "attendee__child",
                "event",
                "ticket_type",
                "registration",
                "registration__payment",
            )
        )
        if not tickets:
            return None

        event_ids = {ticket.event_id for ticket in tickets}
        if len(event_ids) > 1:
            self.message_user(
                request,
                _(
                    "Select tickets from a single event — a ticket type "
                    "belongs to one event only."
                ),
                messages.ERROR,
            )
            return None

        event = tickets[0].event

        # Cancel used to be a bare ``href="#"`` — inert, and on this screen
        # actively harmful: both step 1 and step 2 are TemplateResponses
        # rendered directly from a POST (no redirect-after-post), so the
        # obvious fallback of "let cancel.js call history.back()" walks the
        # browser back into an uncached POST navigation. Chrome refuses that
        # outright (ERR_CACHE_MISS) and shows chrome-error://chromewebdata —
        # exactly what a persona hit. Same shape of bug as B1's lock-text
        # link (a signpost with no route back to where the operator came
        # from), so it gets B1's fix: a real URL to the filtered changelist,
        # built with ``?q=`` when every selected ticket shares one query
        # term, so Cancel returns to the row(s) the operator was working
        # from rather than the unfiltered, thousands-deep list.
        changelist_url = reverse(
            f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_changelist"
        )
        query_terms = {
            (ticket.attendee.last_name or ticket.attendee.first_name).strip()
            for ticket in tickets
        }
        query_terms.discard("")
        if len(query_terms) == 1:
            changelist_url = (
                f"{changelist_url}?{urlencode({'q': next(iter(query_terms))})}"
            )
        cancel_url = changelist_url

        submitted = "preview" in request.POST or "apply" in request.POST
        # B4: each selected ticket's own current type is excluded from step
        # 1's dropdown — plan_ticket_type_change always rejects "already on
        # this type", so offering it here is a choice guaranteed to fail on
        # the next screen. A mixed selection excludes the union of their
        # current types.
        exclude_ticket_type_ids = {
            ticket.ticket_type_id for ticket in tickets if ticket.ticket_type_id
        }
        form = ChangeTicketTypeForm(
            request.POST if submitted else None,
            event=event,
            exclude_ticket_type_ids=exclude_ticket_type_ids,
        )

        plans = []
        rejections = []
        acknowledged = False
        if submitted and form.is_valid():
            new_ticket_type = form.cleaned_data["ticket_type"]
            acknowledged = form.cleaned_data["acknowledge_warnings"]
            for ticket in tickets:
                try:
                    plans.append(plan_ticket_type_change(ticket, new_ticket_type))
                except TicketTypeChangeRejected as exc:
                    rejections.append((ticket, str(exc)))

            needs_acknowledgement = any(p.requires_acknowledgement for p in plans)

            if "apply" in request.POST:
                # B3: the server-side rejection inside change_attendee_
                # ticket_type stays the real guarantee — this check only
                # decides whether an unticked submit gets a second chance on
                # the same screen (see below) instead of quietly dropping
                # the whole selection. Gating here, before the write loop,
                # means the common case (nobody wrote anything, because
                # nobody could) never has to be reverse-engineered from
                # per-row skip messages afterwards.
                if needs_acknowledgement and not acknowledged:
                    self.message_user(
                        request,
                        _(
                            "Tick the acknowledgement before confirming. "
                            "Nothing was changed — the selection below is "
                            "unchanged, review the warning(s) and try again."
                        ),
                        messages.ERROR,
                    )
                else:
                    changed = skipped = 0
                    for plan in plans:
                        try:
                            change_attendee_ticket_type(
                                plan.ticket,
                                new_ticket_type=new_ticket_type,
                                changed_by=request.user,
                                acknowledge_warnings=acknowledged,
                            )
                        except (
                            TicketTypeChangeRejected,
                            InvalidPaymentTransition,
                        ) as exc:
                            # Per-row, like every other staff write path
                            # here: a concurrent edit on one ticket must not
                            # abandon the rest.
                            self.message_user(request, str(exc), messages.WARNING)
                            skipped += 1
                            continue
                        log_audit(
                            request,
                            action="event_ticket_type_changed",
                            entity_type="EventTicket",
                            entity_id=str(plan.ticket.id),
                            details={
                                "attendee": str(plan.ticket.attendee),
                                "event": event.name,
                                "from_ticket_type": (
                                    plan.old_ticket_type.name
                                    if plan.old_ticket_type
                                    else None
                                ),
                                "to_ticket_type": plan.new_ticket_type.name,
                                "old_price": (
                                    None
                                    if plan.old_price is None
                                    else str(plan.old_price)
                                ),
                                "new_price": str(plan.new_price),
                                "delta": str(plan.delta),
                                "price_effect": plan.effect.value,
                                "payment_id": (
                                    None
                                    if plan.payment is None
                                    else str(plan.payment.id)
                                ),
                                "age_warning": (
                                    None
                                    if plan.age_warning is None
                                    else str(plan.age_warning)
                                ),
                                # Added alongside age_warning, same shape
                                # (R4/D1, gate review 2026-09-25) — nothing
                                # outside this module and its own test reads
                                # either key, so no dual-write/migration of
                                # old audit rows is needed.
                                "capacity_warning": (
                                    None
                                    if plan.capacity_warning is None
                                    else str(plan.capacity_warning)
                                ),
                                # Renamed from age_warning_acknowledged: one
                                # checkbox now covers every warning on the
                                # plan, not just age (TicketTypeChangePlan.
                                # warnings), so "acknowledged" is a property
                                # of the whole plan, not of age specifically.
                                "warnings_acknowledged": bool(
                                    plan.warnings and acknowledged
                                ),
                            },
                        )
                        changed += 1
                    self.message_user(
                        request,
                        _("%(changed)d ticket(s) changed, %(skipped)d skipped.")
                        % {"changed": changed, "skipped": skipped + len(rejections)},
                        messages.SUCCESS if changed else messages.WARNING,
                    )
                    return None
        else:
            needs_acknowledgement = False

        # B4: one money-formatting path. old_price/new_price/delta are
        # Decimals straight off the plan; format them here rather than in
        # the template so step 1's dropdown (format_balance in the form
        # above) and step 2's preview can never drift into two renderings
        # of the same number — the "1050,00" vs "10 500,00" failure this
        # increment exists to prevent.
        warning_plans = [plan for plan in plans if plan.warnings]
        single_warning_plan = warning_plans[0] if len(warning_plans) == 1 else None
        plan_rows = [
            {
                "plan": plan,
                "old_price": (
                    None if plan.old_price is None else format_balance(plan.old_price)
                ),
                "new_price": format_balance(plan.new_price),
                "delta": (
                    None if plan.old_price is None else format_signed_amount(plan.delta)
                ),
                # B3: the acknowledgement checkbox lives inside the warning
                # banner it belongs to, not as a detached paragraph below
                # the table. The common case is exactly one flagged ticket
                # (this screen is usually worked one child at a time), so it
                # renders inline there; a batch with more than one flagged
                # ticket falls back to a single shared banner after the
                # table (see show_group_ack_banner) — one tick still covers
                # every row's warning, deliberately: batch semantics for
                # per-row acknowledgement are out of scope for this screen.
                "inline_ack": plan is single_warning_plan,
            }
            for plan in plans
        ]

        context = {
            **self.admin_site.each_context(request),
            "title": _("Change ticket type"),
            "queryset": tickets,
            "event": event,
            "form": form,
            "plans": plans,
            "plan_rows": plan_rows,
            "rejections": rejections,
            "is_preview": bool(plans or rejections),
            "needs_acknowledgement": needs_acknowledgement,
            "show_group_ack_banner": needs_acknowledgement
            and single_warning_plan is None,
            "opts": self.model._meta,
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
            "cancel_url": cancel_url,
        }
        return TemplateResponse(
            request,
            "admin/events/eventticket/change_ticket_type.html",
            context,
        )


@admin.register(SessionTicket)
class SessionTicketAdmin(TicketTriageMixin, TicketTypeGuardMixin, admin.ModelAdmin):
    """
    Admin interface for session tickets.
    """

    list_display = (
        "attendee",
        "family",
        "age_at_event",
        "session",
        "ticket_type_name",
        "registration_status",
        "external_ticket_code",
    )
    list_filter = (
        "session__event",
        ("ticket_type", TicketTypeListFilter),
        AgeFitListFilter,
    )
    search_fields = (
        "attendee__first_name",
        "attendee__last_name",
        "attendee__family__last_name",
        "external_ticket_code",
        "session__name",
        "session__event__name",
    )
    # session__event: Session.__str__ interpolates the event name, so the
    # `session` column needs the join even with the separate `event` column
    # gone (R8, revision round 1 — see TicketTriageMixin.ticket_type_name).
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

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        self._warn_if_age_window_uncheckable(request, obj)

    def _warn_if_age_window_uncheckable(self, request, obj):
        """Warn, don't block (owner's decision — see the increment that
        added this). This must agree with
        ``registrations.services.UNCHECKABLE_AGE_FIT_Q``: an age window can
        only ever be evaluated against a ``Child`` row's birthdate (see
        ``_age_warning_for``'s ``ObjectDoesNotExist`` branch — a ``Parent``
        attendee has no ``.child`` at all, so the comparison never runs for
        one). ``applies_to == PARENT`` steers the public form to hand this
        ticket type only to parent attendees, so a configured window on such
        a type is never actually evaluated through that front door — it
        looks constraining but constrains nothing. Staff can still
        hand-assign the type to a child in the admin regardless of
        ``applies_to`` (see the field's help_text), which *would* make the
        window checkable again; the warning is about the configuration as
        given, not about every possible override.
        """
        has_window = obj.min_birthdate is not None or obj.max_birthdate is not None
        if has_window and obj.applies_to == AppliesTo.PARENT:
            self.message_user(
                request,
                _(
                    '"%(name)s" applies only to parents, but has an age '
                    "window configured (Minimum/Maximum Birthdate). Age is "
                    "only ever checked for attendees registered as a "
                    "child, so this window will never actually be "
                    "evaluated for a parent-only ticket type — it "
                    "constrains nothing as configured."
                )
                % {"name": obj.name},
                level=messages.WARNING,
            )


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
class ExtraChoiceAdmin(HiddenFromIndexAdmin, admin.ModelAdmin):
    """Standalone registration alongside the ExtraAdmin inline above —
    needed so RegistrationExtraAdmin.choice can use autocomplete_fields
    (Django requires the target model have its own registered ModelAdmin
    with search_fields, inlines don't count).

    Hidden from the index (see HiddenFromIndexAdmin) precisely because it
    exists for that autocomplete and for ExtraChoiceInline on ExtraAdmin —
    nobody navigates to it. Do not unregister it: that breaks the widget."""

    list_display = ("label", "extra", "price_delta", "is_active", "sort_order")
    list_filter = ("extra__event", "is_active")
    search_fields = ("label", "extra__name")
    autocomplete_fields = ["extra"]
