from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _

from config.admin import HiddenFromIndexAdmin

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

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if request.user.is_superuser:
            return fields
        # The plaintext token IS the printer's credential. Read-only display is
        # not a weaker form of "can rotate it" — anyone who can read it can
        # impersonate the printer. Administratör is explicitly not trusted with
        # the credential's lifecycle, so it does not get to read it either.
        # ``token_active`` on the changelist still answers "is this printer's
        # token healthy", which is the question the role actually has.
        return [field for field in fields if field != "token"]

    @admin.display(boolean=True, description=_("Token active"))
    def token_active(self, obj):
        return obj.token_active

    @admin.action(
        description=_("Rotate token (invalidates the old one)"),
        # Without this, the action runs for anyone who can *view* the
        # changelist — which would have handed printer-token rotation to every
        # Administratör through the back door, the exact grant the role
        # definition withholds. ``add`` is the permission the equivalent API
        # action (POST rotate-token) needs, and no seeded role holds it.
        permissions=["add"],
    )
    def rotate_tokens(self, request, queryset):
        for printer in queryset:
            printer.rotate_token()
        self.message_user(
            request,
            _(
                "Rotated tokens for %(count)d printer(s). Update each "
                "printer-client with its new token."
            )
            % {"count": queryset.count()},
            level=messages.SUCCESS,
        )

    @admin.action(
        description=_("Revoke token (disables the printer)"), permissions=["add"]
    )
    def revoke_tokens(self, request, queryset):
        count = 0
        for printer in queryset:
            printer.revoke_token()
            count += 1
        self.message_user(
            request,
            _("Revoked tokens for %(count)d printer(s).") % {"count": count},
            level=messages.SUCCESS,
        )


@admin.register(PrintJob)
class PrintJobAdmin(HiddenFromIndexAdmin, admin.ModelAdmin):
    """Queue rows the printing service writes and drains by itself. Hidden
    from the index; still reachable by URL when a badge did not come out."""

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
