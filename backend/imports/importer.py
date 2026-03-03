"""
Database import engine for external booking JSON data.
Uses parser.py for data extraction, then creates/updates Django model instances.
"""

from __future__ import annotations

import logging
import uuid

from django.db import transaction
from django.utils import timezone

from events.models import Event, EventTicket, Session, SessionTicket
from families.models import Child, Family, Parent

from .models import EventImportConfig, ImportRun
from .parser import parse_booking

logger = logging.getLogger(__name__)


def run_import(raw_json: dict, config: EventImportConfig, user) -> ImportRun:
    """
    Main entry point. Process all bookings in raw_json using config.field_mappings.

    For each booking key in raw_json:
      1. Parse booking via parse_booking()
      2. Look up Family by external_booking_id = Booking ID
      3. If not found: create Family + Parent records
      4. If found: skip family/guardian creation (idempotent)
      5. For each child:
         a. Look up by (family, first_name, last_name, birthdate)
         b. If found: log as skipped
         c. If not found: create Child, then create EventTicket or SessionTicket
      6. Log result per booking

    Each booking is processed independently — failures don't stop others.

    Returns the completed ImportRun instance.
    """
    run = ImportRun.objects.create(
        config=config,
        triggered_by=user,
        status=ImportRun.STATUS_RUNNING,
        started_at=timezone.now(),
    )

    log_entries: list[dict] = []
    summary = {
        "total_bookings": 0,
        "families_created": 0,
        "families_skipped": 0,
        "children_created": 0,
        "children_skipped": 0,
        "tickets_created": 0,
        "errors": [],
        "warnings": [],
    }

    event: Event = config.event
    prefix_mappings: dict = config.field_mappings

    # Pre-fetch sessions referenced in mappings (avoid repeated queries)
    session_cache: dict[str, Session] = {}
    for mapping_value in prefix_mappings.values():
        if mapping_value not in ("full_event", "ignore"):
            try:
                session_id = uuid.UUID(mapping_value)
                if str(session_id) not in session_cache:
                    session_cache[str(session_id)] = Session.objects.get(pk=session_id, event=event)
            except (ValueError, Session.DoesNotExist):
                summary["warnings"].append(
                    f"Session {mapping_value} not found for event {event.id} — mapping will be skipped"
                )

    for booking_key, booking in raw_json.items():
        if not isinstance(booking, dict):
            continue

        summary["total_bookings"] += 1

        try:
            parsed = parse_booking(booking, prefix_mappings)
        except Exception as exc:
            msg = f"Parse error for {booking_key}: {exc}"
            logger.warning(msg)
            summary["errors"].append(msg)
            log_entries.append({"booking_key": booking_key, "action": "error", "details": msg})
            continue

        booking_id = parsed["booking_id"]
        if not booking_id:
            msg = f"Missing Booking ID for {booking_key} — skipping"
            summary["warnings"].append(msg)
            log_entries.append({"booking_key": booking_key, "action": "warning", "details": msg})
            continue

        try:
            _process_booking(
                booking_key=booking_key,
                parsed=parsed,
                event=event,
                session_cache=session_cache,
                summary=summary,
                log_entries=log_entries,
            )
        except Exception as exc:
            msg = f"Import error for booking {booking_id} ({booking_key}): {exc}"
            logger.exception(msg)
            summary["errors"].append(msg)
            log_entries.append({"booking_key": booking_key, "action": "error", "details": msg})

    run.status = ImportRun.STATUS_COMPLETED
    run.finished_at = timezone.now()
    run.log = log_entries
    run.summary = summary
    run.save()

    return run


def _process_booking(
    *,
    booking_key: str,
    parsed: dict,
    event: Event,
    session_cache: dict[str, Session],
    summary: dict,
    log_entries: list[dict],
) -> None:
    """Process one booking: create or skip family/guardians, then reconcile children."""
    booking_id = parsed["booking_id"]
    contact = parsed["contact"]
    extra_guardian = parsed["extra_guardian"]
    children_data = parsed["children"]

    with transaction.atomic():
        # Family resolution
        family = Family.objects.filter(external_booking_id=booking_id).first()
        if family is None:
            # Build family last_name from contact
            last_name = contact.get("last_name") or ""
            family = Family.objects.create(
                external_booking_id=booking_id,
                last_name=last_name,
            )
            summary["families_created"] += 1

            # Create primary contact as Parent
            _create_parent(family, contact)

            # Create extra guardian if present
            if extra_guardian:
                _create_parent(family, extra_guardian)

            log_entries.append({
                "booking_key": booking_key,
                "action": "family_created",
                "details": f"Created family {family.id} for booking {booking_id}",
            })
        else:
            summary["families_skipped"] += 1
            log_entries.append({
                "booking_key": booking_key,
                "action": "family_skipped",
                "details": f"Family {family.id} already exists for booking {booking_id}",
            })

        # Child reconciliation
        for child_data in children_data:
            _process_child(
                child_data=child_data,
                family=family,
                event=event,
                session_cache=session_cache,
                summary=summary,
                log_entries=log_entries,
                booking_key=booking_key,
            )


def _create_parent(family: Family, contact: dict) -> Parent:
    """Create a Parent record from contact dict."""
    first = contact.get("first_name", "")
    last = contact.get("last_name", "")
    name = f"{first} {last}".strip() or first or last or "Unknown"
    return Parent.objects.create(
        family=family,
        name=name,
        email=contact.get("email") or None,
        phone=contact.get("phone") or None,
        relationship_type="OTHER",
    )


def _process_child(
    *,
    child_data: dict,
    family: Family,
    event: Event,
    session_cache: dict[str, Session],
    summary: dict,
    log_entries: list[dict],
    booking_key: str,
) -> None:
    """Create or skip a child and their ticket."""
    first_name = child_data["first_name"]
    last_name = child_data.get("last_name", "")
    birthdate = child_data.get("birthdate")
    allergies = child_data.get("allergies")
    eticket_code = child_data.get("eticket_code")
    mapping = child_data.get("mapping", "full_event")

    if not first_name:
        return

    # Look up child by (family, first_name, last_name, birthdate)
    lookup: dict = {"family": family, "first_name": first_name, "last_name": last_name}
    if birthdate is not None:
        lookup["birthdate"] = birthdate

    existing = Child.objects.filter(**lookup).first()
    if existing is not None:
        summary["children_skipped"] += 1
        log_entries.append({
            "booking_key": booking_key,
            "action": "child_skipped",
            "details": f"Child {first_name} {last_name} already exists (id={existing.id})",
        })
        return

    # Need a birthdate to create the child — it's a required field
    if birthdate is None:
        msg = f"Missing birthdate for child {first_name} {last_name} in booking {booking_key} — skipping"
        summary["warnings"].append(msg)
        log_entries.append({"booking_key": booking_key, "action": "warning", "details": msg})
        return

    child = Child.objects.create(
        family=family,
        first_name=first_name,
        last_name=last_name,
        birthdate=birthdate,
        allergies=allergies,
    )
    summary["children_created"] += 1

    # Create ticket
    if mapping == "full_event":
        EventTicket.objects.get_or_create(
            child=child,
            event=event,
            defaults={"external_ticket_code": eticket_code},
        )
        summary["tickets_created"] += 1
        log_entries.append({
            "booking_key": booking_key,
            "action": "child_created",
            "details": f"Created child {child.id} ({first_name} {last_name}) with EventTicket",
        })
    elif mapping in session_cache:
        session = session_cache[mapping]
        SessionTicket.objects.get_or_create(
            child=child,
            session=session,
            defaults={"external_ticket_code": eticket_code},
        )
        summary["tickets_created"] += 1
        log_entries.append({
            "booking_key": booking_key,
            "action": "child_created",
            "details": f"Created child {child.id} ({first_name} {last_name}) with SessionTicket for {session.name}",
        })
    else:
        summary["warnings"].append(
            f"No valid session for mapping '{mapping}' — child {first_name} {last_name} created without ticket"
        )
        log_entries.append({
            "booking_key": booking_key,
            "action": "child_created_no_ticket",
            "details": f"Created child {child.id} ({first_name} {last_name}) without ticket (invalid mapping)",
        })
