import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name=_("Event Name"))
    start_date = models.DateField(verbose_name=_("Start Date"))
    end_date = models.DateField(verbose_name=_("End Date"))

    class Meta:
        db_table = "events"
        verbose_name = _("Event")
        verbose_name_plural = _("Events")

    def __str__(self) -> str:
        return self.name


class Session(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name=_("Session Name"))
    start_time = models.DateTimeField(verbose_name=_("Start Time"))
    end_time = models.DateTimeField(verbose_name=_("End Time"))
    is_active = models.BooleanField(default=False, verbose_name=_("Is Active"))
    requires_ticket = models.BooleanField(
        default=False, verbose_name=_("Requires Ticket")
    )
    event = models.ForeignKey(
        Event,
        related_name="sessions",
        on_delete=models.CASCADE,
        verbose_name=_("Event"),
    )

    class Meta:
        db_table = "sessions"
        verbose_name = _("Session")
        verbose_name_plural = _("Sessions")
        indexes = [
            models.Index(fields=["event"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.event.name} - {self.name}"


class Ticket(models.Model):
    """
    Base model for tickets. This is kept for backwards compatibility
    but new code should use EventTicket or SessionTicket.

    DEPRECATED: This model will be removed in a future version.
    Use EventTicket or SessionTicket instead.
    """

    EVENT_PASS = "EVENT_PASS"
    SESSION_TICKET = "SESSION_TICKET"
    NONE = "NONE"

    TICKET_TYPES = [
        (EVENT_PASS, _("Event Pass")),
        (SESSION_TICKET, _("Session Ticket")),
        (NONE, _("None")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=32, choices=TICKET_TYPES)
    child = models.ForeignKey(
        "families.Child", related_name="tickets", on_delete=models.CASCADE
    )
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


class EventTicket(models.Model):
    """
    Represents a ticket/pass for an entire event.
    Gives the child access to all sessions within the event.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    child = models.ForeignKey(
        "families.Child",
        related_name="event_tickets",
        on_delete=models.CASCADE,
        verbose_name=_("Child"),
    )
    event = models.ForeignKey(
        Event,
        related_name="event_tickets",
        on_delete=models.CASCADE,
        verbose_name=_("Event"),
    )
    external_ticket_code = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_("External Ticket Code"),
        help_text=_("ETicket code from the external registration system."),
    )

    class Meta:
        db_table = "event_tickets"
        verbose_name = _("Event Ticket")
        verbose_name_plural = _("Event Tickets")
        indexes = [
            models.Index(fields=["child"]),
            models.Index(fields=["event"]),
        ]
        unique_together = [["child", "event"]]

    def __str__(self) -> str:
        return f"Event Pass: {self.child} - {self.event}"


class SessionTicket(models.Model):
    """
    Represents a ticket for a specific session.
    Gives the child access only to the specified session.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    child = models.ForeignKey(
        "families.Child",
        related_name="session_tickets",
        on_delete=models.CASCADE,
        verbose_name=_("Child"),
    )
    session = models.ForeignKey(
        Session,
        related_name="session_tickets",
        on_delete=models.CASCADE,
        verbose_name=_("Session"),
    )
    external_ticket_code = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_("External Ticket Code"),
        help_text=_("ETicket code from the external registration system."),
    )

    class Meta:
        db_table = "session_tickets"
        verbose_name = _("Session Ticket")
        verbose_name_plural = _("Session Tickets")
        indexes = [
            models.Index(fields=["child"]),
            models.Index(fields=["session"]),
        ]
        unique_together = [["child", "session"]]

    def __str__(self) -> str:
        return f"Session Ticket: {self.child} - {self.session}"
