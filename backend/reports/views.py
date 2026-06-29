import csv
import json

from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from .models import EventReport
from .serializers import EventReportDetailSerializer, EventReportListSerializer


def _slugify_filename(name: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in name).strip("-")
    return safe or "event-report"


class EventReportViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only access to generated report snapshots.

    Snapshots are produced in the Django backend (admin action or the
    ``generate_event_report`` management command); this API only exposes them
    for viewing and export from the frontend.
    """

    queryset = EventReport.objects.select_related("event", "generated_by").all()
    permission_classes = [IsAuthenticated]
    filterset_fields = ["event"]
    ordering = ["-generated_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return EventReportListSerializer
        return EventReportDetailSerializer

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
