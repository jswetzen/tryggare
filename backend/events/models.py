import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class ParentCheckinPolicy(models.TextChoices):
    """Who's allowed to check in as a parent/guardian, and whether they need a ticket.

    Lives at module level (not nested in Session) so both Event and Session
    can reference ParentCheckinPolicy.choices directly — a nested class
    would force one of the two field definitions into a lambda, which Django
    migrations can't serialize.
    """

    DISABLED = "disabled", _("Disabled")
    OPEN = "open", _("Open (no ticket required)")
    TICKET_REQUIRED = "ticket_required", _("Ticket required")


class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name=_("Event Name"))
    start_date = models.DateField(verbose_name=_("Start Date"))
    end_date = models.DateField(verbose_name=_("End Date"))
    parent_checkin_policy_default = models.CharField(
        max_length=20,
        choices=ParentCheckinPolicy.choices,
        default=ParentCheckinPolicy.OPEN,
        verbose_name=_("Default Parent Check-In Policy"),
        help_text=_(
            "Applied to sessions of this event that don't set their own policy."
        ),
    )

    class Meta:
        db_table = "events"
        verbose_name = _("Event")
        verbose_name_plural = _("Events")

    def __str__(self) -> str:
        return self.name


class Session(models.Model):
    ParentCheckinPolicy = ParentCheckinPolicy

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name=_("Session Name"))
    start_time = models.DateTimeField(verbose_name=_("Start Time"))
    end_time = models.DateTimeField(verbose_name=_("End Time"))
    is_active = models.BooleanField(default=False, verbose_name=_("Is Active"))
    requires_ticket = models.BooleanField(
        default=False, verbose_name=_("Requires Ticket")
    )
    parent_checkin_policy = models.CharField(
        max_length=20,
        choices=ParentCheckinPolicy.choices,
        blank=True,
        default="",
        verbose_name=_("Parent Check-In Policy"),
        help_text=_("Leave blank to inherit the event's default policy."),
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

    @property
    def effective_parent_checkin_policy(self) -> str:
        return self.parent_checkin_policy or self.event.parent_checkin_policy_default


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
    attendee = models.ForeignKey(
        "families.Attendee", related_name="tickets", on_delete=models.CASCADE
    )
    session = models.ForeignKey(
        Session, related_name="tickets", on_delete=models.CASCADE, null=True, blank=True
    )

    class Meta:
        db_table = "tickets"
        indexes = [
            models.Index(fields=["attendee"], name="tickets_attend_0ad1b0_idx"),
            models.Index(fields=["session"]),
        ]

    def __str__(self) -> str:
        return f"{self.type} for {self.attendee}"


class EventTicket(models.Model):
    """
    Represents a ticket/pass for an entire event.
    Gives the attendee access to all sessions within the event.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attendee = models.ForeignKey(
        "families.Attendee",
        related_name="event_tickets",
        on_delete=models.CASCADE,
        verbose_name=_("Attendee"),
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
    registration = models.ForeignKey(
        "registrations.Registration",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="event_tickets",
        verbose_name=_("Registration"),
        help_text=_(
            "Set only for tickets created via public self-serve registration; "
            "staff-created tickets leave this null and are unaffected."
        ),
    )

    class Meta:
        db_table = "event_tickets"
        verbose_name = _("Event Ticket")
        verbose_name_plural = _("Event Tickets")
        indexes = [
            models.Index(fields=["attendee"], name="event_ticke_attend_22981b_idx"),
            models.Index(fields=["event"]),
        ]
        unique_together = [["attendee", "event"]]

    def __str__(self) -> str:
        return f"Event Pass: {self.attendee} - {self.event}"


class SessionTicket(models.Model):
    """
    Represents a ticket for a specific session.
    Gives the attendee access only to the specified session.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attendee = models.ForeignKey(
        "families.Attendee",
        related_name="session_tickets",
        on_delete=models.CASCADE,
        verbose_name=_("Attendee"),
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
    registration = models.ForeignKey(
        "registrations.Registration",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="session_tickets",
        verbose_name=_("Registration"),
        help_text=_(
            "Set only for tickets created via public self-serve registration; "
            "staff-created tickets leave this null and are unaffected."
        ),
    )

    class Meta:
        db_table = "session_tickets"
        verbose_name = _("Session Ticket")
        verbose_name_plural = _("Session Tickets")
        indexes = [
            models.Index(fields=["attendee"], name="session_tic_attend_c5a7b7_idx"),
            models.Index(fields=["session"]),
        ]
        unique_together = [["attendee", "session"]]

    def __str__(self) -> str:
        return f"Session Ticket: {self.attendee} - {self.session}"
