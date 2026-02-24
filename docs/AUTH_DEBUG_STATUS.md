# Authentication Debug Status

## Changes Made (2025-11-24 19:54 UTC)

### Problem Identified
After frontend login, cookies were being set but the navigation menu wasn't appearing. Root causes identified:

1. **Cookie parsing issues**: Django's Set-Cookie headers weren't being correctly parsed
2. **Cookie reading method**: Using `event.request.headers.get('cookie')` instead of SvelteKit's proper `event.cookies.get()` API
3. **Cookie options**: Inconsistent handling of `httpOnly`, `sameSite`, and `path` options

### Fixes Applied

#### 1. Improved Cookie Parsing (`frontend/src/routes/login/+page.server.ts`)
- **Changed**: Refactored cookie parsing to use a Map to avoid duplicates
- **Changed**: Improved cookie option parsing to handle edge cases
- **Changed**: Explicitly set `sameSite: 'lax'` as default
- **Changed**: Better handling of the `httpOnly` flag (always set to `false` so SvelteKit can forward)
- **Changed**: Added detailed console logging for each cookie captured and set

**Key improvements**:
```typescript
const allCookies = new Map<string, { value: string; options: any }>();

const options: any = {
  path: '/',
  httpOnly: false,  // Must be false for cookie forwarding
  sameSite: 'lax',  // Important for security and functionality
};
```

#### 2. Fixed Cookie Reading Method (`frontend/src/hooks.server.ts`)
- **Changed**: Use SvelteKit's `event.cookies.get()` API instead of raw header parsing
- **Added**: Build cookie header manually from individual cookies
- **Added**: Debug logging to show which cookies are present/missing
- **Improved**: Cleaner and more reliable cookie forwarding to Django

**Why this matters**: SvelteKit's cookies API properly handles cookie parsing and is aware of cookies set by `cookies.set()` in server actions, while `event.request.headers.get('cookie')` only sees cookies that came from the browser in the current request.

```typescript
// OLD (unreliable):
const cookies = event.request.headers.get('cookie') || '';

// NEW (correct):
const csrftoken = event.cookies.get('csrftoken');
const sessionid = event.cookies.get('sessionid');
const cookieParts: string[] = [];
if (csrftoken) cookieParts.push(`csrftoken=${csrftoken}`);
if (sessionid) cookieParts.push(`sessionid=${sessionid}`);
const cookies = cookieParts.join('; ');
```

### What Should Happen Now

When you login at `http://localhost:5173/login`, the logs should show:

**Login Action (frontend.log)**:
```
Login successful, processing cookies...
Captured CSRF cookie: csrftoken
Captured login cookie: sessionid
All cookies to set: ['csrftoken', 'sessionid']
Setting cookie: csrftoken = ...
Cookie options: { path: '/', httpOnly: false, sameSite: 'lax' }
Setting cookie: sessionid = ...
Cookie options: { path: '/', httpOnly: false, sameSite: 'lax' }
About to redirect to /checkin
```

**Auth Check on Redirect (frontend.log)**:
```
Cookies from SvelteKit cookies API:
  csrftoken: present
  sessionid: present
Auth check result for /checkin : { authenticated: true, user: { ... } }
Cookie header sent to Django: csrftoken=...; sessionid=...
User authenticated: { id: '...', username: '...', name: '...' }
```

**Layout Load (frontend.log)**:
```
Layout server load, locals.user: { id: '...', username: '...', name: '...' }
```

**Browser Console**:
```
Layout data: { user: { ... } }
User: { id: '...', username: '...', name: '...' }
```

### Testing Steps

1. **Clear browser cookies** for localhost:5173
   - Open DevTools (F12)
   - Go to Application → Cookies → http://localhost:5173
   - Delete all cookies

2. **Navigate to login page**: http://localhost:5173/login

3. **Open two log windows**:
   ```bash
   # Terminal 1 - Frontend logs
   tail -f /workspace/check-ins/frontend.log

   # Terminal 2 - Backend logs (if available)
   tail -f /workspace/check-ins/web.log
   ```

4. **Submit login form** with valid credentials

5. **Check for success indicators**:
   - [ ] Redirects to `/checkin`
   - [ ] Navigation menu appears at top
   - [ ] Can navigate to `/checkout`
   - [ ] Frontend logs show "User authenticated"
   - [ ] Browser console shows user object

6. **Verify cookies in browser**:
   - Open DevTools → Application → Cookies → http://localhost:5173
   - Should see:
     - `csrftoken` cookie
     - `sessionid` cookie
   - Both should have:
     - Path: `/`
     - SameSite: `Lax`
     - HttpOnly: ☐ (unchecked)

### If It Still Doesn't Work

Check the logs to identify where it fails:

**Scenario A: No cookies captured**
```
All cookies to set: []
```
**Issue**: Django isn't returning Set-Cookie headers
**Fix**: Check Django's session configuration in backend/config/settings/base.py

**Scenario B: Cookies set but not accessible to hooks**
```
Cookies from SvelteKit cookies API:
  csrftoken: missing
  sessionid: missing
Auth check result for /checkin : { authenticated: false, ... }
Cookie header sent to Django: empty
```
**Issue**: Cookies were set in login action but aren't accessible via `event.cookies.get()`
**Fix**: This should be resolved by the current changes. If still happening:
  - Check that cookies.set() is being called in the login action
  - Verify cookie options include `path: '/'`
  - Check browser DevTools to confirm cookies were actually set

**Scenario C: Cookies sent but Django doesn't recognize session**
```
Cookies from SvelteKit cookies API:
  csrftoken: present
  sessionid: present
Cookie header sent to Django: csrftoken=...; sessionid=...
Auth check result: { authenticated: false }
```
**Issue**: Django doesn't recognize the session ID
**Fix**: Check Django session backend, verify session exists in database/cache

**Scenario D: User in locals but not in layout**
```
User authenticated: { ... }
Layout server load, locals.user: null
```
**Issue**: event.locals.user not being passed correctly
**Fix**: Verify hooks.server.ts is setting event.locals.user correctly

### Key Technical Insight

The crucial fix was changing from `event.request.headers.get('cookie')` to `event.cookies.get()`.

**Why this matters:**

When a SvelteKit server action (login) sets cookies using `cookies.set()`, those cookies are:
1. Queued to be sent to the browser in the response
2. **Immediately available** to subsequent SvelteKit server code via `event.cookies.get()`

However, `event.request.headers.get('cookie')` only returns cookies that came FROM the browser in the CURRENT request. It doesn't know about cookies that were just set in the same request cycle.

So the sequence was:
1. Login action sets cookies → **Cookies queued for browser**
2. Login action redirects to /checkin → **Still same response**
3. Hooks run for /checkin request → **Happens before browser gets the Set-Cookie headers**
4. `event.request.headers.get('cookie')` → **Empty! Browser hasn't received cookies yet**
5. Auth check fails, no user data
6. Browser finally receives response with Set-Cookie headers

By using `event.cookies.get()`, the hooks can access cookies that were set in the same request cycle, even before the browser has received them.

### Additional Notes

- The frontend dev server should auto-reload with the changes (Vite HMR)
- If changes aren't reflected, try manually restarting Docker containers
- The `httpOnly: false` setting is necessary for SvelteKit to forward cookies to Django
- This is secure because SvelteKit server-side code can access them, not client-side JS
- Django's original HttpOnly flag doesn't matter for server-to-server communication

### Comparison with Working Django Admin Login

When logging in at Django admin works but frontend doesn't, it suggests:
- Django's session system is working correctly
- The issue is in how SvelteKit handles the session cookies
- The improved cookie parsing should resolve this

The key difference:
- **Django admin**: Browser → Django (direct, cookies set by Django, stay with Django)
- **Frontend**: Browser → SvelteKit → Django (cookies must pass through SvelteKit)

Our fix ensures the cookie forwarding works correctly.
