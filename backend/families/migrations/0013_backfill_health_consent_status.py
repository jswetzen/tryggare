from django.db import migrations


def flag_existing_health_data_for_reconfirmation(apps, schema_editor):
    """
    Pre-existing allergy/notes text was captured before consent-capture
    existed (paper/verbal process during pilots). Treat it as unconfirmed
    rather than assuming the past process satisfied Art. 9(2)(a) — same
    handling as an actual withdrawal, so staff get a reconfirmation prompt
    instead of the data silently looking pre-approved. Covers any status
    that shouldn't carry text (not just the default), matching the
    invariant enforced going forward by Child.save().
    """
    Child = apps.get_model("families", "Child")
    live_statuses = ("granted", "needs_reconfirmation")
    for child in Child.objects.exclude(health_consent_status__in=live_statuses):
        if child.allergies or child.notes:
            child.health_consent_status = "needs_reconfirmation"
            child.save(update_fields=["health_consent_status"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("families", "0012_add_anonymized_at_and_health_consent_fields"),
    ]

    operations = [
        migrations.RunPython(
            flag_existing_health_data_for_reconfirmation, noop_reverse
        ),
    ]
