# SvelteKit + Django Authentication Implementation Plan

## Implementation Status: ✅ COMPLETE

See `AUTH_IMPLEMENTATION.md` in the project root for detailed implementation summary and `TESTING_AUTH.md` for testing guide.

## Overview
Session-based authentication using Django's built-in auth system, shared between Django admin and SvelteKit frontend.

## Django Backend Changes

### 1. Configure CORS and Cookie Settings
**File: `settings.py`**

Add CORS middleware and configure for cross-origin requests:
- Enable `CORS_ALLOW_CREDENTIALS` to allow cookies
- Set `CORS_ALLOWED_ORIGINS` to include SvelteKit dev server (localhost:5173)
- Configure session and CSRF cookies for cross-origin use in development
- Set `SESSION_COOKIE_SAMESITE = 'Lax'` and `CSRF_COOKIE_SAMESITE = 'Lax'`
- Set `CSRF_COOKIE_HTTPONLY = False` so JavaScript can read CSRF token
- Keep `SECURE` flags as `False` in dev, `True` in production

### 2. Create Authentication API Endpoints
**File: `api/views.py`**

Create four endpoints:

**GET `/api/csrf/`**
- Returns CSRF token in JSON
- Used before any POST request

**GET `/api/auth/check/`**
- Returns authentication status and user data
- Used by SvelteKit to verify session validity
- Returns `{authenticated: bool, user: {id, username, email} | null}`

**POST `/api/auth/login/`**
- Accepts `{username, password}` JSON
- Uses Django's `authenticate()` and `login()` functions
- Returns success status and user data
- Sets session cookie automatically

**POST `/api/auth/logout/`**
- Calls Django's `logout()` function
- Clears session cookie

### 3. Add URL Routes
**File: `api/urls.py`**

Map the four endpoints to URL patterns under `/api/` prefix

## SvelteKit Frontend Changes

### 1. Create Auth Store
**File: `src/lib/stores/auth.js`**

Svelte writable store that manages authentication state:

**State:**
- `user`: null or user object `{id, username, email}`
- `loading`: boolean for initial auth check

**Methods:**
- `checkAuth()`: Fetches `/api/auth/check/` to verify session
- `login(username, password)`: Gets CSRF token, calls `/api/auth/login/`
- `logout()`: Gets CSRF token, calls `/api/auth/logout/`

All methods use `credentials: 'include'` to send cookies

### 2. Add Server-Side Authentication Hook
**File: `src/hooks.server.js`**

Runs on every server-side request:
- Calls Django `/api/auth/check/` endpoint
- Stores user in `event.locals.user`
- Redirects unauthenticated users to `/login` (except for public paths)
- Redirects authenticated users away from `/login` page

This ensures authentication check happens before any page loads

### 3. Create Root Layout
**File: `src/routes/+layout.server.js`**

Load function that passes user data to all pages:
- Returns `event.locals.user` from the hook
- Makes user data available to all child routes

**File: `src/routes/+layout.svelte`**

Root layout component:
- Displays user info and logout link when authenticated
- Wraps all pages with consistent navigation

### 4. Create Login Page
**File: `src/routes/login/+page.svelte`**

Login form component:
- Input fields for username and password
- Uses auth store's `login()` method
- Handles loading and error states
- Redirects to home page on successful login
- Form prevents default submission to handle via JavaScript

### 5. Create Logout Route
**File: `src/routes/logout/+page.server.js`**

Server-side logout handler:
- Calls auth store's `logout()` method
- Redirects to login page
- Handled server-side to ensure logout completes before redirect

## Authentication Flow

### Initial Page Load
1. User navigates to any SvelteKit page
2. `hooks.server.js` runs, calls Django `/api/auth/check/`
3. If not authenticated → redirect to `/login`
4. If authenticated → load page with user data

### Login Process
1. User submits login form
2. SvelteKit fetches CSRF token from `/api/csrf/`
3. Posts credentials to `/api/auth/login/` with CSRF token
4. Django validates, creates session, sends `sessionid` cookie
5. SvelteKit updates auth store with user data
6. Redirects to home page

### Authenticated Requests
All API calls from SvelteKit must:
- Include `credentials: 'include'` to send session cookie
- Include `X-CSRFToken` header for POST/PUT/DELETE requests
- Use the same origin or be CORS-approved

### Logout Process
1. User clicks logout link
2. SvelteKit fetches CSRF token
3. Posts to `/api/auth/logout/` with CSRF token
4. Django clears session
5. Redirects to login page

## Development vs Production Differences

### Development (separate ports)
- Django: `localhost:8000`
- SvelteKit: `localhost:5173`
- CORS enabled for cross-origin
- Cookie `Secure` flags set to `False`

### Production (same port)
- Django serves built SvelteKit app
- No CORS needed (same origin)
- Cookie `Secure` flags set to `True` (HTTPS only)
- Update `SESSION_COOKIE_SAMESITE = 'Strict'`

## Key Implementation Notes

1. **Always use `credentials: 'include'`** in all fetch calls to Django
2. **CSRF token required** for all POST/PUT/DELETE requests
3. **Server-side auth check** in hooks ensures protection before page renders
4. **Same user database** - Django admin users can log into Svelte app
5. **Session-based** - no tokens to manage, Django handles everything
6. **Automatic cookie handling** - browsers send `sessionid` cookie automatically
