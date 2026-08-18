import secrets
import uuid

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def generate_printer_token() -> str:
    """Generate a secure, URL-safe bearer token for a printer client."""
    return secrets.token_urlsafe(32)


class Printer(models.Model):
    # Provisioned server-side (staff creates the printer, then configures the
    # client with the returned token). Historically the client self-registered
    # an arbitrary UUID; that path is gone — a printer now authenticates with a
    # revocable token bound to this row.
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name=_("Name"))
    is_online = models.BooleanField(default=False, verbose_name=_("Online"))
    last_seen_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Last Seen At")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    # Per-printer auth token (plaintext: the operator copies it once into the
    # printer-client config, and the client presents it on every connection).
    token = models.CharField(
        max_length=64,
        unique=True,
        default=generate_printer_token,
        verbose_name=_("Token"),
    )
    token_created_at = models.DateTimeField(
        default=timezone.now, verbose_name=_("Token Created At")
    )
    token_revoked_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Token Revoked At")
    )

    def __str__(self):
        status = "online" if self.is_online else "offline"
        return f"{self.name} ({status})"

    @property
    def token_active(self) -> bool:
        """True if the current token is usable (not revoked)."""
        return self.token_revoked_at is None

    def rotate_token(self) -> str:
        """Issue a fresh token, invalidating the previous one. Returns it."""
        self.token = generate_printer_token()
        self.token_created_at = timezone.now()
        self.token_revoked_at = None
        self.save(update_fields=["token", "token_created_at", "token_revoked_at"])
        return self.token

    def revoke_token(self) -> None:
        """Disable the current token without issuing a new one."""
        self.token_revoked_at = timezone.now()
        self.save(update_fields=["token_revoked_at"])

    class Meta:
        ordering = ["name"]
        verbose_name = _("Printer")
        verbose_name_plural = _("Printers")


class PrintJob(models.Model):
    STATUS_PENDING = "pending"
    STATUS_SENT = "sent"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"

    STATUS = [
        (STATUS_PENDING, _("Pending")),
        (STATUS_SENT, _("Sent")),
        (STATUS_COMPLETED, _("Completed")),
        (STATUS_FAILED, _("Failed")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    checkin = models.ForeignKey(
        "checkins.CheckInRecord",
        on_delete=models.CASCADE,
        related_name="print_jobs",
        verbose_name=_("Check-In Record"),
    )
    printer = models.ForeignKey(
        Printer,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="print_jobs",
        verbose_name=_("Printer"),
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default=STATUS_PENDING,
        verbose_name=_("Status"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Sent At"))
    completed_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Completed At")
    )

    def __str__(self):
        return f"PrintJob {self.id} [{self.status}]"

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Print Job")
        verbose_name_plural = _("Print Jobs")
