from rest_framework import serializers

from .models import Event, Session, Ticket


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
    child_name = serializers.SerializerMethodField()
    session_name = serializers.CharField(source="session.name", read_only=True, allow_null=True)

    class Meta:
        model = Ticket
        fields = ["id", "type", "child", "child_name", "session", "session_name"]
        read_only_fields = ["id"]

    def get_child_name(self, obj):
        return f"{obj.child.first_name} {obj.child.last_name}"
