"""Delete assistant conversations idle past ASSISTANT_RETENTION_DAYS."""

from django.core.management.base import BaseCommand

from assistant.runner import purge_idle


class Command(BaseCommand):
    def handle(self, *args, **opts):
        self.stdout.write(f"Deleted {purge_idle()} idle assistant conversation(s).")
