from django.contrib import admin, messages

from .models import Printer, PrintJob


@admin.register(Printer)
class PrinterAdmin(admin.ModelAdmin):
    list_display = ["name", "is_online", "token_active", "last_seen_at", "created_at"]
    list_filter = ["is_online"]
    # Token is shown read-only so an operator can copy it into the client config;
    # it is generated automatically on save (model default).
    readonly_fields = [
        "id",
        "token",
        "token_created_at",
        "token_revoked_at",
        "created_at",
    ]
    actions = ["rotate_tokens", "revoke_tokens"]

    @admin.display(boolean=True, description="Token active")
    def token_active(self, obj):
        return obj.token_active

    @admin.action(description="Rotate token (invalidates the old one)")
    def rotate_tokens(self, request, queryset):
        for printer in queryset:
            printer.rotate_token()
        self.message_user(
            request,
            f"Rotated tokens for {queryset.count()} printer(s). "
            "Update each printer-client with its new token.",
            level=messages.SUCCESS,
        )

    @admin.action(description="Revoke token (disables the printer)")
    def revoke_tokens(self, request, queryset):
        count = 0
        for printer in queryset:
            printer.revoke_token()
            count += 1
        self.message_user(
            request, f"Revoked tokens for {count} printer(s).", level=messages.SUCCESS
        )


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
