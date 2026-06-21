from rest_framework import serializers
from .models import Printer, PrintJob


class PrinterSerializer(serializers.ModelSerializer):
    """Printer listing — deliberately omits the token (a bearer secret)."""

    token_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Printer
        fields = [
            "id",
            "name",
            "is_online",
            "last_seen_at",
            "created_at",
            "token_active",
        ]
        read_only_fields = ["id", "is_online", "last_seen_at", "created_at"]


class PrinterWithTokenSerializer(PrinterSerializer):
    """Returned only on provision/rotate, when the plaintext token is shown once."""

    class Meta(PrinterSerializer.Meta):
        fields = PrinterSerializer.Meta.fields + ["token"]


class PrintJobSerializer(serializers.ModelSerializer):
    printer_name = serializers.CharField(
        source="printer.name", read_only=True, allow_null=True
    )

    class Meta:
        model = PrintJob
        fields = [
            "id",
            "checkin",
            "printer",
            "printer_name",
            "status",
            "created_at",
            "sent_at",
            "completed_at",
        ]
        read_only_fields = ["id", "created_at", "sent_at", "completed_at"]
