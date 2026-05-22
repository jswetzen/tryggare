import io
import base64
import qrcode
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from checkins.models import CheckInRecord
from .models import Printer, PrintJob
from .serializers import PrinterSerializer, PrintJobSerializer

# Label dimensions mapping: brother_ql dots_printable → mm at 300 DPI.
# Displayed landscape: width = label length, height = label width.
LABEL_DIMENSIONS = {
    "29x90": {"w_mm": 83.8, "h_mm": 25.9},
    "62": {"w_mm": 54.3, "h_mm": 52.5},
    "62x100": {"w_mm": 93.0, "h_mm": 52.5},
    "29x42": {"w_mm": 36.0, "h_mm": 25.9},
    "29": {"w_mm": 54.3, "h_mm": 25.9},
    "17x54": {"w_mm": 51.0, "h_mm": 12.7},
}
DEFAULT_LABEL_DIMENSIONS = {"w_mm": 54.3, "h_mm": 17.0}


class PrinterViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for listing printers.
    """

    queryset = Printer.objects.all()
    serializer_class = PrinterSerializer
    permission_classes = [IsAuthenticated]


class PrintJobViewSet(viewsets.GenericViewSet):
    """
    ViewSet for creating and managing print jobs.
    """

    serializer_class = PrintJobSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request):
        """
        Create a new print job.
        Accepts: {checkin_id, printer_id?}
        If printer is online, pushes WS job immediately.
        """
        checkin_id = request.data.get("checkin_id")
        printer_id = request.data.get("printer_id")

        if not checkin_id:
            return Response(
                {"error": "checkin_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        checkin = get_object_or_404(CheckInRecord, pk=checkin_id)

        printer = None
        if printer_id:
            printer = get_object_or_404(Printer, pk=printer_id)

        job = PrintJob.objects.create(
            checkin=checkin,
            printer=printer,
            status=PrintJob.STATUS_PENDING,
        )

        if printer and printer.is_online:
            self._push_job_to_printer(request, job)

        serializer = self.get_serializer(job)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        """
        Assign or reassign a printer to a job.
        Accepts: {printer_id}
        """
        job = get_object_or_404(PrintJob, pk=pk)
        printer_id = request.data.get("printer_id")

        if not printer_id:
            return Response(
                {"error": "printer_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        printer = get_object_or_404(Printer, pk=printer_id)
        job.printer = printer
        job.status = PrintJob.STATUS_PENDING
        job.sent_at = None
        job.save()

        if printer.is_online:
            self._push_job_to_printer(request, job)

        serializer = self.get_serializer(job)
        return Response(serializer.data)

    def _push_job_to_printer(self, request, job):
        """Push a print job via WebSocket and update status."""
        host = request.get_host()
        scheme = "https" if request.is_secure() else "http"
        label_url = f"{scheme}://{host}/print-job/{job.id}/label/"

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "checkins_broadcast",
            {
                "type": "print_job",
                "data": {
                    "job_id": str(job.id),
                    "printer_id": str(job.printer.id),
                    "label_url": label_url,
                },
            },
        )

        job.status = PrintJob.STATUS_SENT
        job.sent_at = timezone.now()
        job.save()


def label_page_view(request, job_uuid):
    """
    Unauthenticated endpoint that renders a label page for a print job.
    Used by the printer client to fetch and render the label.
    """
    job = get_object_or_404(
        PrintJob.objects.select_related(
            "checkin__child", "checkin__session", "checkin__qr_code"
        ),
        pk=job_uuid,
        status__in=[PrintJob.STATUS_PENDING, PrintJob.STATUS_SENT],
    )

    checkin = job.checkin
    qr_code_str = (
        checkin.qr_code.code
        if hasattr(checkin, "qr_code") and checkin.qr_code
        else "INVALID"
    )

    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=1,
    )
    qr.add_data(f"http://{request.get_host()}/qr/{qr_code_str}")
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_data_url = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"

    label = request.GET.get("label", "")
    dims = LABEL_DIMENSIONS.get(label, DEFAULT_LABEL_DIMENSIONS)

    return render(
        request,
        "print_label.html",
        {
            "checkin": checkin,
            "qr_url": qr_data_url,
            "no_autoprint": True,
            "w_mm": dims["w_mm"],
            "h_mm": dims["h_mm"],
        },
    )
