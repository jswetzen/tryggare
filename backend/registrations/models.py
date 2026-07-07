import uuid
from datetime import timedelta

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .tokens import generate_unique_reference_code

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
