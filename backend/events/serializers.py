from rest_framework import serializers

from .models import Event, EventTicket, Session, SessionTicket, Ticket


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ["id", "name", "start_date", "end_date"]
        read_only_fields = ["id"]


class SessionSerializer(serializers.ModelSerializer):
    event_name = serializers.CharField(source="event.name", read_only=True)
    effective_ticket_rule = serializers.CharField(read_only=True)
    # Derived, READ-ONLY compatibility fields (2026-10-01). The check-in UI
    # still reads `requires_ticket` and `effective_parent_checkin_policy`; the
    # rows no longer store them, so they are computed from the new rule and
    # keep an older frontend working until the check-in UI moves to
    # `effective_ticket_rule` / `adults_not_checked_in`. Delete both (and the
    # two methods) in that increment. They cannot be written: the old
    # writable `requires_ticket` / `parent_checkin_policy` columns drive
    # nothing any more, so accepting them would be a dead control.
    requires_ticket = serializers.SerializerMethodField()
    effective_parent_checkin_policy = serializers.SerializerMethodField()

    def get_requires_ticket(self, obj) -> bool:
        return obj.children_need_ticket

    def get_effective_parent_checkin_policy(self, obj) -> str:
        if obj.adults_not_checked_in:
            return "disabled"
        return "ticket_required" if obj.adults_need_ticket else "open"

    class Meta:
        model = Session
        fields = [
            "id",
            "name",
            "start_time",
            "end_time",
            "is_active",
            "ticket_rule",
            "effective_ticket_rule",
            "adults_not_checked_in",
            "requires_ticket",
            "effective_parent_checkin_policy",
            "event",
            "event_name",
        ]
        read_only_fields = ["id"]


class TicketSerializer(serializers.ModelSerializer):
    """
    DEPRECATED: Use EventTicketSerializer or SessionTicketSerializer instead.
    This serializer is maintained for backwards compatibility only.
    """

    child = serializers.PrimaryKeyRelatedField(
        source="attendee",
        queryset=Ticket._meta.get_field("attendee").related_model.objects.all(),
    )
    child_name = serializers.SerializerMethodField()
    session_name = serializers.CharField(
        source="session.name", read_only=True, allow_null=True
    )

    class Meta:
        model = Ticket
        fields = ["id", "type", "child", "child_name", "session", "session_name"]
        read_only_fields = ["id"]

    def get_child_name(self, obj):
        return f"{obj.attendee.first_name} {obj.attendee.last_name}"


class EventTicketSerializer(serializers.ModelSerializer):
    """
    Serializer for event tickets (passes that grant access to all sessions in an event).
    """

    # Keep JSON key "child" for frontend back-compat; maps to attendee FK.
    child = serializers.PrimaryKeyRelatedField(
        source="attendee",
        queryset=EventTicket._meta.get_field("attendee").related_model.objects.all(),
    )
    child_name = serializers.SerializerMethodField()
    event_name = serializers.CharField(source="event.name", read_only=True)
    ticket_type = serializers.SerializerMethodField()

    class Meta:
        model = EventTicket
        fields = [
            "id",
            "child",
            "child_name",
            "event",
            "event_name",
            "ticket_type",
            "external_ticket_code",
        ]
        read_only_fields = ["id", "external_ticket_code"]

    def get_child_name(self, obj) -> str:
        return f"{obj.attendee.first_name} {obj.attendee.last_name}"

    def get_ticket_type(self, obj) -> str:
        return "EVENT_PASS"


class SessionTicketSerializer(serializers.ModelSerializer):
    """
    Serializer for session tickets (tickets that grant access to a specific session).
    """

    # Keep JSON key "child" for frontend back-compat; maps to attendee FK.
    child = serializers.PrimaryKeyRelatedField(
        source="attendee",
        queryset=SessionTicket._meta.get_field("attendee").related_model.objects.all(),
    )
    child_name = serializers.SerializerMethodField()
    session_name = serializers.CharField(source="session.name", read_only=True)
    event_name = serializers.CharField(source="session.event.name", read_only=True)
    ticket_type = serializers.SerializerMethodField()

    class Meta:
        model = SessionTicket
        fields = [
            "id",
            "child",
            "child_name",
            "session",
            "session_name",
            "event_name",
            "ticket_type",
            "external_ticket_code",
        ]
        read_only_fields = ["id", "external_ticket_code"]

    def get_child_name(self, obj) -> str:
        return f"{obj.attendee.first_name} {obj.attendee.last_name}"

    def get_ticket_type(self, obj) -> str:
        return "SESSION_TICKET"
