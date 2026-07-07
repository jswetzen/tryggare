from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from checkins.audit import log_audit

from .models import Payment, Registration
from .services import InvalidPaymentTransition, mark_payment_paid


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
    )
    actions = [
        "cancel_registrations",
        "mark_paid_swish",
        "mark_paid_bankgiro",
        "mark_paid_other",
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


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Finance-only search/filter across all payments. The core "mark as
    paid" workflow lives on RegistrationAdmin above — this is a secondary
    view for browsing, reusing the same service function so both surfaces
    stay consistent."""

    list_display = (
        "reference_code",
        "registration",
        "amount",
        "currency",
        "method",
        "status",
        "paid_at",
        "marked_by",
    )
    list_filter = ("status", "method")
    search_fields = ("registration__reference_code", "registration__contact_email")
    readonly_fields = ("id", "registration", "created_at")
    actions = ["mark_paid_swish", "mark_paid_bankgiro", "mark_paid_other"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("registration", "marked_by")

    @admin.display(description=_("Reference Code"))
    def reference_code(self, obj):
        return obj.reference_code

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
