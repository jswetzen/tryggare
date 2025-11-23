import uuid

from django.db import models


class CheckInRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    check_in_time = models.DateTimeField(auto_now_add=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    picked_up_by = models.CharField(max_length=255, null=True, blank=True)
    child = models.ForeignKey("families.Child", related_name="checkin_records", on_delete=models.CASCADE)
    session = models.ForeignKey("events.Session", related_name="checkin_records", on_delete=models.CASCADE)
    check_in_staff = models.ForeignKey(
        "accounts.AdminUser",
        related_name="checkins_performed",
        on_delete=models.PROTECT,
    )
    check_out_staff = models.ForeignKey(
        "accounts.AdminUser",
        related_name="checkouts_performed",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "check_in_records"
        constraints = [
            models.UniqueConstraint(fields=["child", "session", "check_in_time"], name="unique_check_in_per_session"),
        ]
        indexes = [
            models.Index(fields=["child"]),
            models.Index(fields=["session"]),
            models.Index(fields=["check_in_staff"]),
            models.Index(fields=["check_out_staff"]),
        ]

    def __str__(self) -> str:
        return f"{self.child} @ {self.session}"


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
