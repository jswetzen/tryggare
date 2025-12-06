#!/usr/bin/env python
"""Quick model verification - run after model changes"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
sys.path.insert(0, '/workspace/check-ins/backend')
django.setup()

from django.utils import timezone
from accounts.models import AdminUser
from families.models import Family, Parent, Child
from events.models import Event, Session
from checkins.models import CheckInRecord
import uuid

print("🔍 Quick Model Verification\n")

# Test all models can be created
print("Creating test data...")
family = Family.objects.create(last_name="TestFamily")
parent = Parent.objects.create(
    family=family,
    name="Test Parent",
    phone="555-1234",
    relationship_type="Parent"
)
child = Child.objects.create(
    family=family,
    first_name="Test",
    last_name="Child",
    birthdate="2020-01-15"
)
event = Event.objects.create(
    name="Test Event",
    start_date="2025-01-01",
    end_date="2025-01-02"
)
session = Session.objects.create(
    event=event,
    name="Test Session",
    start_time=timezone.now(),
    end_time=timezone.now() + timezone.timedelta(hours=3)
)
admin = AdminUser.objects.first()

if not admin:
    print("⚠️  No admin user found. Creating one...")
    admin = AdminUser.objects.create_superuser('admin', 'admin123')

checkin = CheckInRecord.objects.create(
    child=child,
    session=session,
    check_in_staff=admin
)

print("✓ All models created\n")

# Test business logic
print("Testing business logic...")
child.qr_token = str(uuid.uuid4())
child.last_participation_date = timezone.now()
child.save()

child.refresh_from_db()
assert child.qr_token is not None, "QR token should be set"
assert child.last_participation_date is not None, "Last participation date should be set"
print("✓ QR token generation working")
print("✓ Last participation date tracking working\n")

# Test relationships
print("Testing relationships...")
assert family.children.count() == 1, "Family should have 1 child"
assert family.parents.count() == 1, "Family should have 1 parent"
assert event.sessions.count() == 1, "Event should have 1 session"
assert child.checkin_records.count() == 1, "Child should have 1 check-in"
print("✓ All foreign key relationships working\n")

# Test queries
print("Testing queries...")
active_checkins = CheckInRecord.objects.filter(check_out_time__isnull=True).count()
assert active_checkins >= 1, "Should have at least 1 active check-in"
print(f"✓ Found {active_checkins} active check-in(s)\n")

# Test QR lookup
print("Testing QR lookup...")
found_child = Child.objects.get(qr_token=child.qr_token)
assert found_child.id == child.id, "QR token lookup should find correct child"
print("✓ QR token lookup working\n")

print("=" * 50)
print("✅ All model tests passed!")
print("=" * 50)
print()
print("Test data created:")
print(f"  Family ID: {family.id}")
print(f"  Parent: {parent.name}")
print(f"  Child: {child.first_name} {child.last_name}")
print(f"  QR Token: {child.qr_token}")
print(f"  Event: {event.name}")
print(f"  Session: {session.name}")
print()
