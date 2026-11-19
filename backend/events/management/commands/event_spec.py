"""``manage.py event_spec export|validate|diff|apply``: JSON in, JSON on stdout.

Issues print as ``path: [code] message`` on stderr and the exit code is non-zero
on errors. There is deliberately no confirmation prompt (see docs/event-spec-plan.md).
"""

import json
import sys

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext as _
from pydantic import ValidationError as PydanticValidationError

from events import event_spec
from events.models import Event


class Command(BaseCommand):
    help = "Export, validate, diff and apply event specs (JSON)."

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest="action", required=True)

        p = sub.add_parser("export", help="Print an event's spec.")
        p.add_argument("--event", required=True, help="Event id.")
        p.add_argument("-o", "--output", help="Write to this file instead of stdout.")

        p = sub.add_parser("validate", help="Validate a spec file.")
        p.add_argument("file", help="Spec JSON file, or - for stdin.")
        p.add_argument("--event", help="Validate against this target event id.")

        p = sub.add_parser("diff", help="Show what applying a spec would change.")
        p.add_argument("file", help="Spec JSON file, or - for stdin.")
        p.add_argument("--event", required=True, help="Event id.")

        p = sub.add_parser("apply", help="Apply a spec as a new or an empty event.")
        p.add_argument("file", help="Spec JSON file, or - for stdin.")
        p.add_argument("--event", help="Apply onto this empty event instead.")
        p.add_argument("--dry-run", action="store_true", help="Validate and diff only.")

    def handle(self, *args, **options):
        getattr(self, f"_{options['action']}")(options)

    def _event(self, event_id):
        try:
            return Event.objects.get(pk=event_id)
        except (Event.DoesNotExist, ValidationError):
            raise CommandError(
                _("Event %(id)s does not exist.") % {"id": event_id}
            ) from None

    def _spec(self, path):
        try:
            if path == "-":
                return json.load(sys.stdin)
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except OSError as exc:
            raise CommandError(
                _("Cannot read %(path)s: %(error)s") % {"path": path, "error": exc}
            ) from exc
        except ValueError as exc:
            raise CommandError(
                _("%(path)s is not valid JSON: %(error)s")
                % {"path": path, "error": exc}
            ) from exc

    def _json(self, data):
        self.stdout.write(json.dumps(data, indent=2, ensure_ascii=False))

    def _report(self, errors, warnings):
        for label, issues, style in (
            (_("error"), errors, self.style.ERROR),
            (_("warning"), warnings, self.style.WARNING),
        ):
            for i in issues:
                where = i["path"] or "-"
                self.stderr.write(
                    style(f"{label}: {where}: [{i['code']}] {i['message']}")
                )

    def _fail(self, errors):
        raise CommandError(
            _("The spec was refused: %(count)d error(s); nothing was written.")
            % {"count": len(errors)}
        )

    def _export(self, options):
        event = self._event(options["event"])
        try:
            spec = event_spec.export(event)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        if options["output"]:
            with open(options["output"], "w", encoding="utf-8") as f:
                json.dump(spec, f, indent=2, ensure_ascii=False)
                f.write("\n")
        else:
            self._json(spec)

    def _validate(self, options):
        spec = self._spec(options["file"])
        event = self._event(options["event"]) if options["event"] else None
        errors, warnings = event_spec.validate(spec, event)
        self._report(errors, warnings)
        self._json({"valid": not errors, "errors": errors, "warnings": warnings})
        if errors:
            self._fail(errors)

    def _diff(self, options):
        spec = self._spec(options["file"])
        event = self._event(options["event"])
        errors, warnings = event_spec.validate(spec, event)
        self._report(errors, warnings)
        try:
            changes = event_spec.diff(event, spec)
        except (PydanticValidationError, ValueError, TypeError):
            changes = []  # a shape error; the issues above say where
        self._json({"diff": changes, "errors": errors, "warnings": warnings})
        if errors:
            self._fail(errors)

    def _apply(self, options):
        spec = self._spec(options["file"])
        event = self._event(options["event"]) if options["event"] else None
        if options["dry_run"]:
            errors, warnings = event_spec.validate(spec, event)
            self._report(errors, warnings)
            if errors:
                self._json({"errors": errors, "warnings": warnings})
                self._fail(errors)
            self._json(
                {
                    "dry_run": True,
                    "event_id": str(event.pk) if event else None,
                    "diff": event_spec.diff(event, spec),
                    "warnings": warnings,
                }
            )
            return
        try:
            event, changes, warnings = event_spec.apply(spec, event)
        except event_spec.SpecError as exc:
            self._report(exc.errors, exc.warnings)
            self._json({"errors": exc.errors, "warnings": exc.warnings})
            self._fail(exc.errors)
        self._report([], warnings)
        self._json({"event_id": str(event.pk), "diff": changes, "warnings": warnings})
