#!/usr/bin/env python
"""
Test new features: QR page actions and nested family creation
Run with: uv run python test_new_features.py
"""
import os
import sys
import django
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
sys.path.insert(0, '/workspace/check-ins/backend')
django.setup()

from django.test import Client
from django.utils import timezone
from accounts.models import AdminUser
from families.models import Family, Child, Parent
from events.models import Event, Session
from checkins.models import CheckInRecord
import json

print("🧪 Testing New Features: QR Actions & Family Creation\n")
print("=" * 60)

client = Client()

# Setup: Create admin user
admin = AdminUser.objects.first()
if not admin:
    print("Creating admin user...")
    admin = AdminUser.objects.create_superuser('admin', 'admin123')
    print("✓ Admin created\n")

client.force_login(admin)

# ============================================================================
# TEST 1: Nested Family Creation
# ============================================================================
print("\n📋 TEST 1: Nested Family Creation")
print("-" * 60)

print("Creating family with 2 parents and 2 children...")
family_data = {
    "parents": [
        {
            "name": "Jane Doe",
            "phone": "555-1234",
            "email": "jane@example.com",
            "relationship_type": "Mom"
        },
        {
            "name": "John Doe",
            "phone": "555-5678",
            "email": "john@example.com",
            "relationship_type": "Dad"
        }
    ],
    "children": [
        {
            "first_name": "Alice",
            "last_name": "Doe",
            "birthdate": "2015-03-15",
            "allergies": "Peanuts",
            "notes": "Requires EpiPen"
        },
        {
            "first_name": "Bob",
            "last_name": "Doe",
            "birthdate": "2018-07-22",
            "allergies": "",
            "notes": ""
        }
    ]
}

response = client.post(
    '/api/families/',
    json.dumps(family_data),
    content_type='application/json'
)

assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.content.decode()}"
created_family = response.json()
family_id = created_family['id']
print(f"✓ Family created: {family_id}")

# Verify family has correct number of parents and children
family = Family.objects.get(id=family_id)
parents = family.parents.all()
children = family.children.all()

assert parents.count() == 2, f"Expected 2 parents, got {parents.count()}"
print(f"✓ Family has {parents.count()} parents")

assert children.count() == 2, f"Expected 2 children, got {children.count()}"
print(f"✓ Family has {children.count()} children")

# Verify parent details
jane = parents.get(name="Jane Doe")
assert jane.phone == "555-1234", f"Wrong phone: {jane.phone}"
assert jane.email == "jane@example.com", f"Wrong email: {jane.email}"
assert jane.relationship_type == "Mom", f"Wrong relationship: {jane.relationship_type}"
print("✓ Parent details correct")

# Verify child details
alice = children.get(first_name="Alice")
assert alice.last_name == "Doe", f"Wrong last name: {alice.last_name}"
assert str(alice.birthdate) == "2015-03-15", f"Wrong birthdate: {alice.birthdate}"
assert alice.allergies == "Peanuts", f"Wrong allergies: {alice.allergies}"
assert alice.notes == "Requires EpiPen", f"Wrong notes: {alice.notes}"
print("✓ Child details correct")

print("\n✅ TEST 1 PASSED: Nested family creation works!\n")

# ============================================================================
# TEST 2: Family Creation Validation
# ============================================================================
print("\n📋 TEST 2: Family Creation Validation")
print("-" * 60)

# Test 2a: No parents
print("Testing validation: No parents...")
invalid_data = {
    "parents": [],
    "children": [
        {"first_name": "Test", "last_name": "Child", "birthdate": "2015-01-01"}
    ]
}
response = client.post(
    '/api/families/',
    json.dumps(invalid_data),
    content_type='application/json'
)
assert response.status_code == 400, f"Expected 400, got {response.status_code}"
print("✓ Correctly rejects family with no parents")

# Test 2b: No children
print("Testing validation: No children...")
invalid_data = {
    "parents": [
        {"name": "Test Parent", "relationship_type": "Mom"}
    ],
    "children": []
}
response = client.post(
    '/api/families/',
    json.dumps(invalid_data),
    content_type='application/json'
)
assert response.status_code == 400, f"Expected 400, got {response.status_code}"
print("✓ Correctly rejects family with no children")

print("\n✅ TEST 2 PASSED: Validation works correctly!\n")

# ============================================================================
# TEST 3: Undo Checkout Endpoint
# ============================================================================
print("\n📋 TEST 3: Undo Checkout Functionality")
print("-" * 60)

# Setup: Create event, session, family, and child
event = Event.objects.first()
if not event:
    event = Event.objects.create(
        name="Test Event",
        start_date=timezone.now().date(),
        end_date=timezone.now().date() + timedelta(days=1)
    )
    print(f"✓ Created test event: {event.name}")

session = Session.objects.filter(event=event, is_active=True).first()
if not session:
    session = Session.objects.create(
        event=event,
        name="Test Session",
        start_time=timezone.now(),
        end_time=timezone.now() + timedelta(hours=2),
        is_active=True
    )
    print(f"✓ Created test session: {session.name}")

# Use the family we just created
test_child = children.first()
print(f"Using test child: {test_child.first_name} {test_child.last_name}")

# Check in the child
checkin_data = {
    "child": str(test_child.id),
    "session": str(session.id)
}
response = client.post(
    '/api/checkins/check_in/',
    json.dumps(checkin_data),
    content_type='application/json'
)
assert response.status_code == 201, f"Check-in failed: {response.status_code}: {response.content.decode()}"
checkin = response.json()
checkin_id = checkin['id']
print(f"✓ Child checked in: {checkin_id}")

# Check out the child
response = client.post(
    f'/api/checkins/{checkin_id}/check_out/',
    json.dumps({"picked_up_by": "Test Parent"}),
    content_type='application/json'
)
assert response.status_code == 200, f"Check-out failed: {response.status_code}: {response.content.decode()}"
print("✓ Child checked out")

# Test 3a: Undo checkout (should work - within 5 minutes)
print("Testing undo checkout (within time window)...")
response = client.post(
    f'/api/checkins/{checkin_id}/undo_checkout/',
    json.dumps({}),
    content_type='application/json'
)
assert response.status_code == 200, f"Undo failed: {response.status_code}: {response.content.decode()}"
print("✓ Undo checkout successful")

# Verify child is checked back in
checkin_obj = CheckInRecord.objects.get(id=checkin_id)
assert checkin_obj.check_out_time is None, "Child should be checked in after undo"
assert checkin_obj.check_out_staff is None, "Check-out staff should be cleared"
assert checkin_obj.picked_up_by == "", "Picked up by should be cleared"
print("✓ Check-in record correctly restored")

# Test 3b: Undo again (should fail - already checked in)
print("Testing undo when already checked in...")
response = client.post(
    f'/api/checkins/{checkin_id}/undo_checkout/',
    json.dumps({}),
    content_type='application/json'
)
assert response.status_code == 400, f"Expected 400, got {response.status_code}"
error = response.json()
assert "not checked out" in error['error'].lower(), f"Wrong error message: {error}"
print("✓ Correctly rejects undo when not checked out")

# Test 3c: Test time window enforcement (simulate old checkout)
print("Testing undo after time window...")
# Check out again
response = client.post(
    f'/api/checkins/{checkin_id}/check_out/',
    json.dumps({"picked_up_by": "Test Parent"}),
    content_type='application/json'
)
assert response.status_code == 200, "Check-out failed"

# Manually set checkout time to 10 minutes ago
checkin_obj = CheckInRecord.objects.get(id=checkin_id)
checkin_obj.check_out_time = timezone.now() - timedelta(minutes=10)
checkin_obj.save()

# Try to undo (should fail - outside time window)
response = client.post(
    f'/api/checkins/{checkin_id}/undo_checkout/',
    json.dumps({}),
    content_type='application/json'
)
assert response.status_code == 400, f"Expected 400, got {response.status_code}"
error = response.json()
assert "too much time" in error['error'].lower(), f"Wrong error message: {error}"
print("✓ Correctly enforces 5-minute time window")

print("\n✅ TEST 3 PASSED: Undo checkout works correctly!\n")

# ============================================================================
# TEST 4: QR Token Generation
# ============================================================================
print("\n📋 TEST 4: QR Token on First Check-in")
print("-" * 60)

# Create a new child without QR token
new_child = Child.objects.create(
    family=family,
    first_name="Charlie",
    last_name="Doe",
    birthdate="2020-01-01"
)
assert new_child.qr_token is None or new_child.qr_token == "", "Child should not have QR token initially"
print(f"✓ Created child without QR token: {new_child.first_name}")

# Check in the child (should generate QR token)
checkin_data = {
    "child": str(new_child.id),
    "session": str(session.id)
}
response = client.post(
    '/api/checkins/check_in/',
    json.dumps(checkin_data),
    content_type='application/json'
)
assert response.status_code == 201, f"Check-in failed: {response.status_code}"
print("✓ Child checked in")

# Verify QR token was generated
new_child.refresh_from_db()
assert new_child.qr_token is not None and new_child.qr_token != "", "QR token should be generated"
print(f"✓ QR token generated: {new_child.qr_token[:8]}...")

# Verify it's a valid UUID format
import uuid
try:
    uuid.UUID(new_child.qr_token)
    print("✓ QR token is valid UUID format")
except ValueError:
    raise AssertionError(f"QR token is not valid UUID: {new_child.qr_token}")

print("\n✅ TEST 4 PASSED: QR token generation works!\n")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 60)
print("🎉 ALL TESTS PASSED!")
print("=" * 60)
print("\nSummary:")
print("✓ Nested family creation with multiple parents and children")
print("✓ Family creation validation (min 1 parent, min 1 child)")
print("✓ Undo checkout within 5-minute window")
print("✓ Undo checkout validation (time window, state checks)")
print("✓ QR token generation on first check-in")
print("\n✅ New features are working correctly!\n")
