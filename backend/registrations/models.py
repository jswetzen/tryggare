import uuid
from datetime import timedelta
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .tokens import generate_unique_reference_code

ZERO = Decimal("0")

# Output type for the SQL balance expression (see Payment.balance_expression).
# Wider than Payment.amount's own 8 digits because the expression sums an
# unbounded number of ledger rows before subtracting; the individual amounts
# are still constrained by their own fields.
BALANCE_FIELD = DecimalField(max_digits=12, decimal_places=2)

# How long an unverified registration is kept before the scheduled sweep
# hard-deletes it. A fixed business rule, not an operator-tunable setting.
REGISTRATION_TTL_HOURS = 48

# How long a verified-but-unpaid registration is kept before the scheduled
# sweep cancels it. Also a fixed business rule. Deliberately days, not hours —
# unlike an unverified submission (spam-shaped, no real relationship yet), a
# pending_payment registration already passed email verification and
# represents a real family; giving them a week to pay before cancelling
# balances "don't hold a check-in-invalid slot forever" against "don't
# cancel over a bank transfer that takes a couple of days to clear."
PAYMENT_TTL_DAYS = 7


def default_expires_at():
    return timezone.now() + timedelta(hours=REGISTRATION_TTL_HOURS)


def default_payment_expires_at():
    return timezone.now() + timedelta(days=PAYMENT_TTL_DAYS)


class Registration(models.Model):
    """
    Groups the tickets produced by one public self-serve submission.

    Family/Parent/Child/ticket rows are materialized immediately at
    submission (status=pending_verification) rather than deferred — see the
    Track 1 plan for why (keeps special-category child data inside every
    existing compliance mechanism: export/erase, scrub_family, the
    Child.save() consent-invariant backstop, audit logging).
    """

    class Status(models.TextChoices):
        PENDING_VERIFICATION = "pending_verification", _("Pending email verification")
        CONFIRMED = "confirmed", _("Confirmed")
        PENDING_PAYMENT = "pending_payment", _("Pending payment")  # phase 2
        PENDING_REVIEW = "pending_review", _("Pending staff review")
        CANCELLED = "cancelled", _("Cancelled")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        "events.Event",
        on_delete=models.CASCADE,
        related_name="registrations",
        verbose_name=_("Event"),
    )
    family = models.ForeignKey(
        "families.Family",
        on_delete=models.CASCADE,
        related_name="registrations",
        verbose_name=_("Family"),
        help_text=_("The family materialized by this submission."),
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.PENDING_VERIFICATION,
        verbose_name=_("Status"),
    )
    reference_code = models.CharField(
        max_length=8,
        unique=True,
        default=generate_unique_reference_code,
        verbose_name=_("Reference Code"),
        help_text=_("Short code shown to the guardian for support lookups."),
    )
    contact_email = models.EmailField(verbose_name=_("Contact Email"))
    verification_token_hash = models.CharField(
        max_length=64,
        unique=True,
        verbose_name=_("Verification Token Hash"),
        help_text=_("SHA-256 hash of the one-time token sent by email."),
    )
    verified_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Verified At")
    )
    submitted_at = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Submitted At")
    )
    verification_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Verification Email Last Sent At"),
        help_text=_("Tracks the resend cooldown for a still-pending registration."),
    )
    expires_at = models.DateTimeField(
        default=default_expires_at,
        verbose_name=_("Expires At"),
        help_text=_(
            "When this registration becomes eligible for the expiry sweep — "
            "the verification TTL while pending_verification, reset to the "
            "payment TTL when entering pending_payment."
        ),
    )
    created_new_family = models.BooleanField(
        default=True,
        verbose_name=_("Created New Family"),
        help_text=_(
            "True if this submission materialized a brand-new family (the phase-1 "
            "default). The expiry sweep only hard-deletes the family/children/"
            "tickets it created — it must never delete a pre-existing family."
        ),
    )
    promo_code = models.ForeignKey(
        "events.PromoCode",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="registrations",
        verbose_name=_("Promo Code"),
    )
    discount_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        verbose_name=_("Discount Amount"),
        help_text=_(
            "Snapshotted once at submission (P2) — never recomputed, even "
            "if the promo code is edited afterwards."
        ),
    )

    class Meta:
        db_table = "registrations"
        verbose_name = _("Registration")
        verbose_name_plural = _("Registrations")
        indexes = [
            models.Index(fields=["status", "expires_at"]),
            models.Index(fields=["event", "contact_email"]),
        ]

    def __str__(self) -> str:
        return f"Registration {self.reference_code} ({self.status})"

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at


class Payment(models.Model):
    """
    The single payment record for a paid-event Registration.

    A OneToOne, not a FK: a family registration is paid as one lump sum (per
    payment_processing.md), so there is at most one Payment per Registration.
    Created lazily by verify_registration() once a paid event's registration
    is actually verified — never at submission time, so an unverified/
    spam-shaped submission never gets a Payment row.
    """

    class Method(models.TextChoices):
        SWISH = "swish", _("Swish")
        BANKGIRO = "bankgiro", _("Bankgiro")
        MANUAL_OTHER = "manual_other", _("Other (manual)")

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        PARTIALLY_PAID = "partially_paid", _("Partially paid")
        PAID = "paid", _("Paid")
        REFUNDED = "refunded", _("Refunded")
        CANCELLED = "cancelled", _("Cancelled")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    registration = models.OneToOneField(
        Registration,
        on_delete=models.CASCADE,
        related_name="payment",
        verbose_name=_("Registration"),
    )
    amount = models.DecimalField(
        max_digits=8, decimal_places=2, verbose_name=_("Amount")
    )
    currency = models.CharField(max_length=3, default="SEK", verbose_name=_("Currency"))
    method = models.CharField(
        max_length=20,
        choices=Method.choices,
        blank=True,
        default="",
        verbose_name=_("Method"),
        help_text=_(
            "Set only once marked paid — a guardian may pay via either rail, "
            "so it isn't known in advance."
        ),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("Status"),
    )
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Paid At"))
    marked_by = models.ForeignKey(
        "accounts.AdminUser",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="payments_marked",
        verbose_name=_("Marked By"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        db_table = "payments"
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")
        indexes = [models.Index(fields=["status"])]

    def __str__(self) -> str:
        return f"Payment for {self.reference_code} ({self.status})"

    @property
    def reference_code(self) -> str:
        return self.registration.reference_code

    def ledger_totals(self) -> tuple[Decimal, Decimal, Decimal]:
        """Cumulative (received, refunded, adjusted) from the PaymentEvent
        ledger — the shared read both ``balance`` and
        ``services.record_payment_event``'s C1 invariant checks build on.
        One query with three conditional aggregates, not three separate
        round trips — this runs per admin changelist row and multiple times
        per mark-paid call."""
        totals = self.events.aggregate(
            received=Sum("amount", filter=Q(kind=PaymentEvent.Kind.RECEIVED)),
            refunded=Sum("amount", filter=Q(kind=PaymentEvent.Kind.REFUNDED)),
            adjusted=Sum("amount", filter=Q(kind=PaymentEvent.Kind.ADJUSTMENT)),
        )
        return (
            totals["received"] or ZERO,
            totals["refunded"] or ZERO,
            totals["adjusted"] or ZERO,
        )

    @property
    def balance(self) -> Decimal:
        """Amount still owed: amount minus what the PaymentEvent ledger says
        has actually happened. received reduces it; refunded and adjustment
        (a goodwill write-off — no money moves) increase and reduce it
        respectively per their real-world meaning: a refund gives money back
        to the payer, so it reopens the balance; an adjustment writes off
        part of what's owed."""
        received, refunded, adjusted = self.ledger_totals()
        return self.amount - received + refunded - adjusted

    # The SQL twin of ``balance`` above, and deliberately its immediate
    # neighbour: two implementations of one number that can silently
    # disagree is the hazard, so they are read and edited together.
    # ``balance`` stays the source of truth — this exists only because a
    # Python property cannot be filtered or, crucially, *sorted* by, and
    # "who owes the most on this event" is a sort.
    #
    # Named ``outstanding_balance``, not ``balance``: Django assigns an
    # annotation onto each instance with setattr(), and ``balance`` is a
    # property with no setter, so annotating under that name raises
    # AttributeError the moment the queryset is iterated.
    BALANCE_ANNOTATION = "outstanding_balance"

    @staticmethod
    def balance_expression():
        """``amount - received + refunded - adjusted``, expressed over the
        PaymentEvent join so the database computes it once for the whole
        page instead of once per row. Kept sign-for-sign identical to
        ``balance``; ``PaymentBalanceAnnotationTests`` pins the two
        together across the empty/partial/refund/adjustment/overpayment
        cases."""

        def ledger_sum(kind):
            return Coalesce(
                Sum("events__amount", filter=Q(events__kind=kind)),
                Value(ZERO),
                output_field=BALANCE_FIELD,
            )

        return ExpressionWrapper(
            F("amount")
            - ledger_sum(PaymentEvent.Kind.RECEIVED)
            + ledger_sum(PaymentEvent.Kind.REFUNDED)
            - ledger_sum(PaymentEvent.Kind.ADJUSTMENT),
            output_field=BALANCE_FIELD,
        )

    def recompute_status(self) -> None:
        """Derive and persist status from the ledger. Idempotent; called by
        record_payment_event() inside its transaction. Never touches an
        existing `cancelled` status — that transition belongs to the sweep/
        admin cancel action, not the ledger (see payment_processing.md).

        C1: a fully-refunded payment (everything ever received has since
        been refunded back out) reads as REFUNDED rather than falling into
        the balance-threshold split below — otherwise it lands on PENDING,
        indistinguishable from "never paid" even though real money moved
        twice. Deliberately narrower than "any refund at all": a *partial*
        refund of a fully-paid payment (some of what was received is still
        held) must stay PARTIALLY_PAID, not flip to REFUNDED — see
        tests_payment.py::test_refund_after_confirmed_reopens_balance_
        without_reverting_status."""
        if self.status == self.Status.CANCELLED:
            return

        received, refunded, adjusted = self.ledger_totals()
        balance = self.amount - received + refunded - adjusted

        if refunded > ZERO and refunded >= received:
            new_status = self.Status.REFUNDED
        elif balance <= ZERO:
            new_status = self.Status.PAID
        elif balance < self.amount:
            new_status = self.Status.PARTIALLY_PAID
        else:
            new_status = self.Status.PENDING

        update_fields = []
        if new_status != self.status:
            if new_status == self.Status.PAID and self.status != self.Status.PAID:
                self.paid_at = timezone.now()
                update_fields.append("paid_at")
            self.status = new_status
            update_fields.append("status")
            self.save(update_fields=update_fields)


class PaymentEvent(models.Model):
    """Append-only ledger of money movements against a Payment — the source
    of truth Payment.status/balance are derived from. Nothing ever updates
    or deletes a row (enforced in the admin); a correction is recorded as a
    new offsetting entry, not an edit to history.
    """

    class Kind(models.TextChoices):
        RECEIVED = "received", _("Received")
        REFUNDED = "refunded", _("Refunded")
        ADJUSTMENT = "adjustment", _("Adjustment")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name="events",
        verbose_name=_("Payment"),
    )
    kind = models.CharField(max_length=20, choices=Kind.choices, verbose_name=_("Kind"))
    amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name=_("Amount"),
        help_text=_(
            "Always positive — kind determines the sign of its effect on "
            "the payment's balance."
        ),
    )
    note = models.CharField(
        max_length=255, blank=True, default="", verbose_name=_("Note")
    )
    created_by = models.ForeignKey(
        "accounts.AdminUser",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="payment_events_recorded",
        verbose_name=_("Created By"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        db_table = "payment_events"
        verbose_name = _("Payment Event")
        verbose_name_plural = _("Payment Events")
        indexes = [models.Index(fields=["payment"])]

    def __str__(self) -> str:
        return f"{self.kind} {self.amount} {self.payment.currency} for {self.payment.reference_code}"


class RegistrationExtra(models.Model):
    """One extra (T-shirt, lunch, a shared cabin) attached to a Registration
    — either to one attendee (``attendee`` set) or to the registration as a
    whole (``attendee`` null, e.g. a shared cabin).

    The unique constraint below is the row-level guard against the
    double-tap/two-tab duplicate-submission case: the same per-attendee
    extra can't be attached to the same attendee twice.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    registration = models.ForeignKey(
        Registration,
        on_delete=models.CASCADE,
        related_name="extras",
        verbose_name=_("Registration"),
    )
    extra = models.ForeignKey(
        "events.Extra",
        on_delete=models.PROTECT,
        related_name="registration_extras",
        verbose_name=_("Extra"),
    )
    attendee = models.ForeignKey(
        "families.Attendee",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="registration_extras",
        verbose_name=_("Attendee"),
        help_text=_("Null for a per-registration extra (extra.per_attendee=False)."),
    )
    choice = models.ForeignKey(
        "events.ExtraChoice",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="registration_extras",
        verbose_name=_("Choice"),
    )
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name=_("Quantity"),
        help_text=_(
            "Only >1 allowed for a per-registration extra (per_attendee=False)."
        ),
    )
    price_at_registration = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name=_("Price At Registration"),
        help_text=_(
            "Snapshotted per-unit price (extra.price + choice.price_delta) "
            "at submission time — never recomputed afterwards."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        db_table = "registration_extras"
        verbose_name = _("Registration Extra")
        verbose_name_plural = _("Registration Extras")
        constraints = [
            models.UniqueConstraint(
                fields=["registration", "extra", "attendee"],
                name="unique_registration_extra_attendee",
            )
        ]
        indexes = [models.Index(fields=["registration"])]

    def __str__(self) -> str:
        return f"{self.extra.name} for {self.registration.reference_code}"
