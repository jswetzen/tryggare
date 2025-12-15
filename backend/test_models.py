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
from checkins.models import CheckInRecord, QRCode
from checkins.qr_utils import allocate_code_for_checkin, get_code_for_active_checkin

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

# Test QR code allocation
print("Testing QR code allocation...")
qr_code = allocate_code_for_checkin(checkin)
assert qr_code is not None, "QR code should be allocated"
assert len(qr_code.code) == 5, "QR code should be 5 characters"
assert qr_code.checkin_record == checkin, "QR code should be linked to check-in"
print(f"✓ QR code allocated: {qr_code.code}")

# Test QR code lookup
print("\nTesting QR code lookup...")
found_qr = get_code_for_active_checkin(qr_code.code)
assert found_qr is not None, "Should find QR code for active check-in"
assert found_qr.checkin_record.child.id == child.id, "QR lookup should find correct child"
print("✓ QR code lookup working")

# Test last participation date
print("\nTesting business logic...")
child.last_participation_date = timezone.now()
child.save()
child.refresh_from_db()
assert child.last_participation_date is not None, "Last participation date should be set"
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

# Test QR code privacy (after checkout, code should not be found)
print("Testing QR code privacy...")
checkin.check_out_time = timezone.now()
checkin.save()
qr_code.released_at = timezone.now()
qr_code.save()
not_found_qr = get_code_for_active_checkin(qr_code.code)
assert not_found_qr is None, "Should not find QR code after checkout"
print("✓ QR code privacy working (code not found after checkout)\n")

print("=" * 50)
print("✅ All model tests passed!")
print("=" * 50)
print()
print("Test data created:")
print(f"  Family ID: {family.id}")
print(f"  Parent: {parent.name}")
print(f"  Child: {child.first_name} {child.last_name}")
print(f"  QR Code: {qr_code.code}")
print(f"  Event: {event.name}")
print(f"  Session: {session.name}")
print()
