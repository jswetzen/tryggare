from django.contrib import admin
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


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = (
        "reference_code",
        "event",
        "contact_email",
        "status",
        "submitted_at",
        "verified_at",
    )
    list_filter = ("status", "event")
    search_fields = ("reference_code", "contact_email")
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
        return super().get_queryset(request).select_related("event", "family")

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
        self.message_user(request, _(f"{updated} registration(s) cancelled."))

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
    materialization happens through the public submission flow, not here."""

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
