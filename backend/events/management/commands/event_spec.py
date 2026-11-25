"""``manage.py event_spec export|check|validate|diff|apply``: JSON in, JSON on stdout.

Issues print as ``path: [code] message`` on stderr and the exit code is non-zero
on errors. There is deliberately no confirmation prompt (see docs/event-spec-plan.md).
"""

import json
import sys

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext as _

from events import event_spec
from events.models import Event


class Command(BaseCommand):
    help = "Export, validate, diff and apply event specs (JSON)."

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest="action", required=True)

        p = sub.add_parser("export", help="Print an event's spec.")
        p.add_argument("--event", required=True, help="Event id.")
        p.add_argument("-o", "--output", help="Write to this file instead of stdout.")

        p = sub.add_parser("check", help="Check a live event's setup for problems.")
        p.add_argument("--event", required=True, help="Event id.")

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

    stdin = None  # injectable for tests; defaults to sys.stdin

    def handle(self, *args, **options):
        getattr(self, f"_{options['action']}")(options)

    def _event(self, event_id):
        try:
            return Event.objects.get(pk=event_id)
        except (Event.DoesNotExist, ValidationError):
            raise CommandError(
                _("Event %(id)s does not exist.") % {"id": event_id}, returncode=2
            ) from None

    def _spec(self, path):
        try:
            if path == "-":
                return json.load(self.stdin or sys.stdin)
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except OSError as exc:
            raise CommandError(
                _("Cannot read %(path)s: %(error)s") % {"path": path, "error": exc},
                returncode=2,
            ) from exc
        except ValueError as exc:
            raise CommandError(
                _("%(path)s is not valid JSON: %(error)s")
                % {"path": path, "error": exc},
                returncode=2,
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
        except event_spec.SpecError as exc:
            self._report(exc.errors, [])
            raise CommandError(
                _("The event cannot be exported: %(count)d error(s).")
                % {"count": len(exc.errors)}
            ) from exc
        if options["output"]:
            try:
                with open(options["output"], "w", encoding="utf-8") as f:
                    json.dump(spec, f, indent=2, ensure_ascii=False)
                    f.write("\n")
            except OSError as exc:
                raise CommandError(
                    _("Cannot write %(path)s: %(error)s")
                    % {"path": options["output"], "error": exc},
                    returncode=2,
                ) from exc
        else:
            self._json(spec)

    def _check(self, options):
        try:
            result = event_spec.check_setup(self._event(options["event"]))
        except event_spec.SpecError as exc:
            self._report(exc.errors, [])
            raise CommandError(
                _("The event cannot be checked: %(count)d error(s).")
                % {"count": len(exc.errors)}
            ) from exc
        self._report(result["errors"], result["warnings"])
        self._json(result)
        if result["errors"]:
            raise CommandError(
                _("The setup has %(count)d error(s).")
                % {"count": len(result["errors"])}
            )

    def _validate(self, options):
        spec = self._spec(options["file"])
        event = self._event(options["event"]) if options["event"] else None
        errors, warnings = event_spec.validate(spec, event)
        self._report(errors, warnings)
        self._json({"valid": not errors, "errors": errors, "warnings": warnings})
        if errors:
            self._fail(errors)

    def _diff(self, options):
        result = event_spec.check(
            self._spec(options["file"]), self._event(options["event"])
        )
        self._report(result["errors"], result["warnings"])
        self._json({k: result[k] for k in ("diff", "errors", "warnings")})
        if result["errors"]:
            self._fail(result["errors"])

    def _apply(self, options):
        spec = self._spec(options["file"])
        event = self._event(options["event"]) if options["event"] else None
        if options["dry_run"]:
            result = event_spec.check(spec, event)
            errors, warnings = result["errors"], result["warnings"]
            self._report(errors, warnings)
            if errors:
                self._json({"errors": errors, "warnings": warnings})
                self._fail(errors)
            self._json(
                {
                    "dry_run": True,
                    "event_id": str(event.pk) if event else None,
                    "diff": result["diff"],
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
