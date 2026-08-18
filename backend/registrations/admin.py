from decimal import Decimal

from django.contrib import admin, messages
from django.contrib.admin.exceptions import DisallowedModelAdminLookup
from django.db.models import Q
from django.shortcuts import redirect
from django.utils import translation
from django.utils.formats import date_format, number_format
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from checkins.audit import log_audit

from .models import Payment, PaymentEvent, Registration, RegistrationExtra
from .services import (
    InvalidPaymentTransition,
    confirm_registration_despite_balance,
    mark_payment_paid,
    record_payment_event,
    release_promo_code_use,
    resolve_pending_review,
)

ZERO = Decimal("0")


def format_balance(amount: Decimal) -> str:
    """sv-SE money: decimal comma, non-breaking-space thousands separator,
    unit last — "1 900,00 kr", not "1900,00 kr" (the two are one glyph
    apart and that glyph is the only thing separating 1050,00 from
    10 500,00). Forced to the ``sv`` locale regardless of the admin's own
    active display language (the language switcher lets staff read the
    chrome in English while amounts stay in kronor) via Django's own
    number_format rather than a hand-rolled ``replace(".", ",")``, so
    grouping is never silently dropped."""
    with translation.override("sv"):
        return number_format(amount, decimal_pos=2, force_grouping=True) + " kr"


def format_signed_amount(amount: Decimal) -> str:
    """Same sv-SE money rule as format_balance, prefixed with an explicit
    sign — "+300,00 kr" / "−300,00 kr" — so a price *delta* on the
    change-ticket-type wizard reads as a direction without the operator
    doing the arithmetic themselves. The minus is U+2212 (MINUS SIGN), not
    an ASCII hyphen, to visually match the plus glyph's width."""
    if amount > ZERO:
        return f"+{format_balance(amount)}"
    if amount < ZERO:
        return f"−{format_balance(-amount)}"
    return format_balance(amount)


def render_balance(amount: Decimal | None):
    """Three states, not two (R3): a negative balance is a credit, not a
    smaller debt, and the "remaining to pay" wording is a contradiction for
    it — the "Skuld kvar / Reglerad" filter used to file it under Reglerad
    too, silently burying a real overpayment. Positive renders as the
    amount; zero renders muted, quieter than a debt so the eye can skip it
    while scanning; negative renders worded as a credit and visually
    flagged, using Django admin's own CSS custom properties (this is admin
    chrome, not the Tailwind app) rather than a hard-coded colour.

    Also where the R2 column-width fix lives at the cell level: right-
    aligned, tabular-nums, with a min-width sized to the longest plausible
    figure, so a number's end is never off the edge of its cell."""
    if amount is None:
        return "—"
    style = (
        "display:inline-block;min-width:6.5em;text-align:right;"
        "font-variant-numeric:tabular-nums;"
    )
    if amount > ZERO:
        return format_html('<span style="{}">{}</span>', style, format_balance(amount))
    if amount == ZERO:
        return format_html(
            '<span style="{}color:var(--body-quiet-color);">{}</span>',
            style,
            format_balance(amount),
        )
    return format_html(
        '<span style="{}color:var(--error-fg);font-weight:600;">{}</span>',
        style,
        _("%(amount)s credit") % {"amount": format_balance(-amount)},
    )


class RecoverableChangelistMixin:
    """A hand-edited changelist URL (a bookmarked/typed filter on a field
    that isn't in ``list_filter``/``search_fields``) raises
    ``DisallowedModelAdminLookup``, which Django's generic exception handler
    turns into a bare, unstyled 400 with no way back into the admin —
    whoever hits it has lost their place entirely. Catch it here and bounce
    back to the plain changelist with an explanation instead."""

    def changelist_view(self, request, extra_context=None):
        try:
            return super().changelist_view(request, extra_context=extra_context)
        except DisallowedModelAdminLookup:
            self.message_user(
                request,
                _(
                    "That link used a search or filter this page doesn't "
                    "support. Showing the full list instead."
                ),
                level=messages.WARNING,
            )
            return redirect(request.path)


def _mark_paid_action(method, description):
    @admin.action(description=description)
    def action(self, request, queryset):
        paid = skipped = 0
        for registration in queryset.select_related("payment"):
            payment = getattr(registration, "payment", None)
            if payment is None:
                skipped += 1
                continue
            try:
                mark_payment_paid(payment, method=method, marked_by=request.user)
            except InvalidPaymentTransition:
                skipped += 1
                continue
            log_audit(
                request,
                action="registration_payment_marked_paid",
                entity_type="Registration",
                entity_id=str(registration.id),
                details={
                    "reference_code": registration.reference_code,
                    "method": method,
                    "amount": str(payment.amount),
                },
            )
            paid += 1
        self.message_user(
            request,
            _("%(paid)d marked paid, %(skipped)d skipped (not pending payment).")
            % {"paid": paid, "skipped": skipped},
        )

    return action


class HasOutstandingBalanceFilter(admin.SimpleListFilter):
    """Answers "who still owes money [for this event]" as a filter rather
    than a manual scan — combine with the existing ``event`` filter to
    reproduce the blind-test's job 3 in one screen."""

    title = _("Balance")
    parameter_name = "balance"

    def lookups(self, request, model_admin):
        return (
            ("owing", _("Owes money")),
            ("settled", _("Settled")),
            ("credit", _("Credit (overpaid)")),
        )

    def queryset(self, request, queryset):
        if self.value() == "owing":
            return queryset.filter(**{f"{Payment.BALANCE_ANNOTATION}__gt": 0})
        if self.value() == "settled":
            return queryset.filter(
                Q(payment__isnull=True) | Q(**{f"{Payment.BALANCE_ANNOTATION}": 0})
            )
        if self.value() == "credit":
            return queryset.filter(**{f"{Payment.BALANCE_ANNOTATION}__lt": 0})
        return queryset


@admin.register(Registration)
class RegistrationAdmin(RecoverableChangelistMixin, admin.ModelAdmin):
    # Money is never the rightmost column (R2, and a recurrence of the same
    # shape that hit "Biljettyp" in increment 1): right after the identity
    # column, where it's inside the ~630px a nav-pinned, filter-open 1280px
    # viewport actually renders before the table scrolls off-screen.
    list_display = (
        "reference_code",
        "balance_display",
        "family_last_name",
        "event",
        "status",
        "activity_date",
    )
    list_filter = ("status", "event", HasOutstandingBalanceFilter)
    # A volunteer is holding a surname, not a reference code — the surname
    # lives on the family and on each attendee (a caller as often gives a
    # child's name as the payer's), not on Registration itself, so the
    # search has to reach through both relations. See the increment's
    # evidence: "Nyström" returned 0 results before this.
    #
    # Safe to reach a multi-valued relation here precisely because the
    # balance below is now a correlated Subquery (Payment.balance_subquery),
    # not a join-based Sum — nothing this search adds can multiply it. See
    # R1: it used to be balance_expression() joined straight onto this
    # queryset, and combined with this exact attendee join it silently
    # multiplied every ledger row by the family's attendee count.
    search_fields = (
        "reference_code",
        "contact_email",
        "family__last_name",
        "family__attendees__first_name",
        "family__attendees__last_name",
    )
    # Money at the top, beside Referenskod and Status (R4) — it used to sit
    # last, below a SHA-256 hash and an expiry timestamp, because readonly
    # fields default to appending in readonly_fields order after every
    # editable field. Explicit ``fields`` is what it takes to reorder that.
    fields = (
        "reference_code",
        "status",
        "balance_on_detail",
        "event",
        "family",
        "contact_email",
        "promo_code",
        "discount_amount",
        "created_new_family",
        "submitted_at",
        "verified_at",
        "verification_sent_at",
        "expires_at",
        "verification_token_hash",
        "id",
    )
    readonly_fields = (
        "id",
        "family",
        "reference_code",
        "verification_token_hash",
        "submitted_at",
        "verified_at",
        "verification_sent_at",
        "expires_at",
        "created_new_family",
        # B1: status now transitions only through service functions (this
        # admin's actions, or the public verify/payment endpoints) — a raw
        # field edit used to be the only escape hatch out of pending_review,
        # and it skipped Payment creation, the confirmation/payment-
        # instructions email, and log_audit.
        "status",
        "balance_on_detail",
    )
    actions = [
        "cancel_registrations",
        "mark_paid_swish",
        "mark_paid_bankgiro",
        "mark_paid_other",
        "confirm_despite_balance",
        "resolve_pending_review_confirm",
        "resolve_pending_review_reject",
    ]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("event", "family", "payment")
            # A correlated Subquery, not a join-based Sum (R1) — see
            # Payment.balance_subquery for why: this queryset's own
            # search_fields join family__attendees__*, a multi-valued
            # relation, and a join-based Sum sitting next to that join
            # multiplies every PaymentEvent row by the attendee fan-out.
            # The subquery runs as its own isolated SELECT, so the attendee
            # join can't touch it, with or without a search term applied.
            .annotate(**{Payment.BALANCE_ANNOTATION: Payment.balance_subquery()})
        )

    @admin.display(description=_("Family"), ordering="family__last_name")
    def family_last_name(self, obj):
        # Raw last_name, not str(Family) — Family.__str__ falls back to
        # querying the family's parents when last_name is blank, which
        # would reintroduce a per-row query on this changelist.
        return obj.family.last_name or "—"

    @admin.display(description=_("Date"), ordering="submitted_at")
    def activity_date(self, obj):
        # R2: "Inskickad"/"Bekräftad" were two full-datetime-to-the-minute
        # columns (170px each) — collapsed into one date-only column.
        # Prefers verified_at (the more recent, more decision-relevant of
        # the two once it exists) and falls back to submitted_at; both
        # remain on the detail page at full precision, this is a scan
        # column, not the record of truth.
        date = obj.verified_at or obj.submitted_at
        return date_format(date, "SHORT_DATE_FORMAT") if date else "—"

    @admin.display(description=_("Balance"), ordering=Payment.BALANCE_ANNOTATION)
    def balance_display(self, obj):
        annotated = getattr(obj, Payment.BALANCE_ANNOTATION, None)
        if annotated is not None:
            return render_balance(annotated)
        payment = getattr(obj, "payment", None)
        return render_balance(payment.balance) if payment else "—"

    # R4: "Outstanding balance" here and "Balance" on the changelist/inline
    # were two Swedish names ("Utestående belopp" / "Kvar att betala") for
    # one quantity. Collapsed to one msgid — "Balance", i.e. "Kvar att
    # betala" — which wins because it says what to do about it.
    @admin.display(description=_("Balance"))
    def balance_on_detail(self, obj):
        payment = getattr(obj, "payment", None)
        return render_balance(payment.balance) if payment else "—"

    @admin.action(description=_("Cancel selected registrations"))
    def cancel_registrations(self, request, queryset):
        registrations = list(
            queryset.exclude(status=Registration.Status.CANCELLED).select_related(
                "payment"
            )
        )
        updated = 0
        for registration in registrations:
            registration.status = Registration.Status.CANCELLED
            registration.save(update_fields=["status"])
            payment = getattr(registration, "payment", None)
            if payment is not None and payment.status == Payment.Status.PENDING:
                payment.status = Payment.Status.CANCELLED
                payment.save(update_fields=["status"])
            release_promo_code_use(registration)
            updated += 1
        self.message_user(
            request,
            _("%(count)d registration(s) cancelled.") % {"count": updated},
        )

    mark_paid_swish = _mark_paid_action(
        Payment.Method.SWISH, _("Mark selected as paid (Swish)")
    )
    mark_paid_bankgiro = _mark_paid_action(
        Payment.Method.BANKGIRO, _("Mark selected as paid (Bankgiro)")
    )
    mark_paid_other = _mark_paid_action(
        Payment.Method.MANUAL_OTHER, _("Mark selected as paid (other)")
    )

    @admin.action(description=_("Confirm despite outstanding balance"))
    def confirm_despite_balance(self, request, queryset):
        confirmed = skipped = 0
        for registration in queryset.select_related("payment"):
            payment = getattr(registration, "payment", None)
            if (
                payment is None
                or registration.status != Registration.Status.PENDING_PAYMENT
            ):
                skipped += 1
                continue
            outstanding = payment.balance
            try:
                confirm_registration_despite_balance(
                    registration, confirmed_by=request.user
                )
            except InvalidPaymentTransition:
                # Re-read under lock inside the service can now reject a row
                # that looked pending_payment in this admin queryset's stale
                # snapshot but was cancelled concurrently (e.g. by the
                # hourly TTL sweep) between the query above and this call.
                skipped += 1
                continue
            log_audit(
                request,
                action="registration_confirmed_despite_balance",
                entity_type="Registration",
                entity_id=str(registration.id),
                details={
                    "reference_code": registration.reference_code,
                    "outstanding_balance": str(outstanding),
                },
            )
            confirmed += 1
        self.message_user(
            request,
            _("%(confirmed)d confirmed, %(skipped)d skipped (not pending payment).")
            % {"confirmed": confirmed, "skipped": skipped},
        )

    def _resolve_pending_review(self, request, queryset, *, action, audit_action):
        resolved = skipped = 0
        for registration in queryset.select_related("payment"):
            try:
                resolve_pending_review(
                    registration, action=action, resolved_by=request.user
                )
            except InvalidPaymentTransition:
                skipped += 1
                continue
            log_audit(
                request,
                action=audit_action,
                entity_type="Registration",
                entity_id=str(registration.id),
                details={"reference_code": registration.reference_code},
            )
            resolved += 1
        self.message_user(
            request,
            _("%(resolved)d resolved, %(skipped)d skipped (not pending review).")
            % {"resolved": resolved, "skipped": skipped},
        )

    @admin.action(description=_("Resolve pending review: confirm"))
    def resolve_pending_review_confirm(self, request, queryset):
        self._resolve_pending_review(
            request,
            queryset,
            action="confirm",
            audit_action="registration_pending_review_confirmed",
        )

    @admin.action(description=_("Resolve pending review: reject (cancel)"))
    def resolve_pending_review_reject(self, request, queryset):
        self._resolve_pending_review(
            request,
            queryset,
            action="reject",
            audit_action="registration_pending_review_rejected",
        )


class PaymentEventInline(admin.TabularInline):
    """Read-only ledger history on the Payment page. Adding a new entry
    happens through PaymentEventAdmin below (one code path through
    record_payment_event), not here — has_add_permission is disabled."""

    model = PaymentEvent
    extra = 0
    fields = ("kind", "amount", "note", "created_by", "created_at")
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Finance-only search/filter across all payments. The core "mark as
    paid" workflow lives on RegistrationAdmin above — this is a secondary
    view for browsing, reusing the same service function so both surfaces
    stay consistent."""

    list_display = (
        "reference_code",
        "registration",
        "event",
        "family",
        "amount",
        "balance_display",
        "currency",
        "method",
        "status",
        "paid_at",
        "marked_by",
    )
    # registration__event is the piece whose absence caused a real incident:
    # asked to fix "someone says they paid but shows as unpaid", a coordinator
    # could not narrow this changelist to one event, found the only
    # outstanding balance in the whole system — belonging to a *different*
    # event — and marked that one paid. RelatedOnlyFieldListFilter rather
    # than the plain related filter, so the sidebar lists only events that
    # actually have payments instead of every event ever created.
    list_filter = (
        "status",
        "method",
        ("registration__event", admin.RelatedOnlyFieldListFilter),
    )
    search_fields = (
        "registration__reference_code",
        "registration__contact_email",
        # Guardians phone in by surname far more often than by reference
        # code; without this, finding "the Lindqvists" required already
        # knowing their code.
        "registration__family__last_name",
    )
    readonly_fields = ("id", "registration", "created_at")
    inlines = [PaymentEventInline]
    actions = ["mark_paid_swish", "mark_paid_bankgiro", "mark_paid_other"]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "registration",
                "registration__event",
                "registration__family",
                "marked_by",
            )
            # The balance used to cost one aggregate query *per rendered row*
            # (Payment.balance -> ledger_totals). Computing it in SQL both
            # flattens that N+1 and makes the column sortable, which is the
            # actual job: "who owes money on this event, biggest first."
            .annotate(**{Payment.BALANCE_ANNOTATION: Payment.balance_expression()})
        )

    @admin.display(description=_("Reference Code"))
    def reference_code(self, obj):
        return obj.reference_code

    @admin.display(description=_("Event"), ordering="registration__event__name")
    def event(self, obj):
        return obj.registration.event.name

    @admin.display(description=_("Family"), ordering="registration__family__last_name")
    def family(self, obj):
        # The raw last_name, not str(Family): Family.__str__ falls back to
        # querying the family's parents when last_name is blank, which would
        # reintroduce a per-row query on this changelist.
        return obj.registration.family.last_name or None

    @admin.display(description=_("Balance"), ordering=Payment.BALANCE_ANNOTATION)
    def balance_display(self, obj):
        # Prefers the annotation from get_queryset; falls back to the
        # property for any caller holding an un-annotated Payment (the
        # shell, tests, a future admin view that builds its own queryset).
        # Not `or obj.balance` — a zero balance is falsy and would silently
        # fall through to the per-row query this annotation exists to kill.
        annotated = getattr(obj, Payment.BALANCE_ANNOTATION, None)
        return obj.balance if annotated is None else annotated

    def _mark_paid(self, request, queryset, method):
        paid = skipped = 0
        for payment in queryset.select_related("registration"):
            try:
                mark_payment_paid(payment, method=method, marked_by=request.user)
            except InvalidPaymentTransition:
                skipped += 1
                continue
            log_audit(
                request,
                action="registration_payment_marked_paid",
                entity_type="Registration",
                entity_id=str(payment.registration_id),
                details={
                    "reference_code": payment.reference_code,
                    "method": method,
                    "amount": str(payment.amount),
                },
            )
            paid += 1
        self.message_user(
            request,
            _("%(paid)d marked paid, %(skipped)d skipped (not pending payment).")
            % {"paid": paid, "skipped": skipped},
        )

    @admin.action(description=_("Mark selected as paid (Swish)"))
    def mark_paid_swish(self, request, queryset):
        self._mark_paid(request, queryset, Payment.Method.SWISH)

    @admin.action(description=_("Mark selected as paid (Bankgiro)"))
    def mark_paid_bankgiro(self, request, queryset):
        self._mark_paid(request, queryset, Payment.Method.BANKGIRO)

    @admin.action(description=_("Mark selected as paid (other)"))
    def mark_paid_other(self, request, queryset):
        self._mark_paid(request, queryset, Payment.Method.MANUAL_OTHER)


@admin.register(PaymentEvent)
class PaymentEventAdmin(admin.ModelAdmin):
    """Where staff record a partial payment, refund, or goodwill adjustment
    — one at a time, since each carries its own amount and note. The fast
    "mark fully paid" bulk actions stay on RegistrationAdmin/PaymentAdmin;
    this is for everything that isn't "pay the exact outstanding balance in
    one shot." Append-only: existing rows can't be edited or deleted — to
    correct a mistake, record an offsetting entry, don't edit history."""

    list_display = ("payment", "kind", "amount", "note", "created_by", "created_at")
    list_filter = ("kind",)
    search_fields = (
        "payment__registration__reference_code",
        "payment__registration__contact_email",
    )
    autocomplete_fields = ["payment"]
    readonly_fields = ("id", "created_by", "created_at")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("payment__registration", "created_by")
        )

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        event = record_payment_event(
            obj.payment,
            kind=obj.kind,
            amount=obj.amount,
            note=obj.note,
            created_by=request.user,
        )
        # obj itself is never saved (record_payment_event creates the real
        # row) — repoint its pk at the row that actually exists, so the
        # admin's post-save redirect/log_addition don't reference a
        # UUID that was never persisted (UUIDField assigns its default
        # at instantiation, not at save).
        obj.id = event.id
        log_audit(
            request,
            action="payment_event_recorded",
            entity_type="Payment",
            entity_id=str(obj.payment_id),
            details={
                "reference_code": obj.payment.reference_code,
                "kind": obj.kind,
                "amount": str(obj.amount),
                "note": obj.note,
            },
        )


@admin.register(RegistrationExtra)
class RegistrationExtraAdmin(admin.ModelAdmin):
    """Finance/logistics browsing (kitchen counts, T-shirt orders) —
    materialization happens through the public submission flow, not here.

    Deliberately NOT hidden from the index, unlike the other add-on models.
    The 0.4 triage plan listed it for hiding on the grounds that it is
    "registered only so another admin's autocomplete works" — that describes
    ExtraChoice, not this. The event/extra list_filter and the select_related
    queryset below exist because someone built this as a browsing surface,
    and until the dedicated extras/logistics screen ships, this is the only
    way to answer "how many size-M shirts do we need". Hiding it would make
    that answerable only by typing a URL no volunteer will type."""

    list_display = (
        "registration",
        "extra",
        "attendee",
        "choice",
        "quantity",
        "price_at_registration",
    )
    list_filter = ("extra__event", "extra")
    search_fields = (
        "registration__reference_code",
        "attendee__first_name",
        "attendee__last_name",
    )
    autocomplete_fields = ["registration", "extra", "attendee", "choice"]
    readonly_fields = ("id", "created_at")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("registration", "extra", "attendee", "choice")
        )
