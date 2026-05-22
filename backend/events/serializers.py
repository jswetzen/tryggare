from rest_framework import serializers

from .models import Event, EventTicket, Session, SessionTicket, Ticket


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ["id", "name", "start_date", "end_date"]
        read_only_fields = ["id"]


class SessionSerializer(serializers.ModelSerializer):
    event_name = serializers.CharField(source="event.name", read_only=True)

    class Meta:
        model = Session
        fields = [
            "id",
            "name",
            "start_time",
            "end_time",
            "is_active",
            "requires_ticket",
            "event",
            "event_name",
        ]
        read_only_fields = ["id"]


class TicketSerializer(serializers.ModelSerializer):
    """
    DEPRECATED: Use EventTicketSerializer or SessionTicketSerializer instead.
    This serializer is maintained for backwards compatibility only.
    """

    child_name = serializers.SerializerMethodField()
    session_name = serializers.CharField(
        source="session.name", read_only=True, allow_null=True
    )

    class Meta:
        model = Ticket
        fields = ["id", "type", "child", "child_name", "session", "session_name"]
        read_only_fields = ["id"]

    def get_child_name(self, obj):
        return f"{obj.child.first_name} {obj.child.last_name}"


class EventTicketSerializer(serializers.ModelSerializer):
    """
    Serializer for event tickets (passes that grant access to all sessions in an event).
    """

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
        return f"{obj.child.first_name} {obj.child.last_name}"

    def get_ticket_type(self, obj) -> str:
        return "EVENT_PASS"


class SessionTicketSerializer(serializers.ModelSerializer):
    """
    Serializer for session tickets (tickets that grant access to a specific session).
    """

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
        return f"{obj.child.first_name} {obj.child.last_name}"

    def get_ticket_type(self, obj) -> str:
        return "SESSION_TICKET"
