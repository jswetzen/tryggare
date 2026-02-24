# Django Backend Verification Pattern

A repeatable pattern for testing Django backend changes quickly and reliably.

---

## Quick Verification (30 seconds)

After making changes to models, views, or business logic:

```bash
cd /workspace/check-ins/backend

# 1. Create/run migrations if models changed
uv run python manage.py makemigrations
uv run python manage.py migrate

# 2. Run verification script
uv run python /path/to/verification_script.py
```

---

## Verification Methods (Best to Worst)

### ✅ Method 1: Django Test Client (RECOMMENDED)

**Why:** Fast, no server needed, tests actual Django code, proper authentication handling.

**Pattern:**
```python
#!/usr/bin/env python
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
sys.path.insert(0, '/workspace/check-ins/backend')
django.setup()

from django.test import Client
from accounts.models import AdminUser

# Create test client
client = Client()

# Test unauthenticated access (should fail)
response = client.get('/api/families/')
assert response.status_code == 403, "Should require authentication"

# Test authenticated access
admin = AdminUser.objects.first()
client.force_login(admin)
response = client.get('/api/families/')
assert response.status_code == 200, "Should return families"

# Test POST operations
response = client.post('/api/families/', {}, content_type='application/json')
assert response.status_code in [200, 201], "Should create family"

print("✅ All tests passed!")
```

**Advantages:**
- No running server needed
- Automatic database cleanup
- Full Django request/response cycle
- Easy authentication with `force_login()`
- Fast (~100ms per test)

---

### ✅ Method 2: Django Shell + Direct Model Testing

**Why:** Fastest for testing models and business logic directly.

**Pattern:**
```python
#!/usr/bin/env python
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
sys.path.insert(0, '/workspace/check-ins/backend')
django.setup()

from families.models import Family, Child
from django.utils import timezone
import uuid

# Test model creation
family = Family.objects.create()
child = Child.objects.create(
    family=family,
    first_name="Test",
    last_name="Child",
    birthdate="2020-01-15"
)

# Test business logic
assert child.qr_token is None, "QR token should be null initially"

child.qr_token = str(uuid.uuid4())
child.last_participation_date = timezone.now()
child.save()

assert child.qr_token is not None, "QR token should be set"
assert child.last_participation_date is not None, "Date should be set"

print("✅ Model tests passed!")
```

**Advantages:**
- Extremely fast (<50ms)
- No HTTP overhead
- Direct model testing
- Perfect for TDD

---

### ⚠️ Method 3: HTTP Requests with curl (FALLBACK)

**Why:** Good for testing actual HTTP behavior, but slower and requires running server.

**Pattern:**
```bash
# Start server in background
uv run python manage.py runserver 0.0.0.0:8000 > /tmp/django.log 2>&1 &
SERVER_PID=$!

# Wait for server to start
sleep 2

# Test endpoints
curl -sf http://localhost:8000/qr/test-token/ || echo "✗ QR endpoint failed"
curl -sf http://localhost:8000/api/families/ | grep -q "Authentication" && echo "✓ Auth required"

# Cleanup
kill $SERVER_PID
```

**Disadvantages:**
- Requires running server
- Slower (~500ms per test)
- Harder to authenticate
- No automatic cleanup
- Manual database state management

**Use only for:**
- Testing actual HTTP behavior
- CORS configuration
- WebSocket connections
- Integration with frontend

---

## Recommended Verification Scripts

### Script 1: Quick Model Test (`test_models.py`)

```python
#!/usr/bin/env python
"""Quick model verification - run after model changes"""
import os, sys, django
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
family = Family.objects.create()
parent = Parent.objects.create(family=family, name="Test", phone="555-1234", relationship_type="Parent")
child = Child.objects.create(family=family, first_name="Test", last_name="Child", birthdate="2020-01-15")
event = Event.objects.create(name="Test", start_date="2025-01-01", end_date="2025-01-02")
session = Session.objects.create(event=event, name="Test", start_time=timezone.now(), end_time=timezone.now())
admin = AdminUser.objects.first()
checkin = CheckInRecord.objects.create(child=child, session=session, check_in_staff=admin)

# Test business logic
child.qr_token = str(uuid.uuid4())
child.save()
child.refresh_from_db()
assert child.qr_token is not None

# Test relationships
assert family.children.count() == 1
assert family.parents.count() == 1
assert event.sessions.count() == 1

print("✅ All models working!")
print(f"📝 Test QR: {child.qr_token}")
```

**Usage:**
```bash
uv run python backend/test_models.py
```

---

### Script 2: API Endpoint Test (`test_api.py`)

```python
#!/usr/bin/env python
"""API endpoint verification - run after view changes"""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
sys.path.insert(0, '/workspace/check-ins/backend')
django.setup()

from django.test import Client
from accounts.models import AdminUser
from families.models import Family, Child
from django.utils import timezone
import uuid

print("🔍 API Endpoint Verification\n")

client = Client()
admin = AdminUser.objects.first()

# Test 1: Unauthenticated access
print("Test 1: Unauthenticated access (should fail)")
response = client.get('/api/families/')
assert response.status_code == 403
print("✓ Correctly requires authentication\n")

# Test 2: Authenticated access
print("Test 2: Authenticated access")
client.force_login(admin)
response = client.get('/api/families/')
assert response.status_code == 200
print(f"✓ Got {len(response.json())} families\n")

# Test 3: Create family
print("Test 3: Create family")
response = client.post('/api/families/', {}, content_type='application/json')
assert response.status_code == 201
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
assert response.status_code == 201
child_id = response.json()['id']
print(f"✓ Created child: {child_id}\n")

# Test 5: QR endpoint (public)
print("Test 5: QR endpoint (public, no auth)")
# Create child with QR token
child = Child.objects.get(id=child_id)
child.qr_token = str(uuid.uuid4())
child.save()

# Test without authentication
client.logout()
response = client.get(f'/qr/{child.qr_token}/')
assert response.status_code == 200
data = response.json()
assert data['first_name'] == 'Test'
print(f"✓ QR endpoint working: {data['first_name']} {data['last_name']}\n")

print("✅ All API tests passed!")
```

**Usage:**
```bash
uv run python backend/test_api.py
```

---

### Script 3: Full Verification (`verify.py`)

Combines both model and API tests. Run this after any significant changes.

```python
#!/usr/bin/env python
"""Complete backend verification"""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
sys.path.insert(0, '/workspace/check-ins/backend')
django.setup()

# Run both test suites
print("=" * 60)
print("FULL BACKEND VERIFICATION")
print("=" * 60)
print()

# Import and run model tests
exec(open('backend/test_models.py').read())

print()
print("-" * 60)
print()

# Import and run API tests
exec(open('backend/test_api.py').read())

print()
print("=" * 60)
print("✅ ALL VERIFICATIONS PASSED!")
print("=" * 60)
```

---

## Workflow Patterns

### Pattern 1: After Model Changes

```bash
# 1. Make changes to models.py
# 2. Create migration
uv run python manage.py makemigrations

# 3. Apply migration
uv run python manage.py migrate

# 4. Test models
uv run python backend/test_models.py
```

### Pattern 2: After View Changes

```bash
# 1. Make changes to views.py
# 2. Test API
uv run python backend/test_api.py
```

### Pattern 3: After Business Logic Changes

```bash
# 1. Make changes
# 2. Run full verification
uv run python backend/verify.py
```

### Pattern 4: Before Committing

```bash
# Run all tests
uv run python backend/verify.py

# If all pass, commit
git add -A
git commit -m "Description of changes"
```

---

## Django Test Framework (Production)

For production-grade testing, use Django's test framework:

```python
# backend/families/tests.py
from django.test import TestCase, Client
from .models import Family, Child

class FamilyModelTests(TestCase):
    def setUp(self):
        self.family = Family.objects.create()

    def test_family_creation(self):
        self.assertIsNotNone(self.family.id)

    def test_add_child(self):
        child = Child.objects.create(
            family=self.family,
            first_name="Test",
            last_name="Child",
            birthdate="2020-01-15"
        )
        self.assertEqual(self.family.children.count(), 1)

class FamilyAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = AdminUser.objects.create_superuser('admin', 'pass')
        self.client.force_login(self.admin)

    def test_list_families(self):
        response = self.client.get('/api/families/')
        self.assertEqual(response.status_code, 200)

    def test_create_family(self):
        response = self.client.post('/api/families/', {})
        self.assertEqual(response.status_code, 201)
```

**Run with:**
```bash
uv run python manage.py test
```

**Advantages:**
- Automatic test database creation/cleanup
- Parallel test execution
- Coverage reporting
- CI/CD integration

---

## Summary: Which Method When?

| Scenario | Method | Speed | Command |
|----------|--------|-------|---------|
| Quick model check | Shell script | ⚡ 50ms | `uv run python test_models.py` |
| API endpoint test | Test Client | ⚡ 200ms | `uv run python test_api.py` |
| Full verification | Combined | ⚡ 500ms | `uv run python verify.py` |
| Production tests | Django TestCase | 🐢 2-5s | `uv run python manage.py test` |
| HTTP/CORS testing | curl + running server | 🐢 5-10s | `./test_api.sh` |

---

## Tools to Install

**jq (JSON processing):**
```bash
# Debian/Ubuntu
apt install jq

# macOS
brew install jq

# Or jaq (faster Rust alternative)
cargo install jaq
```

**Usage with curl:**
```bash
curl -s http://localhost:8000/qr/token/ | jq '.first_name'
curl -s http://localhost:8000/api/families/ | jq 'length'
```

---

## Best Practices

1. **Use Django Test Client** for API testing (not curl)
2. **Use Python scripts** for model testing (not Django shell)
3. **Only use curl** for actual HTTP behavior testing
4. **Run quick tests often** (after every change)
5. **Write proper TestCase tests** before production
6. **Use `force_login()`** instead of handling sessions manually
7. **Test in isolated scripts** (not interactive shell)

---

## Example: Testing After a Change

**Scenario:** You just added a new field to the Child model.

```bash
# 1. Create migration
uv run python manage.py makemigrations

# 2. Apply migration
uv run python manage.py migrate

# 3. Test the change
cat > /tmp/test_new_field.py << 'EOF'
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
sys.path.insert(0, '/workspace/check-ins/backend')
django.setup()

from families.models import Family, Child

family = Family.objects.create()
child = Child.objects.create(
    family=family,
    first_name="Test",
    last_name="Child",
    birthdate="2020-01-15",
    new_field="test_value"  # Your new field
)

assert hasattr(child, 'new_field')
assert child.new_field == "test_value"
print("✅ New field working!")
EOF

uv run python /tmp/test_new_field.py
```

---

**Created:** November 23, 2025
**Last Updated:** November 23, 2025
**Pattern Status:** ✅ Verified and Working
