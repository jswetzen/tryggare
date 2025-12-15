import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class CheckInRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    check_in_time = models.DateTimeField(auto_now_add=True, verbose_name=_("Check-In Time"))
    check_out_time = models.DateTimeField(null=True, blank=True, verbose_name=_("Check-Out Time"))
    picked_up_by = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Picked Up By"))
    child = models.ForeignKey("families.Child", related_name="checkin_records", on_delete=models.CASCADE, verbose_name=_("Child"))
    session = models.ForeignKey("events.Session", related_name="checkin_records", on_delete=models.CASCADE, verbose_name=_("Session"))
    check_in_staff = models.ForeignKey(
        "accounts.AdminUser",
        related_name="checkins_performed",
        on_delete=models.PROTECT,
        verbose_name=_("Check-In Staff"),
    )
    check_out_staff = models.ForeignKey(
        "accounts.AdminUser",
        related_name="checkouts_performed",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("Check-Out Staff"),
    )

    # Supervised check-in field
    supervised = models.BooleanField(
        default=False,
        help_text="Child is supervised by guardian, no explicit checkout required",
        verbose_name=_("Supervised")
    )

    # Print tracking fields
    label_printed = models.BooleanField(
        default=False,
        verbose_name=_("Label Printed")
    )
    label_printed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Label Printed At")
    )
    label_printed_by = models.ForeignKey(
        "accounts.AdminUser",
        related_name="labels_printed",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("Label Printed By"),
    )

    class Meta:
        db_table = "check_in_records"
        verbose_name = _("Check-In Record")
        verbose_name_plural = _("Check-In Records")
        constraints = [
            models.UniqueConstraint(fields=["child", "session", "check_in_time"], name="unique_check_in_per_session"),
        ]
        indexes = [
            models.Index(fields=["child"]),
            models.Index(fields=["session"]),
            models.Index(fields=["check_in_staff"]),
            models.Index(fields=["check_out_staff"]),
            models.Index(fields=["label_printed"]),
            models.Index(fields=["supervised"]),
        ]

    def __str__(self) -> str:
        return f"{self.child} @ {self.session}"


class QRCode(models.Model):
    """
    Short alphanumeric codes for active check-ins.
    Codes are allocated on check-in and returned to pool after checkout + 24h grace period.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(
        max_length=6,
        unique=True,
        db_index=True,
        verbose_name=_("QR Code")
    )

    # Current assignment (null = available in pool)
    checkin_record = models.OneToOneField(
        "CheckInRecord",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="qr_code",
        verbose_name=_("Check-In Record")
    )

    # Timestamps for pool management
    allocated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Allocated At")
    )
    released_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Released At"),
        help_text="When checkout occurred. Code returns to pool 24h after this."
    )

    class Meta:
        db_table = "qr_codes"
        verbose_name = _("QR Code")
        verbose_name_plural = _("QR Codes")
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["released_at"]),
        ]

    def __str__(self) -> str:
        status = "allocated" if self.checkin_record else "available"
        return f"{self.code} ({status})"

    @property
    def is_available(self) -> bool:
        """Check if code is available for allocation."""
        from datetime import timedelta
        from django.utils import timezone

        if self.checkin_record is not None:
            return False
        if self.released_at is None:
            return True  # Never used or pre-generated
        # Available if released > 24 hours ago
        return timezone.now() - self.released_at > timedelta(hours=24)


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey("accounts.AdminUser", on_delete=models.PROTECT)
    action = models.CharField(max_length=64)
    entity_type = models.CharField(max_length=64)
    entity_id = models.CharField(max_length=255)
    details = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "audit_logs"
        indexes = [
            models.Index(fields=["timestamp"]),
            models.Index(fields=["user"]),
            models.Index(fields=["entity_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} on {self.entity_type}:{self.entity_id}"
