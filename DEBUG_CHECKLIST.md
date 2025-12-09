# Debug Checklist - Login and Menu Display Issue

## Current Situation
- ✅ Login succeeds (can login at Django admin)
- ✅ Redirect to `/checkin` happens after login
- ✅ Can access `/checkin` after logging in at Django admin
- ❌ Top navigation menu doesn't show after frontend login
- ❌ Can't access `/checkout` after frontend login

## Debug Logging Added

### Frontend Container Logs
Look for these debug messages in the frontend logs:

**1. During Login Action (`login/+page.server.ts`):**
```
Login successful, processing cookies...
All response headers: [...]
All cookies to set: [...]
Processing cookie: csrftoken=...
Setting cookie: csrftoken = ...
Cookie options: { path: '/', httpOnly: false, ... }
Processing cookie: sessionid=...
Setting cookie: sessionid = ...
Cookie options: { path: '/', httpOnly: false, ... }
About to redirect to /checkin
```

**2. During Page Load (`hooks.server.ts`):**
```
Auth check result for /checkin : { authenticated: true/false, user: {...} }
Cookies sent to Django: csrftoken=...; sessionid=...
User authenticated: { id: '...', username: '...', name: '...' }
```

**3. During Layout Load (`+layout.server.ts`):**
```
Layout server load, locals.user: { id: '...', username: '...', name: '...' }
```

### Browser Console Logs
Look for these in the browser console (F12):

**1. During Login Form Submission:**
```
Form submitting...
Form result: { type: 'redirect', location: '/checkin', ... }
Redirecting to: /checkin
```

**2. During Page Render:**
```
Layout data: { user: {...} }
User: { id: '...', username: '...', name: '...' }
```

## What to Check

### Step 1: Login and Cookie Setting
After clicking "Login" button, check frontend logs for:
- [ ] "Login successful, processing cookies..." appears
- [ ] Both `csrftoken` and `sessionid` cookies are being set
- [ ] "About to redirect to /checkin" appears

**Expected:** You should see BOTH cookies being set with `path: '/'`

### Step 2: Redirect Handling
Check browser console for:
- [ ] "Form submitting..." appears
- [ ] "Form result: redirect" appears
- [ ] "Redirecting to: /checkin" appears

**Expected:** All three messages should appear

### Step 3: Auth Check on New Page
When `/checkin` loads, check frontend logs for:
- [ ] "Auth check result for /checkin" shows `authenticated: true`
- [ ] "Cookies sent to Django" shows both csrftoken and sessionid
- [ ] "User authenticated" shows the user object

**Expected:** Django should receive the cookies and return authenticated=true

### Step 4: Layout Data
Check browser console when page renders:
- [ ] "Layout data" shows the user object
- [ ] "User" shows the full user details

**Expected:** User data should be present

## Common Issues and Fixes

### Issue 1: Cookies Not Being Set
**Symptoms:**
- Login succeeds but "All cookies to set" is empty
- Or only csrftoken but no sessionid

**Fix:** Django isn't returning session cookie. Check Django `/api/auth/login/` response.

### Issue 2: Cookies Not Being Sent
**Symptoms:**
- Cookies are set during login
- But "Cookies sent to Django" is empty or missing sessionid

**Fix:** Cookies not being passed from browser to SvelteKit server. Check cookie options (path, sameSite, secure).

### Issue 3: Django Not Recognizing Session
**Symptoms:**
- Cookies are sent to Django
- But "authenticated: false" returned

**Fix:** Session not valid in Django. Check Django session storage and cookie matching.

### Issue 4: Layout Not Receiving User
**Symptoms:**
- "User authenticated" shows user in hooks
- But "Layout server load, locals.user" shows null

**Fix:** User not being passed from hooks to layout. Check `event.locals.user` assignment.

### Issue 5: Browser Not Receiving User
**Symptoms:**
- "Layout server load" shows user
- But browser console shows "User: null"

**Fix:** Data not being serialized/passed to browser. Check `+layout.server.ts` return value.

## Next Steps

1. **Login and check logs** - Note which step above shows unexpected output
2. **Share the logs** - Copy relevant log lines from both frontend container and browser console
3. **Identify the break point** - Which step fails or shows unexpected data?

## Quick Test Commands

After making changes, restart the app:
```bash
date > /workspace/check-ins/restart.txt
```

Check if cookies are being set in browser:
- Open DevTools → Application → Cookies → http://localhost:5173
- Should see: `csrftoken` and `sessionid`

Check if Django recognizes session:
- After login, access: http://localhost:8000/api/auth/check/
- Should return: `{"authenticated": true, "user": {...}}`
