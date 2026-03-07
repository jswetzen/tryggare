"""
Migration: Replace ImportProvider + EventImportConfig with ImportSource + FestivalProImportSource.

Steps:
1. Create import_sources table (ImportSource)
2. Create festivalpro_import_sources table (FestivalProImportSource)
3. Data migration: convert existing ImportProvider + EventImportConfig → ImportSource + FestivalProImportSource
4. Add source FK to ImportRun (nullable initially)
5. Data migration: point ImportRun.source to new ImportSource rows
6. Make ImportRun.source non-nullable
7. Remove old ImportRun.config FK
8. Drop old tables (import_configs, import_providers)
"""

import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def migrate_to_import_source(apps, schema_editor):
    """
    Convert each EventImportConfig (possibly with a linked ImportProvider)
    into an ImportSource + FestivalProImportSource pair.
    Also points ImportRun records to the new ImportSource.
    """
    EventImportConfig = apps.get_model("imports", "EventImportConfig")
    ImportProvider = apps.get_model("imports", "ImportProvider")
    ImportSource = apps.get_model("imports", "ImportSource")
    FestivalProImportSource = apps.get_model("imports", "FestivalProImportSource")
    ImportRun = apps.get_model("imports", "ImportRun")

    # Map old config.id → new source.id for updating ImportRun rows
    config_to_source = {}

    for config in EventImportConfig.objects.select_related("provider", "event").all():
        provider = config.provider

        if provider is not None:
            name = provider.name
            credentials = provider.credentials
        else:
            # Orphaned config — no provider
            event_name = config.event.name if config.event else "Unknown"
            name = f"{event_name} Import"
            credentials = None

        source = ImportSource.objects.create(
            id=uuid.uuid4(),
            name=name,
            provider_type="festivalpro",
            event=config.event,
            credentials=credentials,
        )

        FestivalProImportSource.objects.create(
            id=uuid.uuid4(),
            source=source,
            login_url=provider.login_url if provider else "",
            export_url=provider.export_url if provider else "",
            export_body=provider.export_body if provider else "",
            field_mappings=config.field_mappings,
        )

        config_to_source[str(config.id)] = source

    # Point ImportRun.source_new to newly created ImportSource
    for run in ImportRun.objects.all():
        config_id = str(run.config_id)
        if config_id in config_to_source:
            run.source_new = config_to_source[config_id]
            run.save(update_fields=["source_new"])


class Migration(migrations.Migration):

    dependencies = [
        ("imports", "0002_importprovider_eventimportconfig_provider"),
        ("events", "0005_add_external_ticket_code"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Create ImportSource
        migrations.CreateModel(
            name="ImportSource",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255, verbose_name="Name")),
                ("provider_type", models.CharField(
                    choices=[("festivalpro", "FestivalPro"), ("planningcenter", "Planning Center")],
                    default="festivalpro",
                    max_length=50,
                    verbose_name="Provider Type",
                )),
                ("credentials", models.BinaryField(blank=True, null=True, verbose_name="Credentials")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("event", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="import_sources",
                    to="events.event",
                    verbose_name="Event",
                )),
            ],
            options={"db_table": "import_sources", "ordering": ["name"]},
        ),

        # 2. Create FestivalProImportSource
        migrations.CreateModel(
            name="FestivalProImportSource",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("login_url", models.URLField(max_length=2048, verbose_name="Login URL")),
                ("export_url", models.URLField(max_length=2048, verbose_name="Export URL")),
                ("export_body", models.TextField(
                    blank=True,
                    default="",
                    help_text="Raw form-encoded body to POST to export_url. Paste from browser network capture.",
                    verbose_name="Export POST Body",
                )),
                ("field_mappings", models.JSONField(
                    default=dict,
                    help_text="Maps booking prefix keys to 'full_event', a session UUID, or 'ignore'.",
                    verbose_name="Field Mappings",
                )),
                ("source", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="festivalpro_config",
                    to="imports.importsource",
                    verbose_name="Import Source",
                )),
            ],
            options={
                "db_table": "festivalpro_import_sources",
                "verbose_name": "FestivalPro Import Source",
                "verbose_name_plural": "FestivalPro Import Sources",
            },
        ),

        # 3. Add source_new (nullable) to ImportRun for data migration
        migrations.AddField(
            model_name="importrun",
            name="source_new",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="runs_new",
                to="imports.importsource",
                verbose_name="Import Source",
            ),
        ),

        # 4. Data migration: build ImportSource rows + point ImportRun.source_new
        migrations.RunPython(migrate_to_import_source, migrations.RunPython.noop),

        # 5. Remove old config FK from ImportRun
        migrations.RemoveField(model_name="importrun", name="config"),

        # 6. Rename source_new → source
        migrations.RenameField(model_name="importrun", old_name="source_new", new_name="source"),

        # 7. Make source non-nullable now that all rows have been populated
        migrations.AlterField(
            model_name="importrun",
            name="source",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="runs",
                to="imports.importsource",
                verbose_name="Import Source",
            ),
        ),

        # 8. Drop old tables
        migrations.DeleteModel(name="EventImportConfig"),
        migrations.DeleteModel(name="ImportProvider"),
    ]
