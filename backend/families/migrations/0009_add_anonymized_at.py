from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("families", "0008_add_parent_lock_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="family",
            name="anonymized_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Set when GDPR retention anonymization scrubbed this family's PII.",
                null=True,
                verbose_name="Anonymized At",
            ),
        ),
        migrations.AddField(
            model_name="child",
            name="anonymized_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Set when GDPR retention anonymization scrubbed this child's PII.",
                null=True,
                verbose_name="Anonymized At",
            ),
        ),
    ]
