# Authentication Session Persistence Fix

## Problem
After successful login, the session wasn't persisting when navigating to other pages. Users would be redirected back to the login page.

## Root Cause
The issue was that login was being handled **client-side** in the browser, but SvelteKit's server-side hooks couldn't access the session cookie set by the client-side fetch request. This is a fundamental limitation of how cookies work in SvelteKit:

1. Client-side `fetch()` in browser → Sets cookie in browser
2. Browser navigates to new page → Server-side hook runs in Node.js
3. Server-side hook makes request to Django → **Cookie not included** (different context)

## Solution
Changed login to be **server-side** using SvelteKit form actions:

### Changes Made

#### 1. Created Server-Side Login Action (`/routes/login/+page.server.ts`)
- Handles login on the server
- Forwards cookies from Django to the browser via SvelteKit's `cookies.set()`
- Properly chains CSRF token → Login request with same session
- Redirects to `/checkin` after successful login

Key improvements:
```typescript
// Get CSRF token and track its cookies
const csrfResponse = await fetch(`${API_BASE_URL}/api/csrf/`);
const djangoCookies = [...]; // Extract Set-Cookie headers

// Use those cookies in login request
const loginResponse = await fetch(`${API_BASE_URL}/api/auth/login/`, {
  headers: {
    'Cookie': cookieHeader, // Forward CSRF cookies
    'X-CSRFToken': csrfToken,
  },
});

// Set Django's session cookie in browser via SvelteKit
cookies.set(cookieName, cookieValue, options);
```

#### 2. Updated Login Page (`/routes/login/+page.svelte`)
- Removed client-side JavaScript login logic
- Changed to use standard HTML form with `method="POST"`
- Uses SvelteKit's `use:enhance` for progressive enhancement
- Displays server-side validation errors via `form?.error`

Before (client-side):
```typescript
async function handleSubmit(e: Event) {
  const result = await authStore.login(username, password);
  if (result.success) goto('/');
}
```

After (server-side):
```html
<form method="POST" use:enhance>
  <input name="username" required />
  <input name="password" required />
  <button type="submit">Login</button>
</form>
```

## How It Works Now

### Login Flow
1. User submits login form
2. **Server-side** action receives form data
3. Server fetches CSRF token from Django
4. Server sends login request to Django with CSRF token
5. Server receives session cookie from Django
6. Server forwards session cookie to browser via `cookies.set()`
7. Browser receives cookie and redirects to `/checkin`

### Subsequent Requests
1. Browser makes request to `/checkin`
2. **Server-side** hook runs with cookie from browser
3. Hook forwards cookie to Django's `/api/auth/check/`
4. Django validates session
5. Hook stores user in `event.locals.user`
6. Page loads with authenticated user data

## Key Points

### Cookie Flow
- Django sets `sessionid` cookie
- SvelteKit server proxies it to browser
- Browser sends cookie on all requests
- SvelteKit server forwards to Django
- Session persists across pages

### Why Server-Side?
Server-side login is necessary because:
1. SvelteKit's `cookies` API only works server-side
2. Need to proxy Django's cookies through SvelteKit
3. Ensures cookies are available to server-side hooks
4. More secure (credentials never in client JS)

### Form Actions Benefits
- Progressive enhancement (works without JavaScript)
- Built-in CSRF protection
- Automatic form data parsing
- Server-side validation
- Clean redirect handling

## Testing

Try the login flow now:
1. Navigate to http://localhost:5173
2. Should redirect to `/login`
3. Enter credentials and submit
4. Should redirect to `/checkin` (not `/`)
5. Navigate to any other page (e.g., `/checkout`)
6. Should **stay logged in** (no redirect to login)
7. Click logout
8. Should redirect to `/login` and lose session

## Files Modified

- ✅ `frontend/src/routes/login/+page.server.ts` - Created (server-side action)
- ✅ `frontend/src/routes/login/+page.svelte` - Changed to form-based login
- ✅ `frontend/src/hooks.server.ts` - Already correct (no changes needed)

## Notes

- The auth store (`lib/stores/auth.ts`) is still available for client-side auth checks if needed
- The server-side hook (`hooks.server.ts`) handles all authentication verification
- QR pages (`/qr/*`) remain publicly accessible
- Session cookies are httpOnly=false so SvelteKit can read and forward them
