import uuid

from django.db import models


class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        db_table = "events"

    def __str__(self) -> str:
        return self.name


class Session(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_active = models.BooleanField(default=False)
    requires_ticket = models.BooleanField(default=False)
    event = models.ForeignKey(Event, related_name="sessions", on_delete=models.CASCADE)

    class Meta:
        db_table = "sessions"
        indexes = [
            models.Index(fields=["event"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.event.name} - {self.name}"


class Ticket(models.Model):
    EVENT_PASS = "EVENT_PASS"
    SESSION_TICKET = "SESSION_TICKET"
    NONE = "NONE"

    TICKET_TYPES = [
        (EVENT_PASS, "Event Pass"),
        (SESSION_TICKET, "Session Ticket"),
        (NONE, "None"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=32, choices=TICKET_TYPES)
    child = models.ForeignKey("families.Child", related_name="tickets", on_delete=models.CASCADE)
    session = models.ForeignKey(
        Session, related_name="tickets", on_delete=models.CASCADE, null=True, blank=True
    )

    class Meta:
        db_table = "tickets"
        indexes = [
            models.Index(fields=["child"]),
            models.Index(fields=["session"]),
        ]

    def __str__(self) -> str:
        return f"{self.type} for {self.child}"
