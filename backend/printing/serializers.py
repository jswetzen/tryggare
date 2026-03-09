from rest_framework import serializers
from .models import Printer, PrintJob


class PrinterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Printer
        fields = ["id", "name", "is_online", "last_seen_at", "created_at"]
        read_only_fields = ["last_seen_at", "created_at"]


class PrintJobSerializer(serializers.ModelSerializer):
    printer_name = serializers.CharField(source="printer.name", read_only=True, allow_null=True)

    class Meta:
        model = PrintJob
        fields = ["id", "checkin", "printer", "printer_name", "status", "created_at", "sent_at", "completed_at"]
        read_only_fields = ["id", "created_at", "sent_at", "completed_at"]
