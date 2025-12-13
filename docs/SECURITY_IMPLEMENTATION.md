# Security Implementation Documentation

## Overview
This document describes the critical security fixes implemented in the Django backend to protect against common web vulnerabilities.

## Implementation Date
2025-12-13

## Changes Implemented

### 1. Rate Limiting on Login Endpoint

**Problem:** The login endpoint had no rate limiting, making it vulnerable to brute force attacks.

**Solution:** Implemented DRF throttling with custom rate limit for login attempts.

#### Files Modified
- `/workspace/check-ins/backend/config/settings/base.py`
- `/workspace/check-ins/backend/accounts/views.py`

#### Implementation Details

**Settings Configuration (`config/settings/base.py`):**
```python
REST_FRAMEWORK = {
    # ... existing config ...
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "10/minute",      # Anonymous users: 10 requests/min
        "user": "100/minute",     # Authenticated users: 100 requests/min
        "login": "5/minute",      # Login attempts: 5 attempts/min
    },
}
```

**Custom Throttle Class (`accounts/views.py`):**
```python
class LoginRateThrottle(AnonRateThrottle):
    """
    Rate throttle specifically for login attempts.
    Limits to 5 login attempts per minute per IP address.
    """
    rate = '5/minute'
```

**Applied to Login View:**
```python
@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
def login_view(request):
    # ... implementation
```

#### Behavior
- Anonymous users: Limited to 10 API requests per minute
- Authenticated users: Limited to 100 API requests per minute
- Login endpoint: Limited to 5 login attempts per minute per IP address
- When rate limit is exceeded, returns HTTP 429 (Too Many Requests)
- Rate limits reset automatically after the time window expires

#### Testing
Rate limiting can be tested with:
```bash
cd /workspace/check-ins/backend
uv run python manage.py test tests.test_security.RateLimitingTests
```

### 2. Security Headers Configuration

**Problem:** Production environment lacked critical security headers (HSTS, CSP, X-Frame-Options).

**Solution:** Added comprehensive security header configuration to production settings.

#### Files Modified
- `/workspace/check-ins/backend/config/settings/prod.py`

#### Implementation Details

**Headers Added:**

1. **HTTP Strict Transport Security (HSTS)**
   ```python
   SECURE_HSTS_SECONDS = 31536000  # 1 year
   SECURE_HSTS_INCLUDE_SUBDOMAINS = True
   SECURE_HSTS_PRELOAD = True
   ```
   - Forces browsers to use HTTPS for 1 year
   - Applies to all subdomains
   - Eligible for browser preload lists

2. **SSL/TLS Configuration**
   ```python
   SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "false").lower() == "true"
   ```
   - Redirects HTTP to HTTPS (disabled by default, enable via env var)

3. **Clickjacking Protection**
   ```python
   X_FRAME_OPTIONS = "DENY"
   ```
   - Prevents the site from being embedded in iframes

4. **MIME-Type Sniffing Protection**
   ```python
   SECURE_CONTENT_TYPE_NOSNIFF = True
   ```
   - Prevents browsers from MIME-sniffing responses

5. **XSS Protection**
   ```python
   SECURE_BROWSER_XSS_FILTER = True
   ```
   - Enables browser XSS filtering

6. **Session Security Enhancements**
   ```python
   SESSION_COOKIE_SAMESITE = "Strict"
   CSRF_COOKIE_SAMESITE = "Strict"
   SESSION_COOKIE_AGE = 28800  # 8 hours
   SESSION_SAVE_EVERY_REQUEST = True
   SESSION_EXPIRE_AT_BROWSER_CLOSE = True
   ```
   - Strict SameSite policy prevents CSRF attacks
   - Sessions expire after 8 hours of inactivity
   - Sessions expire when browser closes
   - Session expiry updates on every request

#### Environment Variables

**SECURE_SSL_REDIRECT:**
- Default: `false`
- Set to `true` in production with proper HTTPS setup
- Add to `.env.prod`: `SECURE_SSL_REDIRECT=true`

#### Testing
Security headers can be verified with:
```bash
cd /workspace/check-ins/backend
uv run python manage.py test tests.test_security.SecurityHeadersTests
```

## Security Considerations

### Rate Limiting
- **IP-based:** Throttling is based on IP address, which can be bypassed with distributed attacks
- **Shared IPs:** Users behind NAT/proxies share rate limits
- **Future Enhancement:** Consider implementing account-based lockouts after failed attempts

### HSTS
- **Preload Warning:** HSTS preload is permanent and difficult to reverse
- **Testing:** Test thoroughly before enabling in production
- **Rollback:** If needed, reduce HSTS max-age to 0 and wait for TTL to expire

### SameSite Cookies
- **Strict Mode:** May break legitimate cross-site workflows
- **Testing:** Verify all authentication flows work correctly
- **Fallback:** Can use "Lax" mode if "Strict" causes issues

### SSL Redirect
- **Disabled by Default:** Must explicitly enable via environment variable
- **Reverse Proxy:** Ensure X-Forwarded-Proto header is set correctly
- **Testing:** Test with and without HTTPS before enabling

## Deployment Checklist

### Development Environment
- [x] Rate limiting implemented
- [x] Security headers configured
- [x] Tests written
- [ ] Tests passing (requires disk space fix)

### Production Environment
Before deploying to production:

1. **Environment Variables:**
   - [ ] Add `SECURE_SSL_REDIRECT=true` to `.env.prod` (if using HTTPS)
   - [ ] Verify `SESSION_COOKIE_SECURE=true` in `.env.prod`
   - [ ] Verify `CSRF_COOKIE_SECURE=true` in `.env.prod`

2. **Testing:**
   - [ ] Test rate limiting with multiple failed login attempts
   - [ ] Verify security headers with browser dev tools
   - [ ] Test session expiry after 8 hours
   - [ ] Verify HTTPS redirect works correctly (if enabled)

3. **Monitoring:**
   - [ ] Monitor for increased 429 responses (rate limiting)
   - [ ] Check for session-related errors in logs
   - [ ] Verify no legitimate users are being blocked

4. **Rollback Plan:**
   - Revert `config/settings/base.py` throttle configuration
   - Revert `config/settings/prod.py` security headers
   - Remove `@throttle_classes([LoginRateThrottle])` from login_view

## Related Files

- `/workspace/check-ins/backend/accounts/views.py` - Login view with rate limiting
- `/workspace/check-ins/backend/config/settings/base.py` - DRF throttle configuration
- `/workspace/check-ins/backend/config/settings/prod.py` - Production security headers
- `/workspace/check-ins/backend/tests/test_security.py` - Security tests

## References

- [Django Security Settings](https://docs.djangoproject.com/en/stable/ref/settings/#security)
- [DRF Throttling](https://www.django-rest-framework.org/api-guide/throttling/)
- [OWASP Security Headers](https://owasp.org/www-project-secure-headers/)
- [HSTS Preload List](https://hstspreload.org/)
