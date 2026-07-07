from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Registration


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = (
        "reference_code",
        "event",
        "contact_email",
        "status",
        "submitted_at",
        "verified_at",
    )
    list_filter = ("status", "event")
    search_fields = ("reference_code", "contact_email")
    readonly_fields = (
        "id",
        "family",
        "reference_code",
        "verification_token_hash",
        "submitted_at",
        "verified_at",
        "verification_sent_at",
        "expires_at",
        "created_new_family",
    )
    actions = ["cancel_registrations"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("event", "family")

    @admin.action(description=_("Cancel selected registrations"))
    def cancel_registrations(self, request, queryset):
        updated = queryset.exclude(status=Registration.Status.CANCELLED).update(
            status=Registration.Status.CANCELLED
        )
        self.message_user(request, _(f"{updated} registration(s) cancelled."))
