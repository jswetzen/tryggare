import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class Family(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    last_name = models.CharField(max_length=255, verbose_name=_("Last Name"), blank=True, default="")
    last_participation_date = models.DateTimeField(null=True, blank=True, verbose_name=_("Last Participation Date"))
    external_booking_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True,
        verbose_name=_("External Booking ID"),
        help_text=_("Booking ID from the external registration system (e.g. '10869')."),
    )

    class Meta:
        db_table = "families"
        verbose_name = _("Family")
        verbose_name_plural = _("Families")
        indexes = [
            models.Index(fields=["last_name"]),
        ]

    def __str__(self) -> str:
        if self.last_name:
            return self.last_name
        return f"Family {self.id}" if not self.parents.exists() else f"{self.parents.first().name}'s family"

    @property
    def display_name(self) -> str:
        """
        Returns a formatted display name for the family.

        Returns:
            str: "{last_name}" or a fallback based on family ID or parent name
        """
        if self.last_name:
            return self.last_name
        return f"Family {self.id}" if not self.parents.exists() else f"{self.parents.first().name}'s family"


class Parent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name=_("Name"))
    phone = models.CharField(max_length=50, null=True, blank=True, verbose_name=_("Phone"))
    email = models.EmailField(null=True, blank=True, verbose_name=_("Email"))
    relationship_type = models.CharField(max_length=64, verbose_name=_("Relationship Type"))
    last_participation_date = models.DateTimeField(null=True, blank=True, verbose_name=_("Last Participation Date"))
    family = models.ForeignKey(Family, related_name="parents", on_delete=models.CASCADE, verbose_name=_("Family"))

    class Meta:
        db_table = "parents"
        verbose_name = _("Parent")
        verbose_name_plural = _("Parents")
        indexes = [
            models.Index(fields=["family"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.relationship_type})"


class Child(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=255, verbose_name=_("First Name"))
    last_name = models.CharField(max_length=255, verbose_name=_("Last Name"))
    birthdate = models.DateField(null=True, blank=True, verbose_name=_("Birthdate"))
    allergies = models.TextField(null=True, blank=True, verbose_name=_("Allergies"))
    notes = models.TextField(null=True, blank=True, verbose_name=_("Notes"))
    last_participation_date = models.DateTimeField(null=True, blank=True, verbose_name=_("Last Participation Date"))
    family = models.ForeignKey(Family, related_name="children", on_delete=models.CASCADE, verbose_name=_("Family"))

    class Meta:
        db_table = "children"
        verbose_name = _("Child")
        verbose_name_plural = _("Children")
        indexes = [
            models.Index(fields=["last_name"]),
            models.Index(fields=["family"]),
        ]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def has_ticket(self) -> bool:
        """
        Check if the child has any type of ticket.

        Returns:
            bool: True if child has an event ticket or session ticket, False otherwise
        """
        return self.event_tickets.exists() or self.session_tickets.exists()

    def get_ticket_type(self) -> str:
        """
        Get the type of ticket the child has.

        Returns:
            str: 'event' if child has an event ticket,
                 'session' if child has session tickets (but no event ticket),
                 'none' if child has no tickets

        Note: Event tickets take precedence over session tickets as they provide
              broader access to all sessions within an event.
        """
        if self.event_tickets.exists():
            return 'event'
        elif self.session_tickets.exists():
            return 'session'
        else:
            return 'none'

    def get_ticket_details(self) -> dict:
        """
        Get detailed information about the child's tickets.

        Returns:
            dict: A dictionary containing ticket information with the following structure:
                  - ticket_type: 'event', 'session', or 'none'
                  - event_tickets: List of event ticket details (if any)
                  - session_tickets: List of session ticket details (if any)

        Example:
            {
                'ticket_type': 'event',
                'event_tickets': [{'id': '...', 'event': 'Conference 2025', 'event_id': '...'}],
                'session_tickets': []
            }

        Note:
            This method uses prefetched data if available to avoid N+1 queries.
            Ensure event_tickets and session_tickets are prefetched with select_related
            for optimal performance.
        """
        ticket_type = self.get_ticket_type()

        event_tickets_data = []
        session_tickets_data = []

        for event_ticket in self.event_tickets.all():
            event_tickets_data.append({
                'id': str(event_ticket.id),
                'event': str(event_ticket.event.id),
                'event_name': event_ticket.event.name,
            })

        for session_ticket in self.session_tickets.all():
            session_tickets_data.append({
                'id': str(session_ticket.id),
                'session': str(session_ticket.session.id),
                'session_name': session_ticket.session.name,
            })

        return {
            'ticket_type': ticket_type,
            'event_tickets': event_tickets_data,
            'session_tickets': session_tickets_data,
        }
