#!/usr/bin/env python
"""
Test authentication endpoints
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from django.test import Client
from accounts.models import AdminUser


def test_auth_endpoints():
    """Test the authentication API endpoints"""
    print("🔐 Testing Authentication Endpoints\n")
    print("=" * 60)

    # Create test client
    client = Client()

    # Create a test user
    print("\n1. Creating test user...")
    AdminUser.objects.filter(username="testuser").delete()
    user = AdminUser.objects.create_user(
        username="testuser",
        password="testpass123",
        name="Test User"
    )
    print("   ✓ Test user created")

    # Test CSRF token endpoint
    print("\n2. Testing CSRF token endpoint...")
    response = client.get("/api/csrf/")
    assert response.status_code == 200
    csrf_token = response.json().get("csrfToken")
    assert csrf_token is not None
    print(f"   ✓ CSRF token received: {csrf_token[:20]}...")

    # Test auth check (unauthenticated)
    print("\n3. Testing auth check (not logged in)...")
    response = client.get("/api/auth/check/")
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is False
    assert data["user"] is None
    print("   ✓ Correctly returns not authenticated")

    # Test login with invalid credentials
    print("\n4. Testing login with invalid credentials...")
    response = client.post(
        "/api/auth/login/",
        {"username": "testuser", "password": "wrongpass"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token
    )
    assert response.status_code == 401
    assert "error" in response.json()
    print("   ✓ Correctly rejects invalid credentials")

    # Test login with valid credentials
    print("\n5. Testing login with valid credentials...")
    response = client.post(
        "/api/auth/login/",
        {"username": "testuser", "password": "testpass123"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["user"]["username"] == "testuser"
    assert data["user"]["name"] == "Test User"
    print("   ✓ Login successful")
    print(f"   User: {data['user']['username']} ({data['user']['name']})")

    # Test auth check (authenticated)
    print("\n6. Testing auth check (logged in)...")
    response = client.get("/api/auth/check/")
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is True
    assert data["user"]["username"] == "testuser"
    print("   ✓ Correctly returns authenticated user")

    # Test logout
    print("\n7. Testing logout...")
    # Get fresh CSRF token
    response = client.get("/api/csrf/")
    csrf_token = response.json().get("csrfToken")

    response = client.post(
        "/api/auth/logout/",
        HTTP_X_CSRFTOKEN=csrf_token
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
    print("   ✓ Logout successful")

    # Test auth check (after logout)
    print("\n8. Testing auth check (after logout)...")
    response = client.get("/api/auth/check/")
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is False
    assert data["user"] is None
    print("   ✓ Correctly returns not authenticated")

    # Clean up
    user.delete()

    print("\n" + "=" * 60)
    print("✅ All authentication tests passed!\n")


if __name__ == "__main__":
    try:
        test_auth_endpoints()
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
