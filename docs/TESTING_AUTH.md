# Testing Authentication - Quick Guide

## Quick Test Commands

### 1. Backend Authentication Tests
```bash
cd /workspace/check-ins/backend
uv run python test_auth.py
```

Expected output: All 8 authentication tests should pass ✅

### 2. Full Backend Verification
```bash
cd /workspace/check-ins/backend
uv run python verify.py
```

Expected output: All model and API tests should pass ✅

---

## Manual Testing with Running Servers

### Start the Backend (Terminal 1)
```bash
cd /workspace/check-ins/backend
uv run python manage.py runserver
```

### Start the Frontend (Terminal 2)
```bash
cd /workspace/check-ins/frontend
npm run dev
```

### Create a Test Admin User
```bash
cd /workspace/check-ins/backend
uv run python manage.py createsuperuser
```

Follow prompts:
- Username: `admin` (or your choice)
- Name: `Admin User`
- Password: (your choice, at least 8 characters)

---

## Testing the Login Flow

1. **Open Frontend**
   - Navigate to: http://localhost:5173
   - Should automatically redirect to: http://localhost:5173/login

2. **Test Login Page**
   - Enter username and password
   - Click "Login" button
   - Should redirect to home page on success
   - Should show error message on failure

3. **Verify Authenticated State**
   - After successful login, should see navigation bar with:
     - Welcome message with username
     - Check-In link
     - Check-Out link
     - Logout link

4. **Test Protected Routes**
   - Try to access: http://localhost:5173/checkin
   - Should load successfully (not redirect to login)
   - Navigation bar should be visible

5. **Test Logout**
   - Click "Logout" link in navigation
   - Should redirect to login page
   - Try accessing protected route again
   - Should redirect back to login

6. **Test Public QR Route**
   - While logged out, create a child with QR code via Django admin
   - Access: http://localhost:5173/qr/[token]
   - Should load without requiring login

---

## Testing API Endpoints Directly

### Get CSRF Token
```bash
curl -c cookies.txt http://localhost:8000/api/csrf/
```

### Check Auth Status (Unauthenticated)
```bash
curl -b cookies.txt http://localhost:8000/api/auth/check/
```

Expected response:
```json
{"authenticated": false, "user": null}
```

### Login
```bash
# Get CSRF token
CSRF_TOKEN=$(curl -s -c cookies.txt http://localhost:8000/api/csrf/ | jq -r .csrfToken)

# Login with credentials
curl -b cookies.txt -c cookies.txt \
  -X POST \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  -d '{"username":"admin","password":"yourpassword"}' \
  http://localhost:8000/api/auth/login/
```

Expected response:
```json
{
  "success": true,
  "user": {
    "id": "...",
    "username": "admin",
    "name": "Admin User"
  }
}
```

### Check Auth Status (Authenticated)
```bash
curl -b cookies.txt http://localhost:8000/api/auth/check/
```

Expected response:
```json
{
  "authenticated": true,
  "user": {
    "id": "...",
    "username": "admin",
    "name": "Admin User"
  }
}
```

### Logout
```bash
# Get fresh CSRF token
CSRF_TOKEN=$(curl -s -b cookies.txt http://localhost:8000/api/csrf/ | jq -r .csrfToken)

# Logout
curl -b cookies.txt \
  -X POST \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  http://localhost:8000/api/auth/logout/
```

Expected response:
```json
{"success": true}
```

---

## Common Issues and Solutions

### Issue: "CSRF verification failed"
**Solution**: Make sure to:
1. Get CSRF token before POST requests
2. Include `X-CSRFToken` header
3. Use same cookies for CSRF fetch and POST request

### Issue: "Unauthorized" error on protected endpoints
**Solution**:
1. Check that you're logged in (call `/api/auth/check/`)
2. Verify cookies are being sent (`credentials: 'include'`)
3. Check that session hasn't expired

### Issue: Frontend redirects to login immediately
**Solution**:
1. Check that both servers are running
2. Verify CORS settings in `backend/config/settings/local.py`
3. Check browser console for CORS errors
4. Ensure cookies are allowed in browser

### Issue: Login succeeds but still redirected to login page
**Solution**:
1. Check that session cookie is being set (check browser dev tools)
2. Verify `CORS_ALLOW_CREDENTIALS = True` in Django settings
3. Check that frontend is using `credentials: 'include'`

### Issue: "Cannot read properties of null (reading 'username')"
**Solution**:
1. Check that user object is being passed from layout to components
2. Verify `+layout.server.ts` is exporting user data
3. Check TypeScript types in `app.d.ts`

---

## Browser Testing Checklist

- [ ] Login with valid credentials succeeds
- [ ] Login with invalid credentials shows error
- [ ] Protected routes redirect to login when not authenticated
- [ ] Protected routes load normally when authenticated
- [ ] Navigation bar appears when authenticated
- [ ] Username displays correctly in navigation
- [ ] Logout link works and redirects to login
- [ ] After logout, protected routes redirect to login again
- [ ] QR code pages load without authentication
- [ ] Session persists across page refreshes
- [ ] Session expires after Django timeout (default: 2 weeks)

---

## Django Admin Testing

1. **Access Django Admin**
   - Navigate to: http://localhost:8000/admin/
   - Login with superuser credentials

2. **Verify Admin User Model**
   - Go to "Admin Users" section
   - Should see list of admin users
   - Create/edit users as needed

3. **Cross-Login Test**
   - Login via Django admin
   - Open SvelteKit frontend in same browser
   - Should be automatically logged in (same session)

---

## Next Steps After Testing

Once authentication is verified working:

1. Update check-in/check-out pages to use authenticated user for staff fields
2. Add user permissions and role-based access control if needed
3. Implement password change functionality
4. Add "Remember me" option if desired
5. Configure session timeout for production
6. Set up HTTPS and secure cookies for production deployment
