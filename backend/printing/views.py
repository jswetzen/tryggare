import io
import base64
import qrcode
from asgiref.sync import async_to_sync
from reportlab.pdfbase.pdfmetrics import stringWidth
from channels.layers import get_channel_layer
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from checkins.models import CheckInRecord
from .models import Printer, PrintJob
from .serializers import (
    PrinterSerializer,
    PrinterWithTokenSerializer,
    PrintJobSerializer,
)

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

# Label geometry, kept in sync with print_label.html. The name shares the label
# with a square QR code; whatever horizontal space is left is the name box.
#   .label   padding: PAD_V mm (top/bottom)  PAD_H mm (left/right); gap: GAP mm
#   .qr-code side = (label height - QR_INSET mm)
_PAD_H_MM = 2.5
_PAD_V_MM = 1.5
_GAP_MM = 2.0
_QR_INSET_MM = 3.0

# Bounds for the auto-fitted name. MAX is what a short name expands to; MIN keeps
# a very long name legible (it will wrap/hyphenate rather than shrink past this).
_NAME_MIN_PT = 10.0
_NAME_MAX_PT = 28.0

_PT_PER_MM = 72.0 / 25.4
# Helvetica-Bold cap height as a fraction of em (AFM CapHeight 718/1000). Used to
# size the name to the available height, since font-size > glyph height.
_CAP_HEIGHT_FRAC = 0.718
# Metric font that approximates the template's heavy Helvetica-Neue face.
_METRIC_FONT = "Helvetica-Bold"


def fit_child_name_pt(name, w_mm, h_mm):
    """Largest font size (pt) at which ``name`` fits the label's name box.

    WeasyPrint runs no JavaScript and renders @media print, so the font size has
    to be decided here rather than by CSS in the browser. We measure the name
    with reportlab's font metrics and pick the largest size that fits both the
    width left over after the QR code and the label height, clamped to
    [_NAME_MIN_PT, _NAME_MAX_PT]. Short names hit the max (filling the label);
    long names shrink to fit instead of overflowing.
    """
    name = (name or "").strip().upper()
    if not name:
        return _NAME_MIN_PT

    qr_side_mm = h_mm - _QR_INSET_MM
    avail_w_pt = (w_mm - 2 * _PAD_H_MM - _GAP_MM - qr_side_mm) * _PT_PER_MM
    avail_h_pt = (h_mm - 2 * _PAD_V_MM) * _PT_PER_MM

    # stringWidth scales linearly with font size, so width at 1pt gives the ratio.
    width_at_1pt = stringWidth(name, _METRIC_FONT, 1.0) or 0.001
    by_width = avail_w_pt / width_at_1pt
    by_height = avail_h_pt / _CAP_HEIGHT_FRAC

    size = min(by_width, by_height, _NAME_MAX_PT)
    return round(max(size, _NAME_MIN_PT), 1)


class PrinterViewSet(viewsets.ModelViewSet):
    """
    Manage printers and their auth tokens.

    Printers are provisioned server-side: ``POST`` (or ``provision``) creates a
    printer and returns its token *once* — the operator copies that token into
    the printer-client config. ``rotate_token`` / ``revoke_token`` manage the
    credential's lifecycle. The token is never included in list/retrieve.
    """

    queryset = Printer.objects.all()
    serializer_class = PrinterSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def create(self, request, *args, **kwargs):
        """Provision a new printer; the response includes its token once."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        printer = serializer.save()
        out = PrinterWithTokenSerializer(printer)
        return Response(out.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def provision(self, request):
        """Alias for create, for a clearer client-facing verb."""
        return self.create(request)

    @action(detail=True, methods=["post"], url_path="rotate-token")
    def rotate_token(self, request, pk=None):
        """Issue a fresh token (invalidates the old one). Returns it once."""
        printer = self.get_object()
        printer.rotate_token()
        return Response(PrinterWithTokenSerializer(printer).data)

    @action(detail=True, methods=["post"], url_path="revoke-token")
    def revoke_token(self, request, pk=None):
        """Disable the printer's token without issuing a new one."""
        printer = self.get_object()
        printer.revoke_token()
        return Response(PrinterSerializer(printer).data)


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
        """
        Push a print job via WebSocket and update status.

        IMPORTANT: Database write happens BEFORE broadcast to avoid race conditions
        where the printer client receives the job UUID but the database hasn't
        committed the record yet, causing label_page_view() to return 404.
        """
        # Update status and commit to database FIRST
        job.status = PrintJob.STATUS_SENT
        job.sent_at = timezone.now()
        job.save()

        # NOW broadcast with the committed job
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


def label_page_view(request, job_uuid):
    """
    Unauthenticated endpoint that renders a label page for a print job.
    Used by the printer client to fetch and render the label.

    The label is a pure rendering of the check-in (child name + QR), so we do
    NOT gate it on the job's lifecycle status. Doing so caused a real bug: when
    a whole family is checked in, the printer renders labels one at a time, and
    a job could reach a terminal status (e.g. a transient print retry marking it
    FAILED, a stale/duplicate completion, or a reconnect re-delivery) before the
    printer fetched its label — which then 404'd ("uuid that doesn't exist") and
    that child's label never printed. We only require the child to still be
    checked in, which is the privacy-relevant condition for the public QR page.
    """
    job = get_object_or_404(
        PrintJob.objects.select_related(
            "checkin__child", "checkin__session", "checkin__qr_code"
        ),
        pk=job_uuid,
        checkin__check_out_time__isnull=True,
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

    name_pt = fit_child_name_pt(checkin.child.first_name, dims["w_mm"], dims["h_mm"])

    return render(
        request,
        "print_label.html",
        {
            "checkin": checkin,
            "qr_url": qr_data_url,
            "no_autoprint": True,
            "w_mm": dims["w_mm"],
            "h_mm": dims["h_mm"],
            "name_pt": name_pt,
        },
    )
