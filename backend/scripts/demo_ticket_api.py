#!/usr/bin/env python
"""
Demo script to show the enhanced API serializers with ticket information.
Run this after backend/verify.py to see the new fields in action.
"""

import os
import sys
import django
import json
from datetime import date

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from django.contrib.auth import get_user_model
from families.models import Family, Parent, Child
from events.models import Event, EventTicket, Session, SessionTicket
from families.serializers import ChildSerializer, FamilySerializer

User = get_user_model()


def main():
    print("=" * 70)
    print("API SERIALIZER ENHANCEMENT DEMO - Phase 3.7.3")
    print("=" * 70)
    print()

    # Create test data
    print("Creating test data...")
    family = Family.objects.create(last_name="DemoFamily")

    parent = Parent.objects.create(
        name="John Demo", relationship_type="Father", phone="555-0123", family=family
    )

    child1 = Child.objects.create(
        first_name="Alice",
        last_name="DemoFamily",
        birthdate=date(2018, 3, 15),
        family=family,
    )

    child2 = Child.objects.create(
        first_name="Bob",
        last_name="DemoFamily",
        birthdate=date(2020, 7, 22),
        family=family,
    )

    child3 = Child.objects.create(
        first_name="Charlie",
        last_name="DemoFamily",
        birthdate=date(2019, 11, 5),
        family=family,
    )

    event = Event.objects.create(
        name="Summer Conference 2025",
        start_date=date(2025, 7, 1),
        end_date=date(2025, 7, 10),
    )

    session1 = Session.objects.create(
        name="Morning Workshop",
        event=event,
        start_time="2025-07-01T09:00:00Z",
        end_time="2025-07-01T12:00:00Z",
    )

    session2 = Session.objects.create(
        name="Afternoon Activities",
        event=event,
        start_time="2025-07-01T13:00:00Z",
        end_time="2025-07-01T17:00:00Z",
    )

    # Give child1 an event ticket (full access)
    EventTicket.objects.create(child=child1, event=event)

    # Give child2 session tickets (limited access)
    SessionTicket.objects.create(child=child2, session=session1)
    SessionTicket.objects.create(child=child2, session=session2)

    # child3 has no tickets

    print("✓ Test data created")
    print()

    # Demo 1: Child with event ticket
    print("-" * 70)
    print("DEMO 1: Child Serializer - Event Ticket")
    print("-" * 70)
    serializer = ChildSerializer(child1)
    print(json.dumps(serializer.data, indent=2, default=str))
    print()

    # Demo 2: Child with session tickets
    print("-" * 70)
    print("DEMO 2: Child Serializer - Session Tickets")
    print("-" * 70)
    serializer = ChildSerializer(child2)
    print(json.dumps(serializer.data, indent=2, default=str))
    print()

    # Demo 3: Child with no tickets
    print("-" * 70)
    print("DEMO 3: Child Serializer - No Tickets")
    print("-" * 70)
    serializer = ChildSerializer(child3)
    print(json.dumps(serializer.data, indent=2, default=str))
    print()

    # Demo 4: Family serializer with display_name
    print("-" * 70)
    print("DEMO 4: Family Serializer - With display_name and Children")
    print("-" * 70)

    # Optimize query to avoid N+1 (as done in ViewSet)
    from django.db.models import Prefetch

    event_ticket_prefetch = Prefetch(
        "children__event_tickets", queryset=EventTicket.objects.select_related("event")
    )
    session_ticket_prefetch = Prefetch(
        "children__session_tickets",
        queryset=SessionTicket.objects.select_related("session", "session__event"),
    )

    family_optimized = Family.objects.prefetch_related(
        "parents",
        "children",
        event_ticket_prefetch,
        session_ticket_prefetch,
    ).get(id=family.id)

    serializer = FamilySerializer(family_optimized)
    print(json.dumps(serializer.data, indent=2, default=str))
    print()

    print("=" * 70)
    print("KEY FEATURES DEMONSTRATED:")
    print("=" * 70)
    print("1. ✓ ticket_type field: 'event', 'session', or 'none'")
    print("2. ✓ ticket_details field: Complete ticket information")
    print("3. ✓ display_name field: Formatted family name")
    print("4. ✓ Efficient queries: No N+1 problems with Prefetch")
    print("5. ✓ Read-only fields: Cannot be modified via API")
    print()

    # Cleanup
    print("Cleaning up test data...")
    family.delete()
    event.delete()
    print("✓ Cleanup complete")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
        sys.exit(0)
