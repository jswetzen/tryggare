import uuid
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import (
    DecimalField,
    ExpressionWrapper,
    F,
    OuterRef,
    Q,
    Subquery,
    Sum,
    Value,
)
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

    ``expires_at`` is when the row becomes eligible for the expiry sweep:
    the verification TTL (REGISTRATION_TTL_HOURS) while
    status=pending_verification, reset to the payment TTL (PAYMENT_TTL_DAYS)
    on entering pending_payment.

    ``created_new_family`` is True when the submission materialized a
    brand-new family (the phase-1 default). The expiry sweep only
    hard-deletes the family/children/tickets it created — it must never
    delete a pre-existing family.

    ``discount_amount`` is snapshotted once at submission (P2) and never
    recomputed, even if the promo code is edited afterwards.
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
        help_text=_("The family this registration belongs to."),
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
            "When an unfinished registration is removed automatically. The "
            "deadline is extended once the guardian confirms their email "
            "address, to give them time to pay."
        ),
    )
    created_new_family = models.BooleanField(
        default=True,
        verbose_name=_("Created New Family"),
        help_text=_(
            "Checked when this registration created a new family. If it is "
            "removed for being unfinished, only the family and tickets it "
            "created go with it — an existing family is never touched."
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
            "The discount this registration was given. Editing the promo "
            "code afterwards is safe — it does not change what this family "
            "was charged."
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

    def ledger_totals(self) -> tuple[Decimal, Decimal, Decimal, Decimal]:
        """Cumulative (received, refunded, adjusted, charged) from the
        PaymentEvent ledger — the shared read both ``balance`` and
        ``services.record_payment_event``'s C1 invariant checks build on.
        One query with four conditional aggregates, not four separate
        round trips — this runs per admin changelist row and multiple times
        per mark-paid call."""
        totals = self.events.aggregate(
            received=Sum("amount", filter=Q(kind=PaymentEvent.Kind.RECEIVED)),
            refunded=Sum("amount", filter=Q(kind=PaymentEvent.Kind.REFUNDED)),
            adjusted=Sum("amount", filter=Q(kind=PaymentEvent.Kind.ADJUSTMENT)),
            charged=Sum("amount", filter=Q(kind=PaymentEvent.Kind.CHARGED)),
        )
        return (
            totals["received"] or ZERO,
            totals["refunded"] or ZERO,
            totals["adjusted"] or ZERO,
            totals["charged"] or ZERO,
        )

    @property
    def balance(self) -> Decimal:
        """Amount still owed: amount minus what the PaymentEvent ledger says
        has actually happened. received reduces it; refunded and charged
        (money coming back, or more being asked for) increase it; adjustment
        (a goodwill write-off — no money moves) reduces it. Charged is the
        mirror image of adjustment — both are ledger-only entries with no
        money movement of their own, but a charge raises what's owed while
        an adjustment writes part of it off."""
        received, refunded, adjusted, charged = self.ledger_totals()
        return self.amount - received + refunded - adjusted + charged

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
    def balance_expression(prefix: str = ""):
        """``amount - received + refunded - adjusted + charged``, expressed
        over the PaymentEvent join so the database computes it once for the
        whole page instead of once per row. Kept sign-for-sign identical to
        ``balance``; ``PaymentBalanceAnnotationTests`` pins the two
        together across the empty/partial/refund/adjustment/charge/
        overpayment cases.

        ``prefix`` lets a caller build the same expression from a queryset
        that isn't rooted on Payment itself — e.g. Registration, annotating
        via ``Payment.balance_expression(prefix="payment__")`` so a
        registration changelist can show/sort/filter by outstanding balance
        without a second, drift-prone reimplementation of this arithmetic."""

        def field(name: str) -> str:
            return f"{prefix}{name}"

        def ledger_sum(kind):
            return Coalesce(
                Sum(field("events__amount"), filter=Q(**{field("events__kind"): kind})),
                Value(ZERO),
                output_field=BALANCE_FIELD,
            )

        return ExpressionWrapper(
            F(field("amount"))
            - ledger_sum(PaymentEvent.Kind.RECEIVED)
            + ledger_sum(PaymentEvent.Kind.REFUNDED)
            - ledger_sum(PaymentEvent.Kind.ADJUSTMENT)
            + ledger_sum(PaymentEvent.Kind.CHARGED),
            output_field=BALANCE_FIELD,
        )

    @staticmethod
    def balance_subquery(outer_field: str = "registration_id", outer_ref: str = "pk"):
        """A correlated-subquery twin of ``balance_expression`` — same
        arithmetic, computed inside its own isolated ``SELECT`` instead of
        as a join on whatever queryset it's annotated onto.

        The join-based ``balance_expression`` is only safe as long as
        nothing else in the same top-level query joins a *second*
        multi-valued relation — the admin's search across
        ``family__attendees__*`` does exactly that, and the combination
        silently multiplies every ``PaymentEvent`` row by the attendee
        fan-out (confirmed: a 4-attendee family owing 2300,00 rendered
        -700,00 kr under search). A correlated subquery can't be touched by
        joins the outer query adds — it runs as its own statement, executed
        once per outer row by the database, not as an extra join clause —
        so it's the version to use on any queryset whose search_fields or
        list_filter might reach a one-to-many relation.

        Defaults correlate a queryset rooted on ``Registration`` (its own
        ``pk`` against ``Payment.registration_id``); pass ``outer_field``/
        ``outer_ref`` to correlate a queryset rooted elsewhere, e.g.
        ``family_balance_subquery`` below composing this one level up."""
        inner = (
            Payment.objects.filter(**{outer_field: OuterRef(outer_ref)})
            .order_by()
            .annotate(_balance=Payment.balance_expression())
            .values("_balance")
        )
        return Subquery(inner, output_field=BALANCE_FIELD)

    @staticmethod
    def family_balance_subquery():
        """Sum of outstanding balance across every one of a family's
        registrations — for the family changelist (R6).

        Family -> registrations is already one-to-many, so a join-based
        ``Sum`` here would double-count exactly like R1, one relation up:
        stack that join under FamilyAdmin's own ``attendees__*`` search
        join and every ledger row gets multiplied by the attendee fan-out
        *again*, on top of the registration fan-out. Composing two
        correlated subqueries — ``balance_subquery`` per registration,
        summed per family, both isolated from the outer query's own joins
        — is what keeps this arithmetic correct regardless of what the
        family changelist's search reaches. See
        ``registrations/tests_registration_changelist.py`` for the
        DB-verified proof (a 4-attendee, multi-registration family, summed
        under search) and ``Payment.balance_subquery`` above for why a join
        can't be trusted to sit next to a search join."""
        inner = (
            Registration.objects.filter(family_id=OuterRef("pk"))
            .order_by()
            .annotate(_balance=Payment.balance_subquery())
            .values("family_id")
            .annotate(
                total=Coalesce(Sum("_balance"), Value(ZERO), output_field=BALANCE_FIELD)
            )
            .values("total")
        )
        return Subquery(inner, output_field=BALANCE_FIELD)

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
        without_reverting_status. Unaffected by CHARGED: that check only
        looks at refunded vs received, neither of which a charge touches.

        The PARTIALLY_PAID/PENDING split below compares the balance against
        the *effective* total owed (``amount + charged``), not against
        ``amount`` alone — a charge raises what's owed the same way the
        original ``amount`` did, so with no payments yet the balance sits at
        the full effective total (PENDING), and any money moving away from
        that (in either direction) reads as PARTIALLY_PAID."""
        if self.status == self.Status.CANCELLED:
            return

        received, refunded, adjusted, charged = self.ledger_totals()
        total_owed = self.amount + charged
        balance = total_owed - received + refunded - adjusted

        if refunded > ZERO and refunded >= received:
            new_status = self.Status.REFUNDED
        elif balance <= ZERO:
            new_status = self.Status.PAID
        elif balance < total_owed:
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
        CHARGED = "charged", _("Charge")

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
        max_length=255,
        blank=True,
        default="",
        verbose_name=_("Note"),
        help_text=_(
            "Free text for any event. Mandatory for a Charge — raising what "
            "a family owes must always say why."
        ),
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
        constraints = [
            # A charge must carry a reason — the ledger must never again
            # record an amount moving with nothing behind it. A
            # CheckConstraint is enforced at the database, so it is the one
            # guard a raw PaymentEvent.objects.create() (bypassing clean(),
            # bypassing a ModelForm) cannot slip past. clean()/save() below
            # give the friendlier ValidationError first; this is the
            # backstop.
            models.CheckConstraint(
                check=~Q(kind="charged", note=""),
                name="payment_event_charge_requires_note",
                violation_error_message=_(
                    "A charge must include a reason in its note."
                ),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.kind} {self.amount} {self.payment.currency} for {self.payment.reference_code}"

    def clean(self):
        super().clean()
        if self.kind == self.Kind.CHARGED and not self.note.strip():
            raise ValidationError(
                {
                    "note": _(
                        "A charge must include a reason — say why the family owes more."
                    )
                }
            )

    def save(self, *args, **kwargs):
        # Belt-and-suspenders with the CheckConstraint above: full_clean()
        # here catches a missing charge reason with a friendly
        # ValidationError before it ever reaches the database, for the
        # in-process callers (record_payment_event, and anything else that
        # constructs a PaymentEvent directly) that never go through a
        # ModelForm's own clean/validation. update_fields is never used for
        # this model (append-only: rows are created, never edited — see the
        # admin's has_change_permission), so there is no partial-save case
        # where re-validating unrelated fields would be wrong.
        self.full_clean()
        super().save(*args, **kwargs)


class RegistrationExtra(models.Model):
    """One extra (T-shirt, lunch, a shared cabin) attached to a Registration
    — either to one attendee (``attendee`` set) or to the registration as a
    whole (``attendee`` null, e.g. a shared cabin).

    The unique constraint below is the row-level guard against the
    double-tap/two-tab duplicate-submission case: the same per-attendee
    extra can't be attached to the same attendee twice.

    ``attendee`` is null exactly when ``extra.per_attendee`` is False, and
    only such a per-registration extra may carry ``quantity`` > 1.

    ``price_at_registration`` is the per-unit price
    (``extra.price + choice.price_delta``) snapshotted at submission time
    and never recomputed afterwards — the same snapshot discipline as
    EventTicket/SessionTicket, which is what makes mid-sale price edits
    safe (case catalog §9.4).
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
        help_text=_(
            "Leave blank for an extra that belongs to the whole booking "
            "rather than to one attendee."
        ),
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
            "More than 1 is only allowed for an extra that belongs to the "
            "whole booking rather than to one attendee."
        ),
    )
    price_at_registration = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name=_("Price At Registration"),
        help_text=_(
            "The price per unit this extra was sold at. Editing a price is "
            "safe — extras already sold keep the price they were sold at."
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
