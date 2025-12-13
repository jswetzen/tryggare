#!/usr/bin/env python
"""
Quick test script to verify rate limiting is working.
Tests the login endpoint rate limiting.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from django.test import Client
from accounts.models import AdminUser

def test_rate_limiting():
    """Test login rate limiting"""
    print("=" * 60)
    print("Testing Login Rate Limiting")
    print("=" * 60)

    # Create test user
    print("\n1. Creating test user...")
    AdminUser.objects.filter(username='ratelimit_test').delete()
    user = AdminUser.objects.create_user(
        username='ratelimit_test',
        password='testpass123',
        name='Rate Limit Test'
    )
    print(f"   ✓ Created user: {user.username}")

    # Create client
    client = Client()
    login_url = '/api/accounts/login/'

    # Test 1: Successful login (should work)
    print("\n2. Testing successful login...")
    response = client.post(
        login_url,
        {'username': 'ratelimit_test', 'password': 'testpass123'},
        content_type='application/json'
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print("   ✓ Login succeeded (expected)")
    else:
        print(f"   ✗ Login failed (unexpected): {response.json()}")

    # Test 2: Failed login attempts (should be rate limited after 5)
    print("\n3. Testing rate limiting with failed logins...")
    client.logout()  # Logout first

    for i in range(1, 8):
        response = client.post(
            login_url,
            {'username': 'ratelimit_test', 'password': 'wrongpassword'},
            content_type='application/json'
        )

        if response.status_code == 429:
            print(f"   Attempt {i}: Status {response.status_code} - RATE LIMITED ✓")
            print(f"   Rate limit kicked in after {i-1} attempts")
            break
        elif response.status_code == 401:
            print(f"   Attempt {i}: Status {response.status_code} - Unauthorized (expected)")
        else:
            print(f"   Attempt {i}: Status {response.status_code} - {response.json()}")

    # Cleanup
    print("\n4. Cleaning up...")
    user.delete()
    print("   ✓ Test user deleted")

    print("\n" + "=" * 60)
    print("Rate Limiting Test Complete!")
    print("=" * 60)

if __name__ == '__main__':
    test_rate_limiting()
