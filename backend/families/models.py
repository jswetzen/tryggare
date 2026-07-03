import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class _AttendeeSubclassAccessor:
    """Non-data descriptor giving Family.parents / Family.children as a QuerySet.

    If a Prefetch with `to_attr` has already populated the instance dict
    (e.g. Prefetch("attendees", queryset=Parent.objects.all(), to_attr="parents")),
    that list is returned wrapped in a thin proxy that also supports .first()/.exists().
    Otherwise falls back to a live filtered QuerySet.
    """

    class _ListProxy:
        """Minimal QuerySet-like wrapper around a prefetched list."""

        def __init__(self, items):
            self._items = items

        def all(self):
            return self

        def exists(self):
            return bool(self._items)

        def first(self):
            return self._items[0] if self._items else None

        def filter(self, **kwargs):  # noqa: ARG002 — best-effort passthrough
            return self  # serializer only needs iteration; no complex filtering

        def __iter__(self):
            return iter(self._items)

        def __len__(self):
            return len(self._items)

        def __bool__(self):
            return bool(self._items)

    def __init__(self, subclass_name: str):
        self._subclass_name = subclass_name
        self._attr = ""

    def __set_name__(self, owner, name: str):
        self._attr = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        # Populated by Prefetch(to_attr=...) — takes priority.
        cached = obj.__dict__.get(self._attr)
        if cached is not None:
            return self._ListProxy(cached)
        # Fall back to live queryset.
        import families.models as fm  # local to avoid module-level circular ref

        model = getattr(fm, self._subclass_name)
        return model.objects.filter(family=obj)


class Family(models.Model):
    parents = _AttendeeSubclassAccessor("Parent")
    children = _AttendeeSubclassAccessor("Child")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    last_name = models.CharField(
        max_length=255, verbose_name=_("Last Name"), blank=True, default=""
    )
    last_participation_date = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Last Participation Date")
    )
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
        return (
            f"Family {self.id}"
            if not self.parents.exists()
            else f"{self.parents.first().name}'s family"
        )

    @property
    def display_name(self) -> str:
        """
        Returns a formatted display name for the family.

        Returns:
            str: "{last_name}" or a fallback based on family ID or parent name
        """
        if self.last_name:
            return self.last_name
        return (
            f"Family {self.id}"
            if not self.parents.exists()
            else f"{self.parents.first().name}'s family"
        )


class Attendee(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=255, verbose_name=_("First Name"))
    last_name = models.CharField(
        max_length=255, verbose_name=_("Last Name"), blank=True, default=""
    )
    last_participation_date = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Last Participation Date")
    )
    family = models.ForeignKey(
        Family,
        related_name="attendees",
        on_delete=models.CASCADE,
        verbose_name=_("Family"),
    )

    class Meta:
        db_table = "attendees"
        verbose_name = _("Attendee")
        verbose_name_plural = _("Attendees")

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def has_ticket(self) -> bool:
        """
        Check if the attendee has any type of ticket.

        Returns:
            bool: True if attendee has an event ticket or session ticket, False otherwise
        """
        return self.event_tickets.exists() or self.session_tickets.exists()

    def get_ticket_type(self) -> str:
        """
        Get the type of ticket the attendee has.

        Returns:
            str: 'event' if attendee has an event ticket,
                 'session' if attendee has session tickets (but no event ticket),
                 'none' if attendee has no tickets

        Note: Event tickets take precedence over session tickets as they provide
              broader access to all sessions within an event.
        """
        if self.event_tickets.exists():
            return "event"
        elif self.session_tickets.exists():
            return "session"
        else:
            return "none"

    def get_ticket_details(self) -> dict:
        """
        Get detailed information about the attendee's tickets.

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
            event_tickets_data.append(
                {
                    "id": str(event_ticket.id),
                    "event": str(event_ticket.event.id),
                    "event_name": event_ticket.event.name,
                }
            )

        for session_ticket in self.session_tickets.all():
            session_tickets_data.append(
                {
                    "id": str(session_ticket.id),
                    "session": str(session_ticket.session.id),
                    "session_name": session_ticket.session.name,
                }
            )

        return {
            "ticket_type": ticket_type,
            "event_tickets": event_tickets_data,
            "session_tickets": session_tickets_data,
        }


class Parent(Attendee):
    phone = models.CharField(
        max_length=50, null=True, blank=True, verbose_name=_("Phone")
    )
    phone_locked = models.BooleanField(
        default=False,
        verbose_name=_("Phone Locked"),
        help_text=_("When checked, re-imports will not overwrite this phone number."),
    )
    email = models.EmailField(null=True, blank=True, verbose_name=_("Email"))
    email_locked = models.BooleanField(
        default=False,
        verbose_name=_("Email Locked"),
        help_text=_("When checked, re-imports will not overwrite this email address."),
    )
    relationship_type = models.CharField(
        max_length=64, verbose_name=_("Relationship Type")
    )

    class Meta:
        db_table = "parents"
        verbose_name = _("Parent")
        verbose_name_plural = _("Parents")

    @property
    def name(self) -> str:
        """Read-only shim for legacy code that accesses parent.name."""
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self) -> str:
        return f"{self.name} ({self.relationship_type})"


class Child(Attendee):
    birthdate = models.DateField(null=True, blank=True, verbose_name=_("Birthdate"))
    allergies = models.TextField(null=True, blank=True, verbose_name=_("Allergies"))
    notes = models.TextField(null=True, blank=True, verbose_name=_("Notes"))

    class Meta:
        db_table = "children"
        verbose_name = _("Child")
        verbose_name_plural = _("Children")

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"
