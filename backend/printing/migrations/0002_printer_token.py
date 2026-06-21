import django.utils.timezone
from django.db import migrations, models

import printing.models


class Migration(migrations.Migration):
    dependencies = [
        ("printing", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="printer",
            name="token",
            field=models.CharField(
                default=printing.models.generate_printer_token,
                max_length=64,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name="printer",
            name="token_created_at",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name="printer",
            name="token_revoked_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
