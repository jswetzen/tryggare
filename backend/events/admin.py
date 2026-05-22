from django.contrib import admin

from .models import Event, EventTicket, Session, SessionTicket, Ticket


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date")
    search_fields = ("name",)


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("name", "event", "start_time", "end_time", "is_active")
    list_filter = ("is_active", "event")
    search_fields = ("name", "event__name")


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    """
    DEPRECATED: Use EventTicketAdmin or SessionTicketAdmin instead.
    """

    list_display = ("type", "child", "session")
    list_filter = ("type",)
    search_fields = ("child__first_name", "child__last_name", "session__name")


@admin.register(EventTicket)
class EventTicketAdmin(admin.ModelAdmin):
    """
    Admin interface for event tickets (passes).
    """

    list_display = ("child", "event", "id")
    list_filter = ("event",)
    search_fields = ("child__first_name", "child__last_name", "event__name")
    autocomplete_fields = ["child", "event"]


@admin.register(SessionTicket)
class SessionTicketAdmin(admin.ModelAdmin):
    """
    Admin interface for session tickets.
    """

    list_display = ("child", "session", "get_event", "id")
    list_filter = ("session__event",)
    search_fields = (
        "child__first_name",
        "child__last_name",
        "session__name",
        "session__event__name",
    )
    autocomplete_fields = ["child", "session"]

    def get_event(self, obj):
        return obj.session.event

    get_event.short_description = "Event"
    get_event.admin_order_field = "session__event"
