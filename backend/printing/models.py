import uuid
from django.db import models


class Printer(models.Model):
    id = models.UUIDField(primary_key=True)  # set by client
    name = models.CharField(max_length=100)
    is_online = models.BooleanField(default=False)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status = "online" if self.is_online else "offline"
        return f"{self.name} ({status})"

    class Meta:
        ordering = ["name"]


class PrintJob(models.Model):
    STATUS_PENDING = "pending"
    STATUS_SENT = "sent"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"

    STATUS = [
        (STATUS_PENDING, "pending"),
        (STATUS_SENT, "sent"),
        (STATUS_COMPLETED, "completed"),
        (STATUS_FAILED, "failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    checkin = models.ForeignKey(
        "checkins.CheckInRecord", on_delete=models.CASCADE, related_name="print_jobs"
    )
    printer = models.ForeignKey(
        Printer, null=True, blank=True, on_delete=models.SET_NULL, related_name="print_jobs"
    )
    status = models.CharField(max_length=20, choices=STATUS, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"PrintJob {self.id} [{self.status}]"

    class Meta:
        ordering = ["-created_at"]
