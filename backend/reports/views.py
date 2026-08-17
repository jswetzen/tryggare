import csv
import json

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from config.permissions import DjangoModelPermissionsWithView
from events.models import Event

from .models import EventReport
from .serializers import EventReportDetailSerializer, EventReportListSerializer
from .services import generate_event_report


def _slugify_filename(name: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in name).strip("-")
    return safe or "event-report"


class EventReportViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only access to generated report snapshots.

    Reading is gated on ``reports.view_eventreport``. This is the endpoint that
    most justifies the whole increment: a report snapshot is the event's
    aggregate financial and attendance picture, and under a flat
    ``IsAuthenticated`` any volunteer could read it.

    ``generate`` (below) is the one write. Snapshots were previously producible
    only from Django admin or the ``generate_event_report`` management command,
    so a coordinator with no admin access had to leave the app — or ask someone
    who could — to refresh the numbers (roadmap J6).
    """

    queryset = EventReport.objects.select_related("event", "generated_by").all()
    permission_classes = [DjangoModelPermissionsWithView]
    filterset_fields = ["event"]
    ordering = ["-generated_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return EventReportListSerializer
        return EventReportDetailSerializer

    @action(detail=False, methods=["post"])
    def generate(self, request):
        """Build a fresh snapshot for ``{"event": <uuid>}`` and return it.

        Thin wrapper over :func:`reports.services.generate_event_report` — the
        same function the admin action and the management command call. It is
        deliberately not a reimplementation: the snapshot's contents are one of
        the few things in this system that cannot be recomputed after the fact
        (see :class:`~reports.models.EventReport`), so there must be exactly one
        way to build one.

        **Every call appends a new snapshot; nothing is overwritten.** That is
        the model's whole point — a report is a historical record of what the
        numbers were at a moment in time, taken before PII is deleted for
        retention. An ``update_or_create`` here would quietly destroy the
        earlier picture, which is the one thing the snapshot exists to keep.

        ``POST`` maps to ``reports.add_eventreport`` through the standard
        permission map, so this needs no bespoke check: Koordinator and
        Administratör hold it, Volontär does not, and moving it between groups
        in Django admin is all it takes to change that.
        """
        event_id = request.data.get("event")
        if not event_id:
            return Response(
                {"event": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # A malformed UUID reaches the ORM as a ValidationError, which DRF does
        # not translate — it would surface as a 500 on what is plainly bad
        # input. Catch it here so the client gets the 400 it deserves.
        try:
            event = get_object_or_404(Event, pk=event_id)
        except (DjangoValidationError, ValueError, TypeError):
            return Response(
                {"event": ["Not a valid event id."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        report = generate_event_report(event, user=request.user)
        serializer = EventReportDetailSerializer(report, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def export(self, request, pk=None):
        """Download a snapshot as ``?fmt=csv`` (default) or ``?fmt=json``.

        Note: the query param is ``fmt`` rather than ``format`` because DRF
        reserves ``format`` for content negotiation (an unknown value 404s).
        """
        report = self.get_object()
        fmt = request.query_params.get("fmt", "csv").lower()
        base = _slugify_filename(report.event_name)
        stamp = report.generated_at.strftime("%Y%m%d-%H%M")

        if fmt == "json":
            response = HttpResponse(
                json.dumps(report.data, indent=2, ensure_ascii=False),
                content_type="application/json",
            )
            response["Content-Disposition"] = (
                f'attachment; filename="{base}-{stamp}.json"'
            )
            return response

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{base}-{stamp}.csv"'
        self._write_csv(response, report)
        return response

    @staticmethod
    def _write_csv(response, report):
        data = report.data
        event = data.get("event", {})
        tickets = event.get("tickets", {})
        demo = event.get("demographics", {})
        ops = event.get("operations", {})
        age = demo.get("age_buckets", {})

        writer = csv.writer(response)
        writer.writerow(["Event report", report.event_name])
        writer.writerow(["Generated at", report.generated_at.isoformat()])
        writer.writerow(["Start date", event.get("start_date", "")])
        writer.writerow(["End date", event.get("end_date", "")])
        writer.writerow(["Sessions", event.get("session_count", "")])
        writer.writerow(["Unique children", event.get("unique_children", "")])
        writer.writerow(["Total check-ins", event.get("total_checkins", "")])
        writer.writerow(["Event passes issued", tickets.get("event_passes_issued", "")])
        writer.writerow(
            ["Session tickets issued", tickets.get("session_tickets_issued", "")]
        )
        writer.writerow(["Event pass no-shows", tickets.get("event_pass_no_shows", "")])
        writer.writerow(["With allergies", demo.get("with_allergies", "")])
        writer.writerow(["Returning families", demo.get("returning_families", "")])
        writer.writerow(["New families", demo.get("new_families", "")])
        writer.writerow(["Labels printed", ops.get("labels_printed", "")])
        writer.writerow(["Avg stay (min)", ops.get("avg_stay_minutes", "")])
        for bucket, count in age.items():
            writer.writerow([f"Age {bucket}", count])

        writer.writerow([])
        writer.writerow(["Check-ins per staff", "Count"])
        for row in ops.get("checkins_per_staff", []):
            writer.writerow([row.get("staff", ""), row.get("count", "")])

        writer.writerow([])
        writer.writerow(
            [
                "Session",
                "Start",
                "End",
                "Unique children",
                "Total check-ins",
                "Peak concurrent",
                "Supervised",
                "Staffed checkouts",
                "Session tickets",
                "Session no-shows",
                "Labels printed",
                "Avg stay (min)",
            ]
        )
        for s in data.get("sessions", []):
            writer.writerow(
                [
                    s.get("name", ""),
                    s.get("start_time", ""),
                    s.get("end_time", ""),
                    s.get("unique_children", ""),
                    s.get("total_checkins", ""),
                    s.get("peak_concurrent", ""),
                    s.get("supervised", ""),
                    s.get("staffed_checkouts", ""),
                    s.get("session_tickets_issued", ""),
                    s.get("session_ticket_no_shows", ""),
                    s.get("labels_printed", ""),
                    s.get("avg_stay_minutes", ""),
                ]
            )
