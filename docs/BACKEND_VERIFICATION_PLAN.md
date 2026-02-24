# Backend Verification Plan

## Overview
This document outlines the verification steps needed to confirm the Django REST API backend is working correctly.

## Current Status
- ✅ Django models defined and migrations created
- ✅ REST API endpoints implemented
- ✅ Business logic for check-ins/check-outs implemented
- ✅ Django admin configured
- ✅ Docker configuration ready
- ❌ Services not yet started
- ❌ Database not yet initialized
- ❌ No superuser created
- ❌ API endpoints not yet tested

---

## Prerequisites

### 1. Start Docker Services
```bash
cd /workspace/check-ins
docker-compose up -d
```

Services that should start:
- `web` - Django backend (port 8000)
- `db` - PostgreSQL database (port 5432)
- `valkey` - Redis-compatible message broker (port 6379)
- `frontend` - SvelteKit dev server (port 5173)

### 2. Run Django Migrations
```bash
# Option 1: From host (if you have Python/uv installed)
cd backend
uv sync
uv run python manage.py migrate

# Option 2: Inside Docker container
docker-compose exec web uv run python manage.py migrate
```

Expected output:
```
Operations to perform:
  Apply all migrations: accounts, admin, auth, checkins, contenttypes, events, families, printing, sessions
Running migrations:
  Applying accounts.0001_initial... OK
  Applying families.0001_initial... OK
  Applying events.0001_initial... OK
  Applying checkins.0001_initial... OK
  ...
```

### 3. Create Superuser
```bash
# Option 1: Interactive
docker-compose exec web uv run python manage.py createsuperuser

# Option 2: Non-interactive
docker-compose exec web uv run python manage.py createsuperuser \
  --username admin \
  --email admin@example.com \
  --noinput
```

### 4. (Optional) Seed Sample Data
```bash
docker-compose exec web uv run python manage.py seed_sample_data
```

---

## Verification Tests

### Test 1: Service Health Check

**Goal:** Verify all Docker services are running

```bash
docker-compose ps
```

**Expected Result:**
```
NAME                STATUS              PORTS
check-ins-web-1     Up (healthy)       0.0.0.0:8000->8000/tcp
check-ins-db-1      Up (healthy)       0.0.0.0:5432->5432/tcp
check-ins-valkey-1  Up (healthy)       0.0.0.0:6379->6379/tcp
check-ins-frontend-1 Up                0.0.0.0:5173->5173/tcp
```

**Troubleshooting:**
- If `web` is unhealthy: Check logs with `docker-compose logs web`
- If `db` is unhealthy: Check PostgreSQL logs with `docker-compose logs db`

---

### Test 2: Django Admin Interface

**Goal:** Verify Django is running and admin interface is accessible

1. Open browser: http://localhost:8000/admin
2. Login with superuser credentials
3. Verify all models are visible:
   - Accounts: Admin Users
   - Families: Families, Parents, Children
   - Events: Events, Sessions, Tickets
   - Check-ins: Check In Records, Audit Logs

**Expected Result:**
- Login successful
- All models listed in admin
- Can view model list pages

**Test CRUD Operations:**
- Create a new Family
- Add Parents to the family
- Add Children to the family
- View the created records

---

### Test 3: REST API - Authentication

**Goal:** Verify REST API authentication is working

#### 3.1 Test Unauthenticated Access (Should Fail)
```bash
curl -i http://localhost:8000/api/families/
```

**Expected Result:**
```
HTTP/1.1 403 Forbidden
Content-Type: application/json

{"detail":"Authentication credentials were not provided."}
```

#### 3.2 Test Login
```bash
# Get CSRF token
curl -c cookies.txt http://localhost:8000/admin/login/

# Extract CSRF token from cookies
CSRF_TOKEN=$(grep csrftoken cookies.txt | awk '{print $7}')

# Login
curl -i -b cookies.txt -c cookies.txt \
  -X POST http://localhost:8000/api/auth/login/ \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-password"}'
```

**Expected Result:**
```
HTTP/1.1 200 OK
Set-Cookie: sessionid=...
```

#### 3.3 Test Authenticated Access
```bash
curl -b cookies.txt http://localhost:8000/api/families/
```

**Expected Result:**
```json
HTTP/1.1 200 OK
Content-Type: application/json

[]  // or list of families if any exist
```

---

### Test 4: REST API - Family Management

**Goal:** Test CRUD operations for families, parents, and children

#### 4.1 Create Family
```bash
curl -b cookies.txt -c cookies.txt \
  -X POST http://localhost:8000/api/families/ \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "notes": "Test family"
  }'
```

**Expected Result:**
```json
{
  "id": "uuid-here",
  "notes": "Test family",
  "last_participation_date": null,
  "created_at": "2025-11-23T...",
  "updated_at": "2025-11-23T..."
}
```

Save the family ID for next steps.

#### 4.2 Create Parent
```bash
FAMILY_ID="uuid-from-above"

curl -b cookies.txt -c cookies.txt \
  -X POST http://localhost:8000/api/parents/ \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "family": "'$FAMILY_ID'",
    "name": "John Doe",
    "phone_number": "555-1234",
    "email": "john@example.com",
    "relationship": "Dad"
  }'
```

#### 4.3 Create Child
```bash
curl -b cookies.txt -c cookies.txt \
  -X POST http://localhost:8000/api/children/ \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "family": "'$FAMILY_ID'",
    "first_name": "Jane",
    "last_name": "Doe",
    "birthdate": "2020-01-15",
    "allergies": "None",
    "notes": "Test child"
  }'
```

Save the child ID for check-in tests.

---

### Test 5: REST API - Event/Session Management

#### 5.1 Create Event
```bash
curl -b cookies.txt -c cookies.txt \
  -X POST http://localhost:8000/api/events/ \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Conference",
    "start_date": "2025-11-23",
    "end_date": "2025-11-24",
    "is_multi_day": true
  }'
```

Save the event ID.

#### 5.2 Create Session
```bash
EVENT_ID="uuid-from-above"

curl -b cookies.txt -c cookies.txt \
  -X POST http://localhost:8000/api/sessions/ \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "'$EVENT_ID'",
    "name": "Morning Session",
    "start_time": "2025-11-23T09:00:00Z",
    "end_time": "2025-11-23T12:00:00Z",
    "requires_ticket": false
  }'
```

Save the session ID for check-in tests.

---

### Test 6: REST API - Check-In/Check-Out Logic

**Goal:** Test the core business logic

#### 6.1 Check In Child
```bash
CHILD_ID="uuid-from-above"
SESSION_ID="uuid-from-above"

curl -b cookies.txt -c cookies.txt \
  -X POST http://localhost:8000/api/checkins/check_in/ \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "child": "'$CHILD_ID'",
    "session": "'$SESSION_ID'"
  }'
```

**Expected Result:**
```json
{
  "id": "uuid-here",
  "child": "child-uuid",
  "session": "session-uuid",
  "check_in_time": "2025-11-23T...",
  "check_out_time": null,
  "check_in_staff": "admin-uuid",
  "check_out_staff": null,
  "picked_up_by": ""
}
```

**Verify Side Effects:**
1. Child should now have a `qr_token` (check with `GET /api/children/{id}/`)
2. Child's `last_participation_date` should be updated
3. Family's `last_participation_date` should be updated
4. An audit log entry should be created

#### 6.2 Verify QR Token Generated
```bash
curl -b cookies.txt http://localhost:8000/api/children/$CHILD_ID/
```

**Expected Result:**
```json
{
  "id": "...",
  "qr_token": "uuid-here",  // Should NOT be null now
  ...
}
```

Save the QR token for the next test.

#### 6.3 Test Double Check-In Prevention
```bash
# Try to check in same child again
curl -b cookies.txt -c cookies.txt \
  -X POST http://localhost:8000/api/checkins/check_in/ \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "child": "'$CHILD_ID'",
    "session": "'$SESSION_ID'"
  }'
```

**Expected Result:**
```
HTTP/1.1 400 Bad Request

{"error": "Child is already checked in to this session"}
```

#### 6.4 Get Active Check-Ins
```bash
curl -b cookies.txt http://localhost:8000/api/checkins/active/
```

**Expected Result:**
```json
[
  {
    "id": "...",
    "child": "...",
    "session": "...",
    "check_in_time": "...",
    "check_out_time": null,
    ...
  }
]
```

#### 6.5 Check Out Child
```bash
CHECKIN_ID="uuid-from-check-in-response"

curl -b cookies.txt -c cookies.txt \
  -X POST http://localhost:8000/api/checkins/$CHECKIN_ID/check_out/ \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "picked_up_by": "John Doe"
  }'
```

**Expected Result:**
```json
{
  "id": "...",
  "check_in_time": "...",
  "check_out_time": "2025-11-23T...",  // Should be populated now
  "check_out_staff": "admin-uuid",
  "picked_up_by": "John Doe"
}
```

---

### Test 7: Public QR Code Endpoint

**Goal:** Verify QR code lookup works without authentication

```bash
QR_TOKEN="uuid-from-child-record"

curl http://localhost:8000/qr/$QR_TOKEN/
```

**Expected Result:**
```json
{
  "id": "child-uuid",
  "first_name": "Jane",
  "last_name": "Doe",
  "birthdate": "2020-01-15",
  "allergies": "None",
  "notes": "Test child",
  "family_id": "family-uuid",
  "parent_names": ["John Doe"],
  "is_checked_in": false,  // or true if still checked in
  "current_session": null  // or session details if checked in
}
```

**Important:** This should work WITHOUT authentication (no cookies needed).

---

### Test 8: Audit Logs

**Goal:** Verify all actions are being logged

```bash
curl -b cookies.txt http://localhost:8000/api/audit-logs/
```

**Expected Result:**
```json
[
  {
    "id": "...",
    "user": "admin-uuid",
    "action": "check_out",
    "entity_type": "CheckInRecord",
    "entity_id": "...",
    "details": {
      "child_id": "...",
      "child_name": "Jane Doe",
      "session_id": "...",
      "session_name": "Morning Session",
      "picked_up_by": "John Doe"
    },
    "timestamp": "..."
  },
  {
    "id": "...",
    "user": "admin-uuid",
    "action": "check_in",
    ...
  }
]
```

---

### Test 9: CORS Configuration

**Goal:** Verify frontend can communicate with backend

```bash
# Test from browser console or using curl
curl -i http://localhost:8000/api/families/ \
  -H "Origin: http://localhost:5173"
```

**Expected Result:**
```
HTTP/1.1 403 Forbidden
Access-Control-Allow-Origin: http://localhost:5173
Access-Control-Allow-Credentials: true
```

The 403 is expected (no auth), but CORS headers should be present.

---

## Summary Checklist

Before considering the backend "verified and working", ensure:

- [ ] All Docker services are healthy
- [ ] Django migrations ran successfully
- [ ] Superuser created and can log into admin
- [ ] Can view all models in Django admin
- [ ] Can create/read/update/delete records via admin
- [ ] REST API requires authentication (403 without login)
- [ ] Can login via REST API and get session cookie
- [ ] Can create families, parents, and children via API
- [ ] Can create events and sessions via API
- [ ] Check-in creates QR token on first use
- [ ] Check-in updates last participation dates
- [ ] Check-in prevents duplicate check-ins
- [ ] Check-out records timestamp and staff member
- [ ] Active check-ins endpoint returns only checked-in children
- [ ] Public QR endpoint works WITHOUT authentication
- [ ] QR endpoint returns child details and check-in status
- [ ] Audit logs capture all check-in/check-out actions
- [ ] CORS headers allow frontend origin

---

## What I Still Need From You

To complete this verification, I need you to:

1. **Start the Docker services:**
   ```bash
   cd /workspace/check-ins
   docker-compose up -d
   ```

2. **Run the migrations:**
   ```bash
   docker-compose exec web uv run python manage.py migrate
   ```

3. **Create a superuser:**
   ```bash
   docker-compose exec web uv run python manage.py createsuperuser
   ```

4. **Then I can help you:**
   - Run the API tests (I can write scripts for this)
   - Test the endpoints using curl or a REST client
   - Verify the business logic is working
   - Check that CORS is configured correctly
   - Ensure audit logging is working

5. **Optional but helpful:**
   - Seed sample data: `docker-compose exec web uv run python manage.py seed_sample_data`
   - This will create test families, events, and sessions to experiment with

---

## Next Steps After Verification

Once the backend is verified:
1. ✅ Build the SvelteKit frontend
2. ✅ Implement WebSocket consumers for real-time updates
3. ✅ Add printing service for QR code labels
4. ✅ Write automated tests
5. ✅ Deploy to production environment
