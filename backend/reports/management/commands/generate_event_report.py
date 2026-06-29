"""
Generate report snapshots for one or all events.

Snapshots capture aggregate, non-PII statistics so the figures survive deletion
of the underlying PII. Run this before purging an event's data.

Examples:
    uv run python manage.py generate_event_report <event_id>
    uv run python manage.py generate_event_report --all
"""

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from events.models import Event
from reports.services import generate_event_report


class Command(BaseCommand):
    help = "Generate an EventReport snapshot for one event or all events."

    def add_arguments(self, parser):
        parser.add_argument(
            "event_id",
            nargs="?",
            default=None,
            help="UUID of the event to report on. Omit and pass --all for every event.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Generate a report for every event.",
        )

    def handle(self, *args, **options):
        if options["all"]:
            events = list(Event.objects.all())
            if not events:
                self.stdout.write(self.style.WARNING("No events found."))
                return
        elif options["event_id"]:
            try:
                events = [Event.objects.get(id=options["event_id"])]
            except Event.DoesNotExist:
                raise CommandError(f"No event with id {options['event_id']}")
            except (ValueError, ValidationError):  # malformed UUID
                raise CommandError(f"Invalid event id: {options['event_id']}")
        else:
            raise CommandError("Provide an event_id or --all.")

        for event in events:
            report = generate_event_report(event)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Generated report for '{event.name}': "
                    f"{report.unique_children} children, "
                    f"{report.total_checkins} check-ins."
                )
            )
