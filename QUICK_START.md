# Quick Start Guide - Backend Verification

## TL;DR - What You Need to Do

To verify the backend is working, follow these 4 simple steps:

### Step 1: Start the Services
```bash
cd /workspace/check-ins
docker-compose up -d
```

Wait ~30 seconds for services to start. Check status:
```bash
docker-compose ps
```

All services should show "Up" or "Up (healthy)".

---

### Step 2: Run Database Migrations
```bash
docker-compose exec web uv run python manage.py migrate
```

Expected output: You should see "Applying accounts.0001_initial... OK" and similar messages.

---

### Step 3: Create Admin User
```bash
docker-compose exec web uv run python manage.py createsuperuser
```

Enter:
- Username: `admin` (or whatever you prefer)
- Email: `admin@example.com`
- Password: (choose something, e.g., `admin123`)

---

### Step 4: Test the Backend

#### Option A: Quick Manual Test
1. Open browser: http://localhost:8000/admin
2. Login with the credentials you just created
3. Click around - you should see:
   - Accounts → Admin Users
   - Families → Families, Parents, Children
   - Events → Events, Sessions, Tickets
   - Check-ins → Check In Records, Audit Logs

If you see all these, **the backend is working!** ✅

#### Option B: Automated API Tests
Run the comprehensive test script:
```bash
cd /workspace/check-ins/backend
./test_api.sh
```

This will:
- Test authentication
- Create test family, parent, child
- Create test event and session
- Test check-in/check-out flow
- Verify QR token generation
- Check audit logging
- Validate all business logic

---

## Optional: Seed Sample Data

To get some test data to play with:
```bash
docker-compose exec web uv run python manage.py seed_sample_data
```

This creates:
- 5 families with parents and children
- 2 events with multiple sessions
- Some sample check-ins

---

## What to Tell Me After

Once you've completed the steps above, please share:

1. **Did the services start successfully?**
   - Share output of `docker-compose ps`

2. **Did migrations run?**
   - Any errors?

3. **Can you access Django admin?**
   - Screenshot would be helpful!

4. **If you ran the test script:**
   - Share the output (especially any red ✗ errors)

5. **Any error messages:**
   - From Docker logs: `docker-compose logs web`
   - Or any other issues you encountered

---

## Common Issues

### Issue: Port 8000 already in use
```bash
# Find what's using port 8000
lsof -i :8000

# Kill the process or change the port in docker-compose.yml
```

### Issue: Database connection errors
```bash
# Check if PostgreSQL is running
docker-compose ps db

# Check database logs
docker-compose logs db
```

### Issue: Permission denied errors
```bash
# Make sure you're in the project directory
cd /workspace/check-ins

# Check Docker is running
docker --version
docker-compose --version
```

---

## What the Backend Currently Has

✅ **Complete Models:**
- AdminUser (custom user model)
- Family, Parent, Child (with QR tokens)
- Event, Session, Ticket
- CheckInRecord, AuditLog

✅ **Complete API Endpoints:**
- `/api/families/`, `/api/parents/`, `/api/children/`
- `/api/events/`, `/api/sessions/`, `/api/tickets/`
- `/api/checkins/` with check_in/check_out actions
- `/qr/<token>/` - Public QR lookup
- `/api/auth/` - Login/logout

✅ **Business Logic:**
- QR token generation on first check-in
- Validation: one child per session max
- Last participation date tracking
- Audit logging for all actions
- Staff attribution

✅ **Configuration:**
- PostgreSQL database
- Session-based authentication
- CORS for frontend (port 5173)
- Valkey/Redis for future WebSocket layer

❌ **Not Yet Implemented:**
- WebSocket consumers for real-time updates
- Printing service for QR labels
- Frontend UI (SvelteKit)

---

## Next Steps After Verification

Once we confirm the backend works:

1. **Build SvelteKit Frontend**
   - Check-in station UI
   - Check-out station UI
   - QR info pages
   - Admin dashboard

2. **Add Real-Time Layer**
   - Django Channels consumers
   - WebSocket connections
   - Live check-in updates

3. **Add Printing Service**
   - QR code generation
   - Label template
   - Printer integration

4. **Write Tests**
   - Django unit tests
   - API integration tests
   - Frontend E2E tests

---

## Questions?

If you hit any issues or have questions, please share:
- The exact error message
- What step you were on
- Output from `docker-compose logs web`
- Any relevant screenshots

I'm here to help! 🚀
