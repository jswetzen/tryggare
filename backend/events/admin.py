from django.contrib import admin

from .models import Event, Session, Ticket


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
    list_display = ("type", "child", "session")
    list_filter = ("type",)
    search_fields = ("child__first_name", "child__last_name", "session__name")
