# Security Audit Report - Conference Child Management System
**Django Backend Security Review**

**Date:** December 13, 2025
**Scope:** Django backend preparing for production deployment
**Auditor:** Claude Code Security Analysis

---

## Executive Summary

This security audit reviewed the Django backend of the Conference Child Management System in preparation for production deployment with real user data (PII of children and families). The application demonstrates **good foundational security practices** with proper authentication, CSRF protection, and use of Django's built-in security features.

**Overall Risk Level: MEDIUM**

The application has **7 CRITICAL** and **5 HIGH** priority security issues that **MUST** be addressed before production deployment. Additionally, there are several medium and low priority improvements that should be implemented to harden the security posture.

**Critical Issues Summary:**
- WebSocket authentication is disabled (broadcast channel accepts anonymous connections)
- No rate limiting/throttling on authentication endpoints (vulnerable to brute force)
- Weak SECRET_KEY in production environment file
- Debug logging left in production code
- Missing security headers (HSTS, CSP, X-Frame-Options)
- No admin panel IP restrictions
- QR token endpoint publicly accessible without rate limiting

---

## Critical Findings (MUST FIX)

### 1. WebSocket Authentication Disabled ⚠️ CRITICAL
**File:** `/workspace/check-ins/backend/checkins/consumers.py:21-29`

**Issue:**
```python
async def connect(self):
    # Check if user is authenticated
    user = self.scope.get("user")

    # For now, allow anonymous connections (will implement auth later if needed)
    # if not user or not user.is_authenticated:
    #     await self.close()
    #     return
```

The WebSocket consumer accepts **anonymous connections** and broadcasts check-in events to ALL connected clients, regardless of authentication status. This means:
- Anyone can connect to `ws://yourserver/ws/checkins/` without credentials
- Sensitive data (child names, QR tokens, session info) is broadcast to unauthenticated users
- No authorization checks on who can receive these real-time updates

**Impact:**
- **Data Breach:** Complete exposure of real-time check-in data including child names, QR tokens, and session information to any attacker
- **Privacy Violation:** PII exposed without authentication

**Remediation:**
```python
async def connect(self):
    """Accept WebSocket connection and add to broadcast group"""
    user = self.scope.get("user")

    # REQUIRED: Enforce authentication for WebSocket connections
    if not user or not user.is_authenticated:
        await self.close(code=4401)  # Custom close code for unauthorized
        return

    # Add this connection to the checkins broadcast group
    self.room_group_name = "checkins_broadcast"
    await self.channel_layer.group_add(
        self.room_group_name,
        self.channel_name
    )
    await self.accept()
```

**Additional Security:**
Consider implementing WebSocket origin validation in `config/asgi.py`:
```python
from channels.security.websocket import OriginValidator

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": OriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        ),
        # Only allow WebSocket connections from trusted origins
        ["http://localhost:8080", "http://127.0.0.1:8080"]  # Update for production
    ),
})
```

---

### 2. No Rate Limiting on Authentication Endpoints ⚠️ CRITICAL
**Files:** `/workspace/check-ins/backend/accounts/views.py:46-79`
**Files:** `/workspace/check-ins/backend/config/settings/base.py:145-158`

**Issue:**
The `/api/auth/login/` endpoint has **no rate limiting or throttling**, making it vulnerable to brute force attacks. An attacker can attempt unlimited login attempts to guess passwords.

```python
@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    # No rate limiting here!
    username = request.data.get("username")
    password = request.data.get("password")
    user = authenticate(request, username=username, password=password)
```

**Impact:**
- Brute force attacks against admin accounts
- Account enumeration (timing attacks can reveal valid usernames)
- Resource exhaustion (DOS via repeated login attempts)

**Remediation:**

Add Django REST Framework throttling:

```python
# config/settings/base.py
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "20/hour",  # Anonymous users: 20 requests per hour
        "user": "100/hour",  # Authenticated users: 100 requests per hour
        "login": "5/hour",  # Login attempts: 5 per hour per IP
    },
    # ... rest of config
}
```

Create a custom throttle for login endpoint:

```python
# accounts/throttles.py
from rest_framework.throttling import AnonRateThrottle

class LoginRateThrottle(AnonRateThrottle):
    scope = 'login'

    def get_cache_key(self, request, view):
        # Throttle by IP address
        ident = self.get_ident(request)
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }

# accounts/views.py
from .throttles import LoginRateThrottle

@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])  # Add this
def login_view(request):
    # ... existing code
```

**Additional Hardening:**
- Implement account lockout after 5 failed attempts (using `django-axes` or similar)
- Add CAPTCHA after 3 failed login attempts
- Log all failed authentication attempts to audit logs
- Add delays between failed login attempts (progressive delays)

---

### 3. Weak Production SECRET_KEY ⚠️ CRITICAL
**File:** `/workspace/check-ins/.env.prod`

**Issue:**
The production `.env.prod` file contains a weak, human-readable SECRET_KEY:

```bash
SECRET_KEY=change-this-to-a-random-secret-key-in-production
```

While this file is in `.gitignore`, it demonstrates that production is likely using a weak secret. Django's SECRET_KEY is used for:
- Cryptographic signing of session cookies
- CSRF tokens
- Password reset tokens
- Any cryptographic operations

**Impact:**
- Session hijacking (attackers can forge session cookies)
- CSRF token forgery
- Password reset token prediction
- Complete authentication bypass

**Remediation:**

**Before deployment, generate a strong SECRET_KEY:**

```bash
# Generate a cryptographically secure secret key
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Update `.env.prod`:
```bash
SECRET_KEY=<generated-50+-character-random-string>
```

**Verification Check:**
Add this to production startup to enforce strong secrets:

```python
# config/settings/prod.py
import sys

# Enforce strong SECRET_KEY in production
if SECRET_KEY == "insecure-change-me" or "change-this" in SECRET_KEY.lower():
    print("ERROR: Production SECRET_KEY is not set properly!")
    print("Generate a strong key with:")
    print("  python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'")
    sys.exit(1)

if len(SECRET_KEY) < 50:
    print("WARNING: SECRET_KEY should be at least 50 characters long")
```

---

### 4. Debug Logging in Production Code ⚠️ CRITICAL
**File:** `/workspace/check-ins/backend/checkins/views.py:38-43, 157-163`

**Issue:**
Debug logging statements are left in production code that log **sensitive authentication data**:

```python
# Line 38-43
logger = logging.getLogger(__name__)
logger.warning(f"CSRF Debug - Headers: {dict(request.headers)}")
logger.warning(f"CSRF Debug - Cookies: {request.COOKIES}")
logger.warning(f"CSRF Debug - User: {request.user}, Authenticated: {request.user.is_authenticated}")

# Line 157-163
logger.warning(f"CHECK_OUT DEBUG - User: {request.user}, Authenticated: {request.user.is_authenticated}")
logger.warning(f"CHECK_OUT DEBUG - Method: {request.method}, PK: {pk}")
logger.warning(f"CHECK_OUT DEBUG - Headers: {dict(request.headers)}")
logger.warning(f"CHECK_OUT DEBUG - Cookies: {request.COOKIES}")
```

These logs expose:
- Session cookies
- CSRF tokens
- Authentication headers
- All HTTP headers (may include sensitive data)

**Impact:**
- **Session hijacking:** Session cookies logged in plaintext
- **Token exposure:** CSRF tokens exposed in logs
- **Log injection:** Attackers can inject malicious content into logs
- **Compliance violation:** Logging sensitive data may violate GDPR/privacy laws

**Remediation:**

**Remove all debug logging immediately:**

```python
# Remove these lines entirely from checkins/views.py:
# Lines 38-43, 157-163

# If debugging is needed, use proper DEBUG flag checking:
import logging
logger = logging.getLogger(__name__)

if settings.DEBUG:
    # Only log in development, never in production
    logger.debug(f"User authenticated: {request.user.is_authenticated}")
    # NEVER log cookies, tokens, or headers
```

**Configure proper logging:**

```python
# config/settings/base.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs/django.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'security': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs/security.log',
            'maxBytes': 1024 * 1024 * 10,
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['security'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# In production:
if not DEBUG:
    # Never log request data in production
    LOGGING['loggers']['django.request'] = {
        'handlers': ['security'],
        'level': 'ERROR',  # Only log errors, not debug info
        'propagate': False,
    }
```

---

### 5. Missing Security Headers ⚠️ CRITICAL
**File:** `/workspace/check-ins/backend/config/settings/base.py`, `/workspace/check-ins/backend/config/settings/prod.py`

**Issue:**
Critical security headers are **missing** from the production configuration:

Missing headers:
- `Strict-Transport-Security` (HSTS) - Not configured
- `Content-Security-Policy` (CSP) - Not configured
- `X-Frame-Options` - Not explicitly set
- `X-Content-Type-Options` - Not explicitly set
- `Referrer-Policy` - Not configured
- `Permissions-Policy` - Not configured

**Impact:**
- **No HSTS:** Vulnerable to SSL stripping attacks
- **No CSP:** Vulnerable to XSS attacks
- **Clickjacking:** Without X-Frame-Options, site can be framed
- **MIME sniffing:** Without X-Content-Type-Options, browsers may misinterpret content types

**Remediation:**

Add to `config/settings/prod.py`:

```python
# Security Headers for Production
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True  # Redirect all HTTP to HTTPS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")  # Already set ✓

# Browser Security
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'  # Prevent clickjacking

# Referrer Policy
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Content Security Policy
# Note: This is strict - adjust based on your actual frontend needs
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")  # SvelteKit may need unsafe-inline
CSP_IMG_SRC = ("'self'", "data:", "blob:")
CSP_FONT_SRC = ("'self'",)
CSP_CONNECT_SRC = ("'self'", "ws:", "wss:")  # Allow WebSocket connections
CSP_FRAME_ANCESTORS = ("'none'",)  # Prevent framing
```

Install and configure `django-csp`:

```bash
uv add django-csp
```

```python
# config/settings/base.py
INSTALLED_APPS = [
    # ... existing apps
    'csp',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'csp.middleware.CSPMiddleware',  # Add this
    # ... rest of middleware
]
```

**Verification:**
After deployment, test with: https://securityheaders.com/

---

### 6. Admin Panel Without IP Restrictions ⚠️ CRITICAL
**File:** `/workspace/check-ins/backend/config/urls.py:37`

**Issue:**
The Django admin panel at `/admin/` is accessible from **any IP address** with no additional restrictions beyond username/password. Given that this system manages child PII, the admin panel is a high-value target.

```python
urlpatterns = [
    path("admin/", admin.site.urls),  # No IP restrictions!
    # ...
]
```

**Impact:**
- Increased attack surface for brute force attempts
- No defense-in-depth for admin access
- Admin panel accessible from anywhere on the internet

**Remediation:**

**Option 1: IP Whitelist Middleware (Recommended)**

```python
# config/middleware/admin_ip_whitelist.py
from django.core.exceptions import PermissionDenied
from django.conf import settings
import ipaddress

class AdminIPWhitelistMiddleware:
    """
    Restrict admin panel access to whitelisted IPs only.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # Load from settings or env
        self.allowed_ips = getattr(settings, 'ADMIN_ALLOWED_IPS', [])

    def __call__(self, request):
        if request.path.startswith('/admin/'):
            client_ip = self.get_client_ip(request)

            if not self.is_ip_allowed(client_ip):
                raise PermissionDenied("Admin access restricted to authorized IPs")

        return self.get_response(request)

    def get_client_ip(self, request):
        """Get real client IP, accounting for proxies"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def is_ip_allowed(self, client_ip):
        """Check if IP is in whitelist (supports CIDR notation)"""
        if not self.allowed_ips:
            return True  # No restrictions if not configured

        try:
            client_addr = ipaddress.ip_address(client_ip)
            for allowed in self.allowed_ips:
                if '/' in allowed:  # CIDR notation
                    if client_addr in ipaddress.ip_network(allowed, strict=False):
                        return True
                else:  # Single IP
                    if client_addr == ipaddress.ip_address(allowed):
                        return True
        except ValueError:
            return False

        return False

# config/settings/prod.py
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'config.middleware.admin_ip_whitelist.AdminIPWhitelistMiddleware',  # Add this
    # ... rest of middleware
]

# Whitelist for admin access (update with your actual IPs)
ADMIN_ALLOWED_IPS = os.getenv('ADMIN_ALLOWED_IPS', '').split(',')
# Example in .env.prod:
# ADMIN_ALLOWED_IPS=192.168.1.0/24,10.0.0.5
```

**Option 2: VPN-Only Access**
- Require VPN connection for admin access
- Use firewall rules to block `/admin/` from public internet
- Only allow access via internal network

**Option 3: Two-Factor Authentication**
Install `django-otp` for 2FA on admin panel:

```bash
uv add django-otp qrcode
```

---

### 7. Public QR Endpoint Without Rate Limiting ⚠️ CRITICAL
**File:** `/workspace/check-ins/backend/families/qr_views.py:13-67`

**Issue:**
The `/api/qr/<token>/` endpoint is publicly accessible without authentication (by design for kiosk usage), but has **no rate limiting**. An attacker can:
- Enumerate valid QR tokens by brute force (UUIDs are predictable if using sequential generation)
- Launch DOS attacks
- Scrape all child data if tokens are guessable

```python
@api_view(["GET"])
@permission_classes([AllowAny])  # Public endpoint - no auth
def qr_info(request, token):
    # No rate limiting!
    try:
        child = Child.objects.select_related("family").prefetch_related(
            "checkin_records__session"
        ).get(qr_token=token)
```

**Impact:**
- Data mining of child information
- DOS via repeated requests
- Token enumeration if QR tokens are predictable

**Remediation:**

**Apply aggressive rate limiting:**

```python
# families/throttles.py
from rest_framework.throttling import AnonRateThrottle

class QRScanRateThrottle(AnonRateThrottle):
    scope = 'qr_scan'
    rate = '30/minute'  # Max 30 QR scans per minute per IP

# families/qr_views.py
from rest_framework.decorators import throttle_classes
from .throttles import QRScanRateThrottle

@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([QRScanRateThrottle])  # Add this
def qr_info(request, token):
    # ... existing code
```

**Add to settings:**
```python
# config/settings/base.py
REST_FRAMEWORK = {
    # ... existing config
    "DEFAULT_THROTTLE_RATES": {
        "anon": "20/hour",
        "user": "100/hour",
        "login": "5/hour",
        "qr_scan": "30/minute",  # Add this
    },
}
```

**Additional Security:**
- Use UUIDv4 for QR tokens (already doing this ✓)
- Consider time-based token expiration for high-security scenarios
- Log suspicious QR scan patterns (many failed lookups from same IP)

---

## High Priority Findings

### 8. Missing Session Security Configuration ⚠️ HIGH
**File:** `/workspace/check-ins/backend/config/settings/base.py`

**Issue:**
Session configuration is using Django defaults, which may not be optimal for production:
- No `SESSION_COOKIE_AGE` set (default: 2 weeks)
- No `SESSION_EXPIRE_AT_BROWSER_CLOSE` set
- No `SESSION_SAVE_EVERY_REQUEST` set

**Impact:**
- Sessions may persist longer than necessary
- Increased risk of session hijacking from old sessions

**Remediation:**

```python
# config/settings/base.py
# Session Security
SESSION_COOKIE_AGE = 43200  # 12 hours (adjust as needed)
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # Expire when browser closes
SESSION_SAVE_EVERY_REQUEST = True  # Refresh session on each request
SESSION_COOKIE_HTTPONLY = True  # Already set ✓
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"  # Already set ✓
SESSION_COOKIE_SAMESITE = 'Lax'  # Already set ✓
SESSION_COOKIE_NAME = 'sessionid'  # Don't use default name

# Consider database-backed sessions for better security
SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # Or 'cached_db' for performance
```

---

### 9. No Object-Level Permission Checks (Potential IDOR) ⚠️ HIGH
**File:** `/workspace/check-ins/backend/checkins/views.py` (multiple locations)

**Issue:**
While all ViewSets require authentication (`permission_classes = [IsAuthenticated]`), there are **no object-level permission checks**. The current implementation assumes:
- All authenticated users are staff members
- All staff members have equal permissions to all data

However, Django supports fine-grained permissions that are **not being used**:

```python
class CheckInRecordViewSet(viewsets.ModelViewSet):
    queryset = CheckInRecord.objects.select_related(...).all()  # Returns ALL records
    permission_classes = [IsAuthenticated]  # Only checks if logged in
    # No object-level permissions!
```

**Impact:**
- Any authenticated user can view/modify ANY check-in record
- If you add non-staff user types in future, they'll have full access
- No audit trail of who accessed what (only who modified)

**Current Risk:** LOW (all current users are admin staff)
**Future Risk:** HIGH (if you add kiosk-mode users or limited staff)

**Remediation:**

**Option 1: Use Django's built-in permissions (Recommended for most cases)**

```python
from rest_framework.permissions import DjangoModelPermissions

class CheckInRecordViewSet(viewsets.ModelViewSet):
    queryset = CheckInRecord.objects.select_related(...).all()
    permission_classes = [DjangoModelPermissions]  # Checks add/change/delete/view permissions
```

**Option 2: Custom object-level permissions**

```python
# checkins/permissions.py
from rest_framework import permissions

class IsStaffOrReadOnly(permissions.BasePermission):
    """
    Allow staff to make changes, but allow read-only for authenticated users.
    """
    def has_permission(self, request, view):
        # Must be authenticated
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Read permissions for any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only for staff
        return request.user.is_staff

# checkins/views.py
from .permissions import IsStaffOrReadOnly

class CheckInRecordViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffOrReadOnly]
```

**Option 3: Add role-based access control (RBAC)**

Consider adding user roles (admin, staff, kiosk) and restricting access accordingly.

---

### 10. Audit Log Doesn't Capture All Actions ⚠️ HIGH
**File:** `/workspace/check-ins/backend/checkins/views.py`

**Issue:**
The audit log (`AuditLog` model) only captures certain actions:
- ✓ Check-in
- ✓ Check-out
- ✓ Undo check-in/check-out
- ✓ Label printed

**Missing audit events:**
- Family creation/update/deletion
- Child data modifications
- Parent data modifications
- Session activation/deactivation
- Ticket creation/deletion
- Login/logout events
- Failed login attempts
- Admin panel access
- API endpoint access patterns

**Impact:**
- Incomplete forensic trail
- Cannot detect unauthorized access
- Cannot trace data breaches
- Compliance issues (GDPR requires access logging)

**Remediation:**

**Add comprehensive audit logging:**

```python
# accounts/middleware/audit_middleware.py
from checkins.models import AuditLog
import json

class AuditMiddleware:
    """
    Log all authenticated API access to audit log.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Log API access
        if request.path.startswith('/api/') and request.user.is_authenticated:
            # Skip audit log endpoints to avoid recursion
            if not request.path.startswith('/api/audit-logs'):
                self.log_api_access(request, response)

        return response

    def log_api_access(self, request, response):
        """Log API access to audit trail"""
        # Only log write operations (POST, PUT, PATCH, DELETE)
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            AuditLog.objects.create(
                user=request.user,
                action=f"api_{request.method.lower()}",
                entity_type=request.path.split('/')[2] if len(request.path.split('/')) > 2 else 'unknown',
                entity_id=request.path,
                details={
                    'method': request.method,
                    'path': request.path,
                    'status_code': response.status_code,
                    'ip_address': self.get_client_ip(request),
                }
            )

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
```

**Add login/logout logging:**

```python
# accounts/views.py
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    AuditLog.objects.create(
        user=user,
        action='login',
        entity_type='AdminUser',
        entity_id=str(user.id),
        details={
            'ip_address': get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')
        }
    )

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    if user:
        AuditLog.objects.create(
            user=user,
            action='logout',
            entity_type='AdminUser',
            entity_id=str(user.id),
            details={'ip_address': get_client_ip(request)}
        )

@receiver(user_login_failed)
def log_failed_login(sender, credentials, request, **kwargs):
    AuditLog.objects.create(
        user=None,  # Failed login - no user
        action='login_failed',
        entity_type='AdminUser',
        entity_id=credentials.get('username', 'unknown'),
        details={
            'username': credentials.get('username'),
            'ip_address': get_client_ip(request)
        }
    )
```

---

### 11. No Input Validation on QR Token Length ⚠️ HIGH
**File:** `/workspace/check-ins/backend/families/models.py:66`

**Issue:**
The QR token field has no max length validation, allowing arbitrarily long input:

```python
qr_token = models.CharField(max_length=255, unique=True, null=True, blank=True, verbose_name=_("QR Token"))
```

While Django validates max_length at the database level, the serializers and views don't enforce this. An attacker could submit extremely long strings causing:
- Database performance issues
- Memory exhaustion
- Buffer overflow in downstream systems

**Impact:**
- DOS via resource exhaustion
- Database performance degradation

**Remediation:**

Add validation in serializer:

```python
# families/serializers.py
from rest_framework import serializers

class ChildSerializer(serializers.ModelSerializer):
    class Meta:
        model = Child
        fields = [...]
        read_only_fields = ["id", "qr_token", ...]

    def validate_qr_token(self, value):
        """Validate QR token format and length"""
        if value and len(value) > 255:
            raise serializers.ValidationError("QR token too long")

        # Optionally validate UUID format
        import uuid
        try:
            uuid.UUID(value)
        except ValueError:
            raise serializers.ValidationError("Invalid QR token format")

        return value
```

**Also validate in view:**

```python
# checkins/views.py (check_in action)
if not child.qr_token:
    child.qr_token = str(uuid.uuid4())  # Already doing this ✓
    child.save()
```

This is already correct, but ensure QR token generation is never user-controlled.

---

### 12. Potential XSS in Template Rendering ⚠️ HIGH
**File:** `/workspace/check-ins/backend/checkins/templates/print_label.html:82-83`

**Issue:**
Child names are rendered directly in HTML template without explicit escaping:

```html
<div class="child-name">{{ checkin.child.first_name }} {{ checkin.child.last_name }}</div>
```

While Django's template engine **auto-escapes by default** (✓), if a developer accidentally uses `|safe` or `mark_safe()` in the view, this could become an XSS vulnerability.

**Current Risk:** LOW (Django auto-escapes)
**Future Risk:** MEDIUM (if someone adds `|safe` filter)

**Remediation:**

**Explicitly document and enforce escaping:**

```html
<!-- checkins/templates/print_label.html -->
<!--
SECURITY: Child names are user-input and must be escaped.
Django auto-escapes by default - DO NOT use |safe filter.
-->
<div class="child-name">{{ checkin.child.first_name|escape }} {{ checkin.child.last_name|escape }}</div>
```

**Add Content Security Policy header to prevent XSS:**

```python
# config/settings/prod.py
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'",)  # No inline scripts
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")  # Allow inline styles for label printing
```

**Validate input:**

```python
# families/serializers.py
class ChildCreateSerializer(serializers.ModelSerializer):
    def validate_first_name(self, value):
        """Sanitize child name to prevent script injection"""
        # Remove any HTML tags
        import re
        sanitized = re.sub(r'<[^>]*>', '', value)
        if sanitized != value:
            raise serializers.ValidationError("HTML tags not allowed in names")
        return sanitized

    def validate_last_name(self, value):
        # Same validation
        import re
        sanitized = re.sub(r'<[^>]*>', '', value)
        if sanitized != value:
            raise serializers.ValidationError("HTML tags not allowed in names")
        return sanitized
```

---

## Medium Priority Findings

### 13. CORS Configuration Allows Credentials 🔶 MEDIUM
**File:** `/workspace/check-ins/backend/config/settings/base.py:142`

**Issue:**
```python
CORS_ALLOW_CREDENTIALS = True  # Allow cookies in cross-origin requests
```

While this is necessary for session authentication, it should be paired with strict origin validation.

**Current State:**
- ✓ `CORS_ALLOWED_ORIGINS` is configured (not using wildcard)
- ✓ Origins are loaded from environment variables

**Risk:**
If `CORS_ALLOWED_ORIGINS` is misconfigured or contains wildcards, credentials could be leaked to unauthorized origins.

**Remediation:**

Add validation in settings:

```python
# config/settings/base.py
CORS_ALLOWED_ORIGINS = [host for host in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if host]

# Validate no wildcards when credentials are allowed
if CORS_ALLOW_CREDENTIALS:
    if '*' in CORS_ALLOWED_ORIGINS or any('*' in origin for origin in CORS_ALLOWED_ORIGINS):
        raise ValueError("Cannot use wildcard CORS origins when CORS_ALLOW_CREDENTIALS is True")

    if not CORS_ALLOWED_ORIGINS:
        raise ValueError("CORS_ALLOWED_ORIGINS must be set when CORS_ALLOW_CREDENTIALS is True")
```

---

### 14. No Password Complexity Requirements 🔶 MEDIUM
**File:** `/workspace/check-ins/backend/config/settings/base.py:106-111`

**Issue:**
Django's default password validators are used, but they allow weak passwords:
- Minimum length: 8 characters (default)
- No uppercase requirement
- No special character requirement

**Current validators:**
```python
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},  # Default: 8 chars
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
```

**Impact:**
- Weak passwords increase brute force success rate
- Admin accounts may use simple passwords

**Remediation:**

Strengthen password requirements:

```python
# config/settings/base.py
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12}  # Increase from default 8 to 12
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
```

**For higher security, add custom validator:**

```python
# accounts/validators.py
from django.core.exceptions import ValidationError
import re

class ComplexityValidator:
    """
    Require passwords to have:
    - Uppercase letter
    - Lowercase letter
    - Number
    - Special character
    """
    def validate(self, password, user=None):
        if not re.search(r'[A-Z]', password):
            raise ValidationError("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', password):
            raise ValidationError("Password must contain at least one lowercase letter")
        if not re.search(r'[0-9]', password):
            raise ValidationError("Password must contain at least one number")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError("Password must contain at least one special character")

    def get_help_text(self):
        return "Password must contain uppercase, lowercase, number, and special character"

# Add to settings
AUTH_PASSWORD_VALIDATORS = [
    # ... existing validators
    {"NAME": "accounts.validators.ComplexityValidator"},
]
```

---

### 15. Admin Panel Uses Default URL 🔶 MEDIUM
**File:** `/workspace/check-ins/backend/config/urls.py:37`

**Issue:**
The admin panel is accessible at the default `/admin/` URL, which is well-known and frequently targeted by automated scanners.

```python
path("admin/", admin.site.urls),
```

**Impact:**
- Increased automated attack attempts
- Easy to discover admin interface

**Remediation:**

Use a non-standard URL:

```python
# config/urls.py
import os

# Use custom admin URL from environment or default to random path
ADMIN_PATH = os.getenv('ADMIN_PATH', 'secure-admin-portal-2025/')

urlpatterns = [
    path(ADMIN_PATH, admin.site.urls),  # Custom path
    # ...
]
```

```bash
# .env.prod
ADMIN_PATH=my-custom-secret-admin-path/
```

**Additional hardening:**
```python
# config/urls.py
from django.contrib import admin

admin.site.site_header = "Conference Management"  # Custom branding
admin.site.site_title = "Conference Admin"
admin.site.index_title = "Administration"
```

---

### 16. No Database Connection Encryption 🔶 MEDIUM
**File:** `/workspace/check-ins/backend/config/settings/base.py:79-104`

**Issue:**
Database connections don't enforce SSL/TLS encryption:

```python
return {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": parsed.path.lstrip("/"),
    "USER": parsed.username,
    "PASSWORD": parsed.password,
    "HOST": parsed.hostname,
    "PORT": parsed.port or "5432",
    # No SSL configuration!
}
```

**Impact:**
- Database credentials transmitted in plaintext over network
- Query data (including PII) transmitted unencrypted
- Man-in-the-middle attacks possible

**Remediation:**

Enable SSL for PostgreSQL connections:

```python
def _database_config():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }

    parsed = urlparse(database_url)
    if parsed.scheme.startswith("postgres"):
        config = {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/"),
            "USER": parsed.username,
            "PASSWORD": parsed.password,
            "HOST": parsed.hostname,
            "PORT": parsed.port or "5432",
        }

        # Enable SSL in production
        if not DEBUG:
            config["OPTIONS"] = {
                "sslmode": "require",  # Or "verify-full" for certificate validation
            }

        return config

    raise ValueError("Unsupported DATABASE_URL scheme")
```

---

### 17. Sensitive Data in Audit Log Details 🔶 MEDIUM
**File:** `/workspace/check-ins/backend/checkins/views.py:118-130`

**Issue:**
Audit logs store child names in plaintext in the `details` JSON field:

```python
AuditLog.objects.create(
    user=request.user,
    action="check_in",
    entity_type="CheckInRecord",
    entity_id=str(record.id),
    details={
        "child_id": str(child.id),
        "child_name": f"{child.first_name} {child.last_name}",  # PII stored
        "session_id": str(session.id),
        "session_name": session.name,
        "supervised": supervised,
    },
)
```

**Impact:**
- PII (child names) stored in audit logs
- Audit logs are typically retained longer than operational data
- May violate data retention policies
- Difficult to anonymize if child record is deleted

**Remediation:**

**Option 1: Store IDs only, not names**

```python
AuditLog.objects.create(
    user=request.user,
    action="check_in",
    entity_type="CheckInRecord",
    entity_id=str(record.id),
    details={
        "child_id": str(child.id),
        # Don't store child_name - lookup from child_id when displaying logs
        "session_id": str(session.id),
        # Don't store session_name - lookup from session_id
        "supervised": supervised,
    },
)
```

**Option 2: Hash or pseudonymize names**

```python
import hashlib

def pseudonymize(name):
    """Create pseudonymized version of name for logging"""
    return hashlib.sha256(name.encode()).hexdigest()[:8]

AuditLog.objects.create(
    # ...
    details={
        "child_id": str(child.id),
        "child_name_hash": pseudonymize(f"{child.first_name} {child.last_name}"),
        # ...
    },
)
```

---

### 18. No ALLOWED_HOSTS Validation 🔶 MEDIUM
**File:** `/workspace/check-ins/backend/config/settings/base.py:17-22`

**Issue:**
`ALLOWED_HOSTS` accepts wildcard `*` if environment variable is empty:

```python
ALLOWED_HOSTS = [host for host in os.getenv("ALLOWED_HOSTS", "*").split(",") if host]
if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['*']:
    ALLOWED_HOSTS = ['*']  # Allows all hosts!
```

**Impact:**
- Host header injection attacks
- Cache poisoning
- Password reset poisoning

**Remediation:**

Enforce strict ALLOWED_HOSTS in production:

```python
# config/settings/base.py
ALLOWED_HOSTS = [host for host in os.getenv("ALLOWED_HOSTS", "").split(",") if host]

# config/settings/prod.py
# Override and enforce ALLOWED_HOSTS in production
ALLOWED_HOSTS = [host.strip() for host in os.getenv("ALLOWED_HOSTS", "").split(",") if host.strip()]

if not ALLOWED_HOSTS or '*' in ALLOWED_HOSTS:
    raise ValueError("ALLOWED_HOSTS must be set to specific domains in production (not '*')")

# Validate format
import re
for host in ALLOWED_HOSTS:
    if not re.match(r'^[a-zA-Z0-9.-]+$', host):
        raise ValueError(f"Invalid ALLOWED_HOSTS entry: {host}")
```

---

## Low Priority Findings

### 19. No Content-Type Validation on File Uploads 🔵 LOW
**File:** File upload functionality not found in current codebase

**Status:** Currently no file upload endpoints detected, but if added in future:

**Recommendation:**
If implementing file uploads (e.g., child photos, documents):
- Validate file types using magic bytes, not just extension
- Limit file sizes
- Store uploads outside web root
- Scan for malware
- Use UUIDs for filenames (prevent directory traversal)

---

### 20. Hardcoded QR URL in PDF Generation 🔵 LOW
**File:** `/workspace/check-ins/backend/checkins/utils.py:90`

**Issue:**
QR code URL is hardcoded to localhost:

```python
qr_url = f"http://localhost:8080/qr/{record.child.qr_token}"
```

**Impact:**
- QR codes won't work in production
- Labels printed in dev will have wrong URLs

**Remediation:**

Use dynamic URL from settings:

```python
# config/settings/base.py
QR_BASE_URL = os.getenv('QR_BASE_URL', 'http://localhost:8080')

# checkins/utils.py
from django.conf import settings

def generate_label_pdf(checkin_records):
    # ...
    qr_url = f"{settings.QR_BASE_URL}/qr/{record.child.qr_token}"
```

```bash
# .env.prod
QR_BASE_URL=https://yourdomain.com
```

---

### 21. Session Cookie Name Uses Default 🔵 LOW
**File:** Currently using default `sessionid` cookie name

**Recommendation:**

Change to custom name to reduce fingerprinting:

```python
# config/settings/base.py
SESSION_COOKIE_NAME = 'ccms_session'  # Conference Child Management System
CSRF_COOKIE_NAME = 'ccms_csrf'
```

---

### 22. No Security.txt File 🔵 LOW

**Issue:**
No `/.well-known/security.txt` file for vulnerability disclosure.

**Recommendation:**

Create security contact information:

```python
# config/urls.py
from django.http import HttpResponse
from django.views.decorators.http import require_GET

@require_GET
def security_txt(request):
    content = """Contact: mailto:security@yourdomain.com
Expires: 2026-12-31T23:59:59.000Z
Preferred-Languages: en
"""
    return HttpResponse(content, content_type='text/plain')

urlpatterns = [
    # ...
    path('.well-known/security.txt', security_txt),
]
```

---

## Positive Security Controls ✅

The application demonstrates several **good security practices**:

### Authentication & Authorization
✅ **Proper authentication required** on all sensitive endpoints
✅ **Session-based authentication** using Django's secure session framework
✅ **Password hashing** using Django's default PBKDF2 (strong algorithm)
✅ **AllowAny permission** only on appropriate public endpoints (CSRF, QR lookup)

### CSRF Protection
✅ **CSRF middleware enabled** in production
✅ **CSRF tokens required** for state-changing operations
✅ **Proper CSRF cookie configuration** (HttpOnly=False for JavaScript access, which is correct for CSRF tokens)

### Input Validation
✅ **Django ORM** prevents SQL injection (no raw queries found)
✅ **Serializers validate input** before database operations
✅ **UUID primary keys** prevent enumeration attacks
✅ **Unique constraints** on critical fields (QR tokens, check-in records)

### Data Protection
✅ **No hardcoded secrets** in code (using environment variables)
✅ **.env files in .gitignore** (not committed to repository)
✅ **Proper foreign key relationships** with CASCADE/PROTECT as appropriate
✅ **Auto-escaping in templates** (Django default)

### Infrastructure
✅ **Separate dev/prod configurations** (good separation of concerns)
✅ **DEBUG=False in production** (prevents information disclosure)
✅ **WhiteNoise for static files** (secure static file serving)
✅ **PostgreSQL in production** (better security than SQLite)
✅ **Docker containerization** (isolation and reproducibility)

### Audit & Logging
✅ **Audit log model** captures critical operations
✅ **User association** on all check-in/check-out operations
✅ **Timestamps** on all records
✅ **JSONField for flexible audit details**

### Code Quality
✅ **Type hints** used throughout (improves code safety)
✅ **Descriptive model names** and relationships
✅ **No obvious SQL injection vectors** (using ORM properly)
✅ **No dangerous functions** (eval, exec, pickle) found

---

## Dependency Security

**Django Version:** 5.0+ (Latest stable) ✅
**DRF Version:** 3.15+ ✅
**All dependencies** appear to be modern versions ✅

**Recommendation:**
Run regular dependency audits:

```bash
# Check for known vulnerabilities
uv pip list --outdated
pip-audit  # Install with: uv add pip-audit

# Consider adding to CI/CD:
# - Safety (dependency vulnerability scanner)
# - Bandit (Python security linter)
# - Semgrep (static analysis)
```

---

## Pre-Deployment Checklist

Before deploying to production, complete the following:

### Critical (Must Complete)
- [ ] **Enable WebSocket authentication** (Issue #1)
- [ ] **Implement rate limiting** on auth endpoints (Issue #2)
- [ ] **Generate and set strong SECRET_KEY** (Issue #3)
- [ ] **Remove debug logging** from production code (Issue #4)
- [ ] **Configure security headers** (HSTS, CSP, X-Frame-Options) (Issue #5)
- [ ] **Implement admin IP restrictions** or 2FA (Issue #6)
- [ ] **Add rate limiting** to QR endpoint (Issue #7)

### High Priority (Strongly Recommended)
- [ ] Configure session expiration (Issue #8)
- [ ] Review object-level permissions (Issue #9)
- [ ] Expand audit logging coverage (Issue #10)
- [ ] Validate QR token input (Issue #11)
- [ ] Review XSS prevention in templates (Issue #12)

### Medium Priority
- [ ] Validate CORS configuration (Issue #13)
- [ ] Strengthen password requirements (Issue #14)
- [ ] Change admin URL from default (Issue #15)
- [ ] Enable database SSL/TLS (Issue #16)
- [ ] Review audit log data retention (Issue #17)
- [ ] Enforce ALLOWED_HOSTS validation (Issue #18)

### Configuration Verification
- [ ] Verify `.env.prod` has strong SECRET_KEY
- [ ] Verify `DEBUG=False` in production
- [ ] Verify `ALLOWED_HOSTS` is not `*`
- [ ] Verify `SESSION_COOKIE_SECURE=True` (if using HTTPS)
- [ ] Verify `CSRF_COOKIE_SECURE=True` (if using HTTPS)
- [ ] Verify CORS origins are restrictive
- [ ] Verify database uses SSL (if remote)

### Testing
- [ ] Run security header check: https://securityheaders.com
- [ ] Test rate limiting on login endpoint
- [ ] Test WebSocket requires authentication
- [ ] Verify admin panel IP restrictions work
- [ ] Test CSRF protection on all POST endpoints
- [ ] Verify QR endpoint rate limiting

### Documentation
- [ ] Document security contact (security.txt)
- [ ] Document incident response plan
- [ ] Document backup and recovery procedures
- [ ] Document access control policies

---

## Recommended Security Tools

### Development
```bash
# Install security linting tools
uv add --dev bandit safety semgrep

# Run security checks
bandit -r backend/  # Python security issues
safety check  # Dependency vulnerabilities
semgrep --config=auto backend/  # SAST scanning
```

### Production Monitoring
- **Django-axes**: Automatic lockout after failed login attempts
- **Django-defender**: Advanced brute force protection
- **Django-ratelimit**: Decorator-based rate limiting
- **Sentry**: Error tracking and security monitoring
- **fail2ban**: IP banning for repeated attacks

### Infrastructure
- **Let's Encrypt**: Free SSL/TLS certificates
- **Cloudflare**: DDoS protection and WAF
- **AWS WAF/Azure WAF**: Web application firewall
- **Database encryption**: Enable encryption at rest

---

## Compliance Considerations

### GDPR (if applicable)
- ✅ Audit logging for access tracking
- ⚠️ Need data retention policies
- ⚠️ Need data export/deletion procedures
- ⚠️ Need consent management
- ⚠️ Need privacy policy

### Child Data Protection (COPPA/Similar)
- ⚠️ Parental consent tracking
- ⚠️ Age verification
- ⚠️ Data minimization review
- ⚠️ Secure deletion procedures

---

## Conclusion

The Conference Child Management System demonstrates **solid foundational security** with proper use of Django's built-in protections. However, **7 critical vulnerabilities** must be addressed before production deployment:

1. WebSocket authentication bypass
2. Missing rate limiting on authentication
3. Weak production SECRET_KEY
4. Debug logging exposing sensitive data
5. Missing security headers
6. Unprotected admin panel
7. Unprotected public QR endpoint

**Recommendation:** Address all CRITICAL issues (1-7) and HIGH priority issues (8-12) before deploying to production with real user data. The remaining medium and low priority issues should be addressed in the first maintenance cycle after launch.

**Estimated remediation time:**
- Critical issues: 8-16 hours
- High priority: 4-8 hours
- Medium priority: 4-6 hours
- Total: 16-30 hours

With these fixes implemented, the application will have a **strong security posture** appropriate for handling sensitive child and family data in a production environment.

---

**End of Security Audit Report**
