"""Cross-ticket composition rules for a Registration.

Distinct from pricing.py (which only sums what's already on the
registration): this module validates *which combinations* of TicketType
selections are allowed, via TicketType.requires_ticket_type/
max_per_required (e.g. a free "family member" type requiring a paid
"family ticket" type, capped at N free members per paid ticket).
"""

from collections import defaultdict

from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError

from events.models import TicketType


def validate_ticket_composition(registration) -> None:
    """Call once all of a registration's EventTicket/SessionTicket rows
    exist (after the attendee loop in _create_registration). Counts
    distinct attendees per ticket_type — a session_bundle ticket type fans
    out into one SessionTicket per covered session for the same attendee,
    so counting by attendee (not by row) avoids over-counting a single
    guardian's multi-day pass. Raises ValidationError, matching the style
    of _validate_ticket_type_for_attendee."""
    attendees_by_type: dict[str, set] = defaultdict(set)
    for ticket in registration.event_tickets.all():
        if ticket.ticket_type_id is not None:
            attendees_by_type[ticket.ticket_type_id].add(ticket.attendee_id)
    for ticket in registration.session_tickets.all():
        if ticket.ticket_type_id is not None:
            attendees_by_type[ticket.ticket_type_id].add(ticket.attendee_id)

    if not attendees_by_type:
        return

    ticket_types = TicketType.objects.in_bulk(attendees_by_type.keys())

    for ticket_type_id, attendee_ids in attendees_by_type.items():
        ticket_type = ticket_types[ticket_type_id]
        if ticket_type.requires_ticket_type_id is None:
            continue

        count = len(attendee_ids)
        required_count = len(
            attendees_by_type.get(ticket_type.requires_ticket_type_id, ())
        )
        required_name = ticket_type.requires_ticket_type.name

        if required_count == 0:
            raise ValidationError(
                _("%(name)s requires at least one %(required)s ticket.")
                % {"name": ticket_type.name, "required": required_name}
            )
        if (
            ticket_type.max_per_required is not None
            and count > required_count * ticket_type.max_per_required
        ):
            raise ValidationError(
                _(
                    "Too many %(name)s tickets for the number of "
                    "%(required)s tickets (max %(max)s per)."
                )
                % {
                    "name": ticket_type.name,
                    "required": required_name,
                    "max": ticket_type.max_per_required,
                }
            )
