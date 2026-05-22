import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class ImportSource(models.Model):
    """
    Unified import source that replaces ImportProvider + EventImportConfig.
    Represents one configured connection to an external booking system.
    """

    PROVIDER_FESTIVALPRO = "festivalpro"
    PROVIDER_PLANNINGCENTER = "planningcenter"

    PROVIDER_CHOICES = [
        (PROVIDER_FESTIVALPRO, "FestivalPro"),
        (PROVIDER_PLANNINGCENTER, "Planning Center"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name=_("Name"))
    provider_type = models.CharField(
        max_length=50,
        choices=PROVIDER_CHOICES,
        default=PROVIDER_FESTIVALPRO,
        verbose_name=_("Provider Type"),
    )
    event = models.ForeignKey(
        "events.Event",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="import_sources",
        verbose_name=_("Event"),
    )
    credentials = models.BinaryField(
        null=True, blank=True, verbose_name=_("Credentials")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "import_sources"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    @property
    def has_credentials(self) -> bool:
        return bool(self.credentials)


class FestivalProImportSource(models.Model):
    """
    FestivalPro-specific configuration for an ImportSource.
    One-to-one extension: only exists when source.provider_type == 'festivalpro'.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.OneToOneField(
        ImportSource,
        on_delete=models.CASCADE,
        related_name="festivalpro_config",
        verbose_name=_("Import Source"),
    )
    login_url = models.URLField(max_length=2048, verbose_name=_("Login URL"))
    export_url = models.URLField(max_length=2048, verbose_name=_("Export URL"))
    # Full form-encoded body for the export POST request (event-specific params, no credentials)
    export_body = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Export POST Body"),
        help_text=_(
            "Raw form-encoded body to POST to export_url. Paste from browser network capture."
        ),
    )
    field_mappings = models.JSONField(
        default=dict,
        verbose_name=_("Field Mappings"),
        help_text=_(
            "Maps booking prefix keys to 'full_event', a session UUID, or 'ignore'."
        ),
    )

    class Meta:
        db_table = "festivalpro_import_sources"
        verbose_name = _("FestivalPro Import Source")
        verbose_name_plural = _("FestivalPro Import Sources")

    def __str__(self) -> str:
        return f"FestivalPro config for {self.source.name}"


class ImportRun(models.Model):
    """
    Records a single execution of the import process for an import source.

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
    source = models.ForeignKey(
        ImportSource,
        on_delete=models.CASCADE,
        related_name="runs",
        verbose_name=_("Import Source"),
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
    started_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Started At")
    )
    finished_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Finished At")
    )
    source_file_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name=_("Source File Name"),
    )
    raw_data = models.JSONField(
        default=None,
        null=True,
        blank=True,
        verbose_name=_("Raw Data"),
        help_text=_("Raw parsed JSON from the import source, for debugging."),
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
        event_str = self.source.event.name if self.source.event else "no event"
        return f"ImportRun [{self.status}] for {event_str} at {self.started_at}"
