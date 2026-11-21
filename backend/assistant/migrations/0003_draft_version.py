from django.db import migrations, models


def backfill(apps, schema_editor):
    Conversation = apps.get_model("assistant", "AssistantConversation")
    for conv in Conversation.objects.exclude(draft=None):
        conv.draft_version = (conv.draft or {}).get("version", 0)
        conv.save(update_fields=["draft_version"])


class Migration(migrations.Migration):

    dependencies = [
        ("assistant", "0002_assistant_conversation"),
    ]

    operations = [
        migrations.AddField(
            model_name="assistantconversation",
            name="draft_version",
            field=models.PositiveIntegerField(default=0, editable=False),
        ),
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
