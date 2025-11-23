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
from families.models import Family, Child
from django.utils import timezone
import uuid
import json

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
response = client.post('/api/families/', {}, content_type='application/json')
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
print(f"  QR token (should be null): {child_data.get('qr_token')}\n")

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

# Test 7: QR endpoint (public, no auth required)
print("Test 7: QR endpoint (public, no auth)")
# Create child with QR token
child = Child.objects.get(id=child_id)
child.qr_token = str(uuid.uuid4())
child.save()

# Test without authentication
client.logout()
response = client.get(f'/qr/{child.qr_token}/')
assert response.status_code == 200, f"Expected 200, got {response.status_code}"
data = response.json()
assert data['first_name'] == 'Test', "QR endpoint should return child data"
assert 'is_checked_in' in data, "Should include check-in status"
print(f"✓ QR endpoint working: {data['first_name']} {data['last_name']}")
print(f"  Checked in: {data['is_checked_in']}")
print(f"  Parent names: {data['parent_names']}\n")

# Test 8: Invalid QR token
print("Test 8: Invalid QR token")
response = client.get('/qr/invalid-token-12345/')
assert response.status_code == 404, f"Expected 404, got {response.status_code}"
print("✓ Invalid QR token returns 404\n")

# Test 9: Create event and session
print("Test 9: Create event and session")
client.force_login(admin)
response = client.post('/api/events/', {
    'name': 'Test Conference',
    'start_date': '2025-11-23',
    'end_date': '2025-11-24'
}, content_type='application/json')
assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.content}"
event_id = response.json()['id']
print(f"✓ Created event: {event_id}")

response = client.post('/api/sessions/', {
    'event': event_id,
    'name': 'Morning Session',
    'start_time': timezone.now().isoformat(),
    'end_time': (timezone.now() + timezone.timedelta(hours=3)).isoformat(),
    'requires_ticket': False
}, content_type='application/json')
assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.content}"
session_id = response.json()['id']
print(f"✓ Created session: {session_id}\n")

print("=" * 50)
print("✅ All API tests passed!")
print("=" * 50)
print()
print("Test URLs:")
print(f"  QR endpoint: http://localhost:8000/qr/{child.qr_token}/")
print(f"  Admin: http://localhost:8000/admin/")
print()
