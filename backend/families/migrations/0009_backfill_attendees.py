from django.db import migrations


def backfill_attendees(apps, schema_editor):
    """
    For every existing Child, insert one Attendee row reusing id=child.id.
    For every existing Parent, insert one Attendee row reusing id=parent.id,
    splitting parent.name on the first space into first_name/last_name.
    """
    Attendee = apps.get_model("families", "Attendee")
    Child = apps.get_model("families", "Child")
    Parent = apps.get_model("families", "Parent")

    # Backfill Children -> Attendees
    for child in Child.objects.all():
        Attendee.objects.create(
            id=child.id,
            first_name=child.first_name,
            last_name=child.last_name,
            last_participation_date=child.last_participation_date,
            family_id=child.family_id,
        )

    # Backfill Parents -> Attendees
    for parent in Parent.objects.all():
        # Split parent.name on the first space
        parts = parent.name.split(" ", 1) if parent.name else ["", ""]
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""
        Attendee.objects.create(
            id=parent.id,
            first_name=first_name,
            last_name=last_name,
            last_participation_date=parent.last_participation_date,
            family_id=parent.family_id,
        )


def reverse_backfill_attendees(apps, schema_editor):
    """
    Remove all Attendee rows that were created during the forward migration.
    (Child and Parent rows are still intact, so this is safe.)
    """
    Attendee = apps.get_model("families", "Attendee")
    Attendee.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("families", "0008_create_attendee_table"),
    ]

    operations = [
        migrations.RunPython(backfill_attendees, reverse_backfill_attendees),
    ]
