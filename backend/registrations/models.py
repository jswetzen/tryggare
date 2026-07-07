import uuid
from datetime import timedelta

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .tokens import generate_unique_reference_code

# How long an unverified registration is kept before the scheduled sweep
# hard-deletes it. A fixed business rule, not an operator-tunable setting.
REGISTRATION_TTL_HOURS = 48


def default_expires_at():
    return timezone.now() + timedelta(hours=REGISTRATION_TTL_HOURS)


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
            "When an unverified registration becomes eligible for the expiry sweep."
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
