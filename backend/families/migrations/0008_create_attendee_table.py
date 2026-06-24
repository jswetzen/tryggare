import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("families", "0007_allow_null_birthdate"),
    ]

    operations = [
        migrations.CreateModel(
            name="Attendee",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "first_name",
                    models.CharField(max_length=255, verbose_name="First Name"),
                ),
                (
                    "last_name",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=255,
                        verbose_name="Last Name",
                    ),
                ),
                (
                    "last_participation_date",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Last Participation Date"
                    ),
                ),
                (
                    "family",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attendees",
                        to="families.family",
                        verbose_name="Family",
                    ),
                ),
            ],
            options={
                "verbose_name": "Attendee",
                "verbose_name_plural": "Attendees",
                "db_table": "attendees",
            },
        ),
    ]
