import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class EventImportConfig(models.Model):
    """
    Stores the field/prefix mapping configuration for importing bookings
    into a specific event. One config per event.

    field_mappings stores a dict like:
    {
        "SK26 Barnkonferens ": "full_event",
        "Dagsbiljett barn fredag ": "<session_uuid>",
        "SK26 Helkonferens ": "ignore"
    }
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.OneToOneField(
        "events.Event",
        on_delete=models.CASCADE,
        related_name="import_config",
        verbose_name=_("Event"),
    )
    field_mappings = models.JSONField(
        default=dict,
        verbose_name=_("Field Mappings"),
        help_text=_(
            "Maps booking prefix keys to 'full_event', a session UUID, or 'ignore'."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        db_table = "import_configs"
        verbose_name = _("Event Import Config")
        verbose_name_plural = _("Event Import Configs")

    def __str__(self) -> str:
        return f"Import config for {self.event}"


class ImportRun(models.Model):
    """
    Records a single execution of the import process for an event config.

    log is an array of dicts: [{"booking_id": str, "action": str, "details": str}]

    summary is a dict:
    {
        "total_bookings": int,
        "families_created": int,
        "families_skipped": int,
        "children_created": int,
        "children_skipped": int,
        "tickets_created": int,
        "errors": [str],
        "warnings": [str]
    }
    """

    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, _("Pending")),
        (STATUS_RUNNING, _("Running")),
        (STATUS_COMPLETED, _("Completed")),
        (STATUS_FAILED, _("Failed")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    config = models.ForeignKey(
        EventImportConfig,
        on_delete=models.CASCADE,
        related_name="runs",
        verbose_name=_("Import Config"),
    )
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="import_runs",
        verbose_name=_("Triggered By"),
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name=_("Status"),
    )
    started_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Started At"))
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Finished At"))
    source_file_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name=_("Source File Name"),
    )
    log = models.JSONField(
        default=list,
        verbose_name=_("Log"),
        help_text=_("Array of per-booking log entries."),
    )
    summary = models.JSONField(
        default=dict,
        verbose_name=_("Summary"),
        help_text=_("Aggregated import statistics."),
    )

    class Meta:
        db_table = "import_runs"
        verbose_name = _("Import Run")
        verbose_name_plural = _("Import Runs")
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"ImportRun [{self.status}] for {self.config.event} at {self.started_at}"
