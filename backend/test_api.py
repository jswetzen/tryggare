#!/usr/bin/env python
"""API endpoint verification - run after view changes"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
sys.path.insert(0, '/workspace/check-ins/backend')
django.setup()

from django.test import Client
from accounts.models import AdminUser
from families.models import Child
from events.models import Event, Session
from checkins.models import CheckInRecord
from django.utils import timezone

print("🔍 API Endpoint Verification\n")

client = Client()
admin = AdminUser.objects.first()

if not admin:
    print("⚠️  No admin user found. Creating one...")
    admin = AdminUser.objects.create_superuser('admin', 'admin123')

# Test 1: Unauthenticated access
print("Test 1: Unauthenticated access (should fail)")
response = client.get('/api/families/')
assert response.status_code == 403, f"Expected 403, got {response.status_code}"
print("✓ Correctly requires authentication\n")

# Test 2: Authenticated access
print("Test 2: Authenticated access")
client.force_login(admin)
response = client.get('/api/families/')
assert response.status_code == 200, f"Expected 200, got {response.status_code}"
families = response.json()
print(f"✓ Got {len(families)} families\n")

# Test 3: Create family
print("Test 3: Create family")
response = client.post('/api/families/', {
    'last_name': 'Test',
    'parents': [
        {
            'name': 'Test Parent',
            'phone': '+1234567890',
            'email': 'test@example.com',
            'relationship_type': 'Parent'
        }
    ],
    'children': [
        {
            'first_name': 'TestChild',
            'last_name': 'Test',
            'birthdate': '2020-01-15',
            'allergies': None,
            'notes': None
        }
    ]
}, content_type='application/json')
assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.content}"
family_id = response.json()['id']
print(f"✓ Created family: {family_id}\n")

# Test 4: Create child
print("Test 4: Create child")
response = client.post('/api/children/', {
    'family': family_id,
    'first_name': 'Test',
    'last_name': 'Child',
    'birthdate': '2020-01-15'
}, content_type='application/json')
assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.content}"
child_id = response.json()['id']
child_data = response.json()
print(f"✓ Created child: {child_id}")
print("  (QR codes are now generated on check-in, not on child creation)\n")

# Test 5: List children
print("Test 5: List children")
response = client.get('/api/children/')
assert response.status_code == 200, f"Expected 200, got {response.status_code}"
children = response.json()
print(f"✓ Got {len(children)} children\n")

# Test 6: Get specific child
print("Test 6: Get specific child")
response = client.get(f'/api/children/{child_id}/')
assert response.status_code == 200, f"Expected 200, got {response.status_code}"
child_detail = response.json()
assert child_detail['first_name'] == 'Test'
print(f"✓ Retrieved child: {child_detail['first_name']} {child_detail['last_name']}\n")

# Test 7: QR endpoint (privacy-first - only works when checked in)
print("Test 7: QR endpoint - privacy-first behavior")

# First, create event and session for check-in
event = Event.objects.create(
    name="Test Event",
    start_date="2025-01-01",
    end_date="2025-01-02"
)
session = Session.objects.create(
    event=event,
    name="Test Session",
    start_time=timezone.now(),
    end_time=timezone.now() + timezone.timedelta(hours=3),
    is_active=True
)

# Check in the child via the API
child = Child.objects.get(id=child_id)
response = client.post('/api/checkins/check_in/', {
    'child': str(child.id),
    'session': str(session.id)
}, content_type='application/json')
assert response.status_code == 201, f"Check-in failed: {response.content}"
checkin = CheckInRecord.objects.get(id=response.json()['id'])
print("✓ Checked in child to session")

# Get the allocated QR code
assert hasattr(checkin, 'qr_code') and checkin.qr_code, "QR code should be allocated on check-in"
qr_code = checkin.qr_code.code
print(f"✓ QR code allocated: {qr_code}")

# Test QR endpoint (public, no auth) - should work when checked in
client.logout()
response = client.get(f'/api/qr/{qr_code}/')
assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
data = response.json()
assert data['child']['first_name'] == 'Test', "QR endpoint should return child data"
assert 'current_session' in data, "Should include session info when checked in"
print(f"✓ QR endpoint working: {data['child']['first_name']} {data['child']['last_name']}")
print(f"  Session: {data['current_session']['name']}\n")

# Test 8: Invalid QR code
print("Test 8: Invalid QR code")
response = client.get('/api/qr/ZZZZZ/')
assert response.status_code == 404, f"Expected 404, got {response.status_code}"
print("✓ Invalid QR code returns 404\n")

# Test 9: QR code after checkout (should be 404 - privacy first)
print("Test 9: QR code privacy after checkout")
client.force_login(admin)
response = client.post(f'/api/checkins/{checkin.id}/check_out/', {}, content_type='application/json')
assert response.status_code == 200, f"Checkout failed: {response.content}"

client.logout()
response = client.get(f'/api/qr/{qr_code}/')
assert response.status_code == 404, f"Expected 404 after checkout, got {response.status_code}"
print("✓ QR code returns 404 after checkout (privacy working)\n")

print("=" * 50)
print("✅ All API tests passed!")
print("=" * 50)
print()
print("Privacy-first QR codes:")
print("  - QR codes only work when child is actively checked in")
print("  - After checkout, QR code returns 404 for privacy")
print()
