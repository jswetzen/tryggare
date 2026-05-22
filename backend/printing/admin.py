from django.contrib import admin
from .models import Printer, PrintJob


@admin.register(Printer)
class PrinterAdmin(admin.ModelAdmin):
    list_display = ["name", "is_online", "last_seen_at", "created_at"]
    list_filter = ["is_online"]
    readonly_fields = ["created_at"]


@admin.register(PrintJob)
class PrintJobAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "checkin",
        "printer",
        "status",
        "created_at",
        "sent_at",
        "completed_at",
    ]
    list_filter = ["status", "printer"]
    readonly_fields = ["created_at"]
