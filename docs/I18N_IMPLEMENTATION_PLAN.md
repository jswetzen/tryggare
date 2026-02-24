# Internationalization (i18n) Implementation Plan
## Conference Child Management System - Swedish & English

**Date:** 2025-11-25  
**Languages:** English (en), Swedish (sv)  
**Current Status:** No i18n implementation (hardcoded English strings)

---

## Executive Summary

This document provides a comprehensive analysis and implementation plan for adding Swedish and English internationalization to the Django + SvelteKit application. The system currently has **zero i18n implementation** despite having `svelte-i18n` installed in the frontend package.json.

### Key Findings

- **Backend (Django)**: No i18n setup (USE_I18N=True but no translations)
- **Frontend (SvelteKit)**: `svelte-i18n` installed but not configured
- **Total translatable strings**: ~150+ strings across backend and frontend
- **Critical areas**: Error messages, validation, UI labels, navigation

---

## Table of Contents

1. [Current i18n Status](#1-current-i18n-status)
2. [Architecture Considerations](#2-architecture-considerations)
3. [Backend Translation Requirements](#3-backend-translation-requirements)
4. [Frontend Translation Requirements](#4-frontend-translation-requirements)
5. [Implementation Roadmap](#5-implementation-roadmap)
6. [File-by-File Analysis](#6-file-by-file-analysis)

---

## 1. Current i18n Status

### Django Backend (Python)

**Settings Configuration** (`backend/config/settings/base.py`):
- Line 106: `LANGUAGE_CODE = "en-us"` (English only)
- Line 108: `USE_I18N = True` (i18n enabled but not used)
- **Missing**: No `LOCALE_PATHS`, no middleware, no translation files

**Current State**:
- ✅ Django's i18n framework enabled
- ❌ No locale directory structure
- ❌ No translation files (.po/.mo)
- ❌ No `django.middleware.locale.LocaleMiddleware`
- ❌ No `gettext()` or `ugettext()` usage in code
- ❌ No model field `verbose_name` translations

### SvelteKit Frontend (TypeScript/Svelte)

**Dependencies** (`frontend/package.json`):
- ✅ `svelte-i18n: ^4.0.0` installed
- ❌ Not configured
- ❌ No translation files
- ❌ No locale setup

**Current State**:
- ✅ Library available
- ❌ Not initialized
- ❌ No translation JSON files
- ❌ All UI strings hardcoded in English

---

## 2. Architecture Considerations

### Language Selection Strategy

**Recommendation: Cookie-Based Unified Approach**

```
┌─────────────┐
│   User      │
│  Selects    │──────┐
│  Language   │      │
└─────────────┘      │
                     ▼
            ┌────────────────┐
            │  Set Cookie:   │
            │  "language=sv" │
            └────────────────┘
                     │
        ┏━━━━━━━━━━━┻━━━━━━━━━━━┓
        ▼                       ▼
┌───────────────┐      ┌───────────────┐
│ Django Backend│      │ SvelteKit     │
│ Read Cookie   │      │ Read Cookie   │
│ Activate Lang │      │ Load Locale   │
└───────────────┘      └───────────────┘
```

**Storage Location**: 
- Cookie name: `django_language` (Django standard)
- Domain: Shared between frontend and backend
- SameSite: `Lax`
- Path: `/`

**Sync Mechanism**:
1. User selects language in UI (SvelteKit component)
2. SvelteKit sets cookie and switches locale
3. Cookie sent to Django on next API request
4. Django activates language based on cookie
5. API responses use selected language

### Date/Time Formatting

**Approach**: Use locale-aware libraries on both sides

- **Django**: `django.utils.formats.date_format()` with `USE_L10N=True`
- **SvelteKit**: JavaScript `Intl.DateTimeFormat()` or `date-fns` with locale

**Swedish Format Examples**:
- Date: `2025-11-25` (ISO format)
- Time: `14:30`
- DateTime: `2025-11-25 14:30`

---

## 3. Backend Translation Requirements

### 3.1 Django Configuration Changes

**File: `backend/config/settings/base.py`**

Add after line 109:
```python
# Internationalization
LANGUAGE_CODE = "en"  # Default language
TIME_ZONE = "Europe/Stockholm"  # For Swedish conferences

USE_I18N = True
USE_L10N = True  # Locale-aware formatting
USE_TZ = True

# Supported languages
LANGUAGES = [
    ("en", "English"),
    ("sv", "Swedish"),
]

# Translation file paths
LOCALE_PATHS = [
    BASE_DIR / "locale",
]
```

**File: `backend/config/settings/base.py` - MIDDLEWARE**

Add `LocaleMiddleware` after line 44 (after SessionMiddleware):
```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",  # ADD THIS
    "corsheaders.middleware.CorsMiddleware",
    # ... rest
]
```

### 3.2 Translation Files Structure

Create directory structure:
```
backend/
└── locale/
    ├── en/
    │   └── LC_MESSAGES/
    │       ├── django.po
    │       └── django.mo (compiled)
    └── sv/
        └── LC_MESSAGES/
            ├── django.po
            └── django.mo (compiled)
```

### 3.3 Backend Strings to Translate

#### API Error Messages (`checkins/views.py`)

| Line | English String | Context |
|------|---------------|---------|
| 42 | "Both child and session are required" | Check-in validation |
| 51 | "Child or session not found" | Check-in validation |
| 62 | "Child is already checked in to this session" | Check-in validation |
| 125 | "Child is already checked out" | Check-out validation |

**Swedish Translations**:
```python
# Line 42
{"error": _("Both child and session are required")}
# Swedish: "Både barn och session krävs"

# Line 51
{"error": _("Child or session not found")}
# Swedish: "Barn eller session hittades inte"

# Line 62
{"error": _("Child is already checked in to this session")}
# Swedish: "Barnet är redan incheckad till denna session"

# Line 125
{"error": _("Child is already checked out")}
# Swedish: "Barnet är redan utcheckad"
```

#### Authentication Messages (`accounts/views.py`)

| Line | English String | Context |
|------|---------------|---------|
| 58 | "Username and password are required" | Login validation |
| 76 | "Invalid credentials" | Login error |

**Swedish Translations**:
```python
# Line 58
{"error": _("Username and password are required")}
# Swedish: "Användarnamn och lösenord krävs"

# Line 76
{"error": _("Invalid credentials")}
# Swedish: "Ogiltiga inloggningsuppgifter"
```

#### QR Code Messages (`families/qr_views.py`)

| Line | English String | Context |
|------|---------------|---------|
| 29 | "Invalid QR code" | QR lookup error |

**Swedish Translation**:
```python
# Line 29
{"error": _("Invalid QR code")}
# Swedish: "Ogiltig QR-kod"
```

#### Serializer Validation (`checkins/serializers.py`)

| Line | English String | Context |
|------|---------------|---------|
| 48 | "This child is already checked in to this session." | Validation error |

**Swedish Translation**:
```python
# Line 48
raise serializers.ValidationError(
    _("This child is already checked in to this session.")
)
# Swedish: "Detta barn är redan incheckad till denna session."
```

#### Model Choices (`events/models.py`)

| Line | Choices | Context |
|------|---------|---------|
| 45-47 | "Event Pass", "Session Ticket", "None" | Ticket types |

**Swedish Translations**:
```python
TICKET_TYPES = [
    (EVENT_PASS, _("Event Pass")),      # "Evenemangskort"
    (SESSION_TICKET, _("Session Ticket")),  # "Sessionsbiljett"
    (NONE, _("None")),                  # "Ingen"
]
```

### 3.4 Django Admin Interface

Django admin already has Swedish translations built-in. To activate:

1. Install Swedish translation package (included in Django)
2. User selects language in browser or via Django admin language selector
3. Admin interface automatically switches to Swedish

**Custom Model Labels** - Add to models:

**families/models.py**:
```python
class Parent(models.Model):
    name = models.CharField(max_length=255, verbose_name=_("Name"))
    phone = models.CharField(max_length=50, null=True, blank=True, verbose_name=_("Phone"))
    email = models.EmailField(null=True, blank=True, verbose_name=_("Email"))
    relationship_type = models.CharField(max_length=64, verbose_name=_("Relationship Type"))
    
    class Meta:
        verbose_name = _("Parent")
        verbose_name_plural = _("Parents")
```

**Swedish Translations**:
- Name → "Namn"
- Phone → "Telefon"
- Email → "E-post"
- Relationship Type → "Relation"
- Parent → "Förälder"
- Parents → "Föräldrar"

---

## 4. Frontend Translation Requirements

### 4.1 SvelteKit i18n Setup

**File: `frontend/src/lib/i18n.ts`** (NEW FILE)

```typescript
import { register, init, getLocaleFromNavigator } from 'svelte-i18n';

// Register translation files
register('en', () => import('./locales/en.json'));
register('sv', () => import('./locales/sv.json'));

// Initialize with browser locale or default to English
init({
  fallbackLocale: 'en',
  initialLocale: getLocaleFromNavigator(),
});
```

**File: `frontend/src/routes/+layout.svelte`** (MODIFY)

Add i18n initialization:
```svelte
<script lang="ts">
  import '../lib/i18n';  // Initialize i18n
  import { locale, t } from 'svelte-i18n';
  // ... rest of imports
</script>
```

### 4.2 Translation Files Structure

Create directory structure:
```
frontend/src/lib/
└── locales/
    ├── en.json
    └── sv.json
```

### 4.3 Frontend Strings to Translate

#### Navigation (`+layout.svelte`)

| Line | English String | Translation Key | Swedish |
|------|---------------|----------------|---------|
| 15 | "Check-In System" | `nav.title` | "Incheckningssystem" |
| 18 | "Welcome" | `nav.welcome` | "Välkommen" |
| 19 | "Check-In" | `nav.checkin` | "Incheckning" |
| 20 | "Check-Out" | `nav.checkout` | "Utcheckning" |
| 21 | "Logout" | `nav.logout` | "Logga ut" |

**en.json**:
```json
{
  "nav": {
    "title": "Check-In System",
    "welcome": "Welcome, {username}",
    "checkin": "Check-In",
    "checkout": "Check-Out",
    "logout": "Logout"
  }
}
```

**sv.json**:
```json
{
  "nav": {
    "title": "Incheckningssystem",
    "welcome": "Välkommen, {username}",
    "checkin": "Incheckning",
    "checkout": "Utcheckning",
    "logout": "Logga ut"
  }
}
```

**Updated +layout.svelte**:
```svelte
<a href="/" class="text-xl font-bold">{$t('nav.title')}</a>
<span>{$t('nav.welcome', { values: { username: data.user.username } })}</span>
<a href="/checkin">{$t('nav.checkin')}</a>
<a href="/checkout">{$t('nav.checkout')}</a>
<a href="/logout">{$t('nav.logout')}</a>
```

#### Login Page (`login/+page.svelte`)

| Line | English String | Translation Key | Swedish |
|------|---------------|----------------|---------|
| 52 | "Login - Check-In System" | `login.pageTitle` | "Logga in - Incheckningssystem" |
| 57 | "Check-In System Login" | `login.title` | "Logga in till incheckningssystemet" |
| 61 | "Login successful! Redirecting..." | `login.success` | "Inloggning lyckades! Omdirigerar..." |
| 71 | "Username" | `login.username` | "Användarnamn" |
| 80 | "Enter your username" | `login.usernamePlaceholder` | "Ange ditt användarnamn" |
| 85 | "Password" | `login.password` | "Lösenord" |
| 94 | "Enter your password" | `login.passwordPlaceholder` | "Ange ditt lösenord" |
| 103 | "Login" | `login.submit` | "Logga in" |

**en.json addition**:
```json
{
  "login": {
    "pageTitle": "Login - Check-In System",
    "title": "Check-In System Login",
    "success": "Login successful! Redirecting...",
    "username": "Username",
    "usernamePlaceholder": "Enter your username",
    "password": "Password",
    "passwordPlaceholder": "Enter your password",
    "submit": "Login"
  }
}
```

**sv.json addition**:
```json
{
  "login": {
    "pageTitle": "Logga in - Incheckningssystem",
    "title": "Logga in till incheckningssystemet",
    "success": "Inloggning lyckades! Omdirigerar...",
    "username": "Användarnamn",
    "usernamePlaceholder": "Ange ditt användarnamn",
    "password": "Lösenord",
    "passwordPlaceholder": "Ange ditt lösenord",
    "submit": "Logga in"
  }
}
```

#### Check-In Page (`checkin/+page.svelte`)

| Line | English String | Translation Key | Swedish |
|------|---------------|----------------|---------|
| 142 | "Check-In Station" | `checkin.pageTitle` | "Incheckningsstation" |
| 146 | "Check-In Station" | `checkin.title` | "Incheckningsstation" |
| 149 | "WebSocket Status" | `checkin.wsStatus` | "WebSocket-status" |
| 157 | "Connected" | `checkin.connected` | "Ansluten" |
| 157 | "Disconnected" | `checkin.disconnected` | "Frånkopplad" |
| 176 | "Select Session" | `checkin.selectSession` | "Välj session" |
| 182 | "-- Select a session --" | `checkin.selectSessionPlaceholder` | "-- Välj en session --" |
| 191 | "Search Family" | `checkin.searchFamily` | "Sök familj" |
| 197 | "Search by family name, email, or phone..." | `checkin.searchPlaceholder` | "Sök efter familjenamn, e-post eller telefon..." |
| 206 | "Search" | `checkin.searchButton` | "Sök" |
| 233 | "Select Children" | `checkin.selectChildren` | "Välj barn" |
| 235 | "No children found for this family." | `checkin.noChildren` | "Inga barn hittades för denna familj." |
| 252 | "DOB:" | `checkin.dob` | "Födelsedatum:" |
| 270 | "Checking in..." | `checkin.checkingIn` | "Checkar in..." |
| 270 | "Check In {count} Child(ren)" | `checkin.checkInButton` | "Checka in {count} barn" |
| 103 | "Please select a session and at least one child" | `checkin.selectError` | "Välj en session och minst ett barn" |
| 119 | "Successfully checked in {count} child(ren)" | `checkin.successMessage` | "Checkade in {count} barn" |
| 134 | "Check-in failed" | `checkin.error` | "Incheckning misslyckades" |
| 52 | "Failed to load sessions" | `checkin.sessionsError` | "Kunde inte ladda sessioner" |
| 69 | "Search failed" | `checkin.searchError` | "Sökning misslyckades" |
| 86 | "Failed to load children" | `checkin.childrenError` | "Kunde inte ladda barn" |

#### Check-Out Page (`checkout/+page.svelte`)

| Line | English String | Translation Key | Swedish |
|------|---------------|----------------|---------|
| 86 | "Check-Out Station" | `checkout.pageTitle` | "Utcheckningsstation" |
| 90 | "Check-Out Station" | `checkout.title` | "Utcheckningsstation" |
| 93 | "WebSocket Status" | `checkout.wsStatus` | "WebSocket-status" |
| 101 | "Connected" | `checkout.connected` | "Ansluten" |
| 101 | "Disconnected" | `checkout.disconnected` | "Frånkopplad" |
| 119 | "Currently Checked In" | `checkout.currentlyCheckedIn` | "För närvarande incheckade" |
| 123 | "Loading..." | `checkout.loading` | "Laddar..." |
| 127 | "No children currently checked in." | `checkout.noChildren` | "Inga barn är för närvarande incheckade." |
| 135 | "Child ID:" | `checkout.childId` | "Barn-ID:" |
| 137 | "Session:" | `checkout.session` | "Session:" |
| 140 | "Checked in:" | `checkout.checkedIn` | "Incheckad:" |
| 144 | "Notes:" | `checkout.notes` | "Anteckningar:" |
| 153 | "Picked up by..." | `checkout.pickedUpByPlaceholder` | "Hämtas av..." |
| 162 | "Checking out..." | `checkout.checkingOut` | "Checkar ut..." |
| 162 | "Check Out" | `checkout.checkOutButton` | "Checka ut" |
| 174 | "Refreshing..." | `checkout.refreshing` | "Uppdaterar..." |
| 174 | "Refresh" | `checkout.refreshButton` | "Uppdatera" |
| 64 | "Successfully checked out" | `checkout.success` | "Utcheckning lyckades" |
| 78 | "Check-out failed" | `checkout.error` | "Utcheckning misslyckades" |
| 50 | "Failed to load active check-ins" | `checkout.loadError` | "Kunde inte ladda aktiva incheckningar" |

#### QR Page (`qr/[token]/+page.svelte`)

| Line | English String | Translation Key | Swedish |
|------|---------------|----------------|---------|
| 40 | "Child Information" | `qr.pageTitle` | "Barninformation" |
| 47 | "Loading..." | `qr.loading` | "Laddar..." |
| 54 | "Child not found" | `qr.notFound` | "Barn hittades inte" |
| 57 | "Please check the QR code or contact staff for assistance." | `qr.notFoundHelp` | "Kontrollera QR-koden eller kontakta personal för hjälp." |
| 63 | "Child Information" | `qr.title` | "Barninformation" |
| 67 | "Name" | `qr.name` | "Namn" |
| 75 | "Date of Birth" | `qr.dateOfBirth` | "Födelsedatum" |
| 82 | "Allergies" | `qr.allergies` | "Allergier" |
| 89 | "Medical Conditions" | `qr.medicalConditions` | "Medicinska tillstånd" |
| 99 | "Special Needs" | `qr.specialNeeds` | "Särskilda behov" |
| 107 | "Check-In Status" | `qr.checkInStatus` | "Incheckningsstatus" |
| 113 | "Currently Checked In" | `qr.currentlyCheckedIn` | "För närvarande incheckad" |
| 116 | "Session:" | `qr.session` | "Session:" |
| 119 | "Since:" | `qr.since` | "Sedan:" |
| 126 | "Not Currently Checked In" | `qr.notCheckedIn` | "Ej incheckad" |
| 133 | "Emergency Contact" | `qr.emergencyContact` | "Nödkontakt" |
| 135 | "For emergency contact information, please see a staff member." | `qr.emergencyContactHelp` | "För nödkontaktinformation, kontakta en personalmedlem." |
| 137 | "Family ID:" | `qr.familyId` | "Familje-ID:" |

### 4.4 Language Switcher Component

**File: `frontend/src/lib/components/LanguageSwitcher.svelte`** (NEW FILE)

```svelte
<script lang="ts">
  import { locale } from 'svelte-i18n';
  
  const languages = [
    { code: 'en', label: 'English' },
    { code: 'sv', label: 'Svenska' }
  ];
  
  function setLanguage(lang: string) {
    locale.set(lang);
    // Save to cookie for Django backend
    document.cookie = `django_language=${lang}; path=/; SameSite=Lax`;
  }
</script>

<div class="language-switcher">
  {#each languages as lang}
    <button
      onclick={() => setLanguage(lang.code)}
      class:active={$locale === lang.code}
    >
      {lang.label}
    </button>
  {/each}
</div>
```

**Add to `+layout.svelte`** navigation:
```svelte
<div class="flex items-center gap-4">
  <LanguageSwitcher />
  <span>{$t('nav.welcome', { values: { username: data.user.username } })}</span>
  <!-- ... rest of nav -->
</div>
```

---

## 5. Implementation Roadmap

### Phase 1: Backend Setup (2-3 hours)

**Tasks**:
1. ✅ Update `settings/base.py` with i18n configuration
2. ✅ Add `LocaleMiddleware` to middleware stack
3. ✅ Create `locale/` directory structure
4. ✅ Generate translation files: `python manage.py makemessages -l sv`
5. ✅ Wrap all strings in views with `gettext()` / `_()`
6. ✅ Add `verbose_name` to model fields
7. ✅ Update choices in models with `_()`
8. ✅ Translate strings in `.po` files
9. ✅ Compile translations: `python manage.py compilemessages`
10. ✅ Test Django admin in Swedish

**Commands**:
```bash
cd backend

# Create locale directory
mkdir -p locale

# Generate English template
python manage.py makemessages -l en

# Generate Swedish translations
python manage.py makemessages -l sv

# After editing .po files, compile
python manage.py compilemessages

# Run server and test
python manage.py runserver
```

### Phase 2: Frontend Setup (3-4 hours)

**Tasks**:
1. ✅ Create `frontend/src/lib/i18n.ts` initialization file
2. ✅ Create `frontend/src/lib/locales/en.json`
3. ✅ Create `frontend/src/lib/locales/sv.json`
4. ✅ Translate all frontend strings (see section 4.3)
5. ✅ Create `LanguageSwitcher` component
6. ✅ Update `+layout.svelte` with i18n import and switcher
7. ✅ Update all `.svelte` files to use `$t()` function
8. ✅ Test language switching in browser
9. ✅ Verify cookie is set correctly

**Test Checklist**:
- [ ] Login page displays in Swedish
- [ ] Navigation switches language
- [ ] Check-in page fully translated
- [ ] Check-out page fully translated
- [ ] QR page fully translated
- [ ] Error messages display in selected language
- [ ] Date/time formats correct for locale

### Phase 3: Integration & Testing (2 hours)

**Tasks**:
1. ✅ Test language cookie sync between frontend and backend
2. ✅ Verify API errors return in selected language
3. ✅ Test date/time formatting in both languages
4. ✅ Test with real data (check-in/check-out flows)
5. ✅ Browser testing (Chrome, Firefox, Safari)
6. ✅ Mobile responsive testing
7. ✅ Document language selection in user guide

### Phase 4: Production Deployment (1 hour)

**Tasks**:
1. ✅ Add compiled `.mo` files to Git (`.po` files too)
2. ✅ Update Docker build to include locale files
3. ✅ Set default language via environment variable
4. ✅ Test production build
5. ✅ Deploy to staging
6. ✅ Final QA testing
7. ✅ Deploy to production

**Total Estimated Time**: 8-10 hours

---

## 6. File-by-File Analysis

### Backend Files Requiring Changes

#### High Priority (User-Facing Strings)

1. **`backend/config/settings/base.py`**
   - Lines to modify: 106-109
   - Add: LANGUAGES, LOCALE_PATHS
   - Add middleware: LocaleMiddleware

2. **`backend/checkins/views.py`**
   - Lines: 42, 51, 62, 125
   - Wrap error messages with `_()`
   - Import: `from django.utils.translation import gettext as _`

3. **`backend/accounts/views.py`**
   - Lines: 58, 76
   - Wrap error messages with `_()`
   - Import: `from django.utils.translation import gettext as _`

4. **`backend/families/qr_views.py`**
   - Line: 29
   - Wrap error message with `_()`
   - Import: `from django.utils.translation import gettext as _`

5. **`backend/checkins/serializers.py`**
   - Line: 48
   - Wrap validation error with `_()`
   - Import: `from django.utils.translation import gettext as _`

6. **`backend/events/models.py`**
   - Lines: 45-47 (TICKET_TYPES)
   - Wrap choice labels with `_()`
   - Import: `from django.utils.translation import gettext_lazy as _`

#### Medium Priority (Model Labels)

7. **`backend/families/models.py`**
   - Add `verbose_name` to all fields
   - Add `verbose_name` and `verbose_name_plural` to Meta

8. **`backend/events/models.py`**
   - Add `verbose_name` to all fields
   - Add `verbose_name` and `verbose_name_plural` to Meta

9. **`backend/checkins/models.py`**
   - Add `verbose_name` to all fields
   - Add `verbose_name` and `verbose_name_plural` to Meta

10. **`backend/accounts/models.py`**
    - Already has verbose_name (lines 47-48)
    - No changes needed

#### Low Priority (Admin Customization)

11. **`backend/families/admin.py`**
    - Add custom list_display labels if needed
    - Django admin auto-translates based on verbose_name

12. **`backend/events/admin.py`**
    - No changes needed (uses verbose_name)

13. **`backend/checkins/admin.py`**
    - No changes needed (uses verbose_name)

### Frontend Files Requiring Changes

#### High Priority (User-Facing Pages)

1. **`frontend/src/lib/i18n.ts`** (NEW FILE)
   - Initialize svelte-i18n
   - Register locales

2. **`frontend/src/lib/locales/en.json`** (NEW FILE)
   - All English translations
   - ~60 translation keys

3. **`frontend/src/lib/locales/sv.json`** (NEW FILE)
   - All Swedish translations
   - ~60 translation keys

4. **`frontend/src/lib/components/LanguageSwitcher.svelte`** (NEW FILE)
   - Language selection component
   - Cookie setter

5. **`frontend/src/routes/+layout.svelte`**
   - Lines: 15, 18, 19, 20, 21
   - Import i18n and $t function
   - Add LanguageSwitcher component

6. **`frontend/src/routes/login/+page.svelte`**
   - Lines: 52, 57, 61, 71, 80, 85, 94, 103
   - Replace all strings with `$t()` calls

7. **`frontend/src/routes/checkin/+page.svelte`**
   - Lines: Multiple (see section 4.3)
   - Replace all strings with `$t()` calls

8. **`frontend/src/routes/checkout/+page.svelte`**
   - Lines: Multiple (see section 4.3)
   - Replace all strings with `$t()` calls

9. **`frontend/src/routes/qr/[token]/+page.svelte`**
   - Lines: Multiple (see section 4.3)
   - Replace all strings with `$t()` calls

#### Medium Priority (Error Messages)

10. **`frontend/src/lib/stores/auth.ts`**
    - Lines: 56, 91
    - Console errors (low priority)
    - Consider translating user-facing errors

11. **`frontend/src/routes/login/+page.server.ts`**
    - Lines: 19, 58, 64, 153
    - Server-side errors
    - Return error keys instead of strings

---

## 7. Complete Translation Dictionary

### Backend Translation Keys

#### Error Messages
```python
# checkins/views.py
_("Both child and session are required")
_("Child or session not found")
_("Child is already checked in to this session")
_("Child is already checked out")

# accounts/views.py
_("Username and password are required")
_("Invalid credentials")

# families/qr_views.py
_("Invalid QR code")

# checkins/serializers.py
_("This child is already checked in to this session.")
```

#### Model Choices
```python
# events/models.py
_("Event Pass")
_("Session Ticket")
_("None")
```

#### Model Field Labels
```python
# families/models.py - Parent
_("Name")
_("Phone")
_("Email")
_("Relationship Type")
_("Last Participation Date")
_("Parent")
_("Parents")

# families/models.py - Child
_("First Name")
_("Last Name")
_("Birthdate")
_("Allergies")
_("Notes")
_("QR Token")
_("Child")
_("Children")

# events/models.py - Event
_("Event Name")
_("Start Date")
_("End Date")
_("Event")
_("Events")

# events/models.py - Session
_("Session Name")
_("Start Time")
_("End Time")
_("Is Active")
_("Requires Ticket")
_("Session")
_("Sessions")

# checkins/models.py
_("Check-In Time")
_("Check-Out Time")
_("Picked Up By")
_("Check-In Staff")
_("Check-Out Staff")
_("Check-In Record")
_("Check-In Records")
```

### Frontend Translation Keys (JSON)

Complete `en.json`:
```json
{
  "nav": {
    "title": "Check-In System",
    "welcome": "Welcome, {username}",
    "checkin": "Check-In",
    "checkout": "Check-Out",
    "logout": "Logout"
  },
  "login": {
    "pageTitle": "Login - Check-In System",
    "title": "Check-In System Login",
    "success": "Login successful! Redirecting...",
    "username": "Username",
    "usernamePlaceholder": "Enter your username",
    "password": "Password",
    "passwordPlaceholder": "Enter your password",
    "submit": "Login"
  },
  "checkin": {
    "pageTitle": "Check-In Station",
    "title": "Check-In Station",
    "wsStatus": "WebSocket Status",
    "connected": "Connected",
    "disconnected": "Disconnected",
    "selectSession": "Select Session",
    "selectSessionPlaceholder": "-- Select a session --",
    "searchFamily": "Search Family",
    "searchPlaceholder": "Search by family name, email, or phone...",
    "searchButton": "Search",
    "selectChildren": "Select Children",
    "noChildren": "No children found for this family.",
    "dob": "DOB:",
    "checkingIn": "Checking in...",
    "checkInButton": "Check In {count} Child(ren)",
    "selectError": "Please select a session and at least one child",
    "successMessage": "Successfully checked in {count} child(ren)",
    "error": "Check-in failed",
    "sessionsError": "Failed to load sessions",
    "searchError": "Search failed",
    "childrenError": "Failed to load children"
  },
  "checkout": {
    "pageTitle": "Check-Out Station",
    "title": "Check-Out Station",
    "wsStatus": "WebSocket Status",
    "connected": "Connected",
    "disconnected": "Disconnected",
    "currentlyCheckedIn": "Currently Checked In",
    "loading": "Loading...",
    "noChildren": "No children currently checked in.",
    "childId": "Child ID:",
    "session": "Session:",
    "checkedIn": "Checked in:",
    "notes": "Notes:",
    "pickedUpByPlaceholder": "Picked up by...",
    "checkingOut": "Checking out...",
    "checkOutButton": "Check Out",
    "refreshing": "Refreshing...",
    "refreshButton": "Refresh",
    "success": "Successfully checked out",
    "error": "Check-out failed",
    "loadError": "Failed to load active check-ins"
  },
  "qr": {
    "pageTitle": "Child Information",
    "title": "Child Information",
    "loading": "Loading...",
    "notFound": "Child not found",
    "notFoundHelp": "Please check the QR code or contact staff for assistance.",
    "name": "Name",
    "dateOfBirth": "Date of Birth",
    "allergies": "Allergies",
    "medicalConditions": "Medical Conditions",
    "specialNeeds": "Special Needs",
    "checkInStatus": "Check-In Status",
    "currentlyCheckedIn": "Currently Checked In",
    "session": "Session:",
    "since": "Since:",
    "notCheckedIn": "Not Currently Checked In",
    "emergencyContact": "Emergency Contact",
    "emergencyContactHelp": "For emergency contact information, please see a staff member.",
    "familyId": "Family ID:"
  }
}
```

Complete `sv.json`:
```json
{
  "nav": {
    "title": "Incheckningssystem",
    "welcome": "Välkommen, {username}",
    "checkin": "Incheckning",
    "checkout": "Utcheckning",
    "logout": "Logga ut"
  },
  "login": {
    "pageTitle": "Logga in - Incheckningssystem",
    "title": "Logga in till incheckningssystemet",
    "success": "Inloggning lyckades! Omdirigerar...",
    "username": "Användarnamn",
    "usernamePlaceholder": "Ange ditt användarnamn",
    "password": "Lösenord",
    "passwordPlaceholder": "Ange ditt lösenord",
    "submit": "Logga in"
  },
  "checkin": {
    "pageTitle": "Incheckningsstation",
    "title": "Incheckningsstation",
    "wsStatus": "WebSocket-status",
    "connected": "Ansluten",
    "disconnected": "Frånkopplad",
    "selectSession": "Välj session",
    "selectSessionPlaceholder": "-- Välj en session --",
    "searchFamily": "Sök familj",
    "searchPlaceholder": "Sök efter familjenamn, e-post eller telefon...",
    "searchButton": "Sök",
    "selectChildren": "Välj barn",
    "noChildren": "Inga barn hittades för denna familj.",
    "dob": "Födelsedatum:",
    "checkingIn": "Checkar in...",
    "checkInButton": "Checka in {count} barn",
    "selectError": "Välj en session och minst ett barn",
    "successMessage": "Checkade in {count} barn",
    "error": "Incheckning misslyckades",
    "sessionsError": "Kunde inte ladda sessioner",
    "searchError": "Sökning misslyckades",
    "childrenError": "Kunde inte ladda barn"
  },
  "checkout": {
    "pageTitle": "Utcheckningsstation",
    "title": "Utcheckningsstation",
    "wsStatus": "WebSocket-status",
    "connected": "Ansluten",
    "disconnected": "Frånkopplad",
    "currentlyCheckedIn": "För närvarande incheckade",
    "loading": "Laddar...",
    "noChildren": "Inga barn är för närvarande incheckade.",
    "childId": "Barn-ID:",
    "session": "Session:",
    "checkedIn": "Incheckad:",
    "notes": "Anteckningar:",
    "pickedUpByPlaceholder": "Hämtas av...",
    "checkingOut": "Checkar ut...",
    "checkOutButton": "Checka ut",
    "refreshing": "Uppdaterar...",
    "refreshButton": "Uppdatera",
    "success": "Utcheckning lyckades",
    "error": "Utcheckning misslyckades",
    "loadError": "Kunde inte ladda aktiva incheckningar"
  },
  "qr": {
    "pageTitle": "Barninformation",
    "title": "Barninformation",
    "loading": "Laddar...",
    "notFound": "Barn hittades inte",
    "notFoundHelp": "Kontrollera QR-koden eller kontakta personal för hjälp.",
    "name": "Namn",
    "dateOfBirth": "Födelsedatum",
    "allergies": "Allergier",
    "medicalConditions": "Medicinska tillstånd",
    "specialNeeds": "Särskilda behov",
    "checkInStatus": "Incheckningsstatus",
    "currentlyCheckedIn": "För närvarande incheckad",
    "session": "Session:",
    "since": "Sedan:",
    "notCheckedIn": "Ej incheckad",
    "emergencyContact": "Nödkontakt",
    "emergencyContactHelp": "För nödkontaktinformation, kontakta en personalmedlem.",
    "familyId": "Familje-ID:"
  }
}
```

---

## 8. Testing Checklist

### Backend Testing

- [ ] Django admin displays in Swedish when language selected
- [ ] API error messages return in Swedish when `Accept-Language: sv` header sent
- [ ] Cookie `django_language=sv` changes API response language
- [ ] Date formats use Swedish locale (YYYY-MM-DD)
- [ ] Model verbose names display in Swedish in admin
- [ ] Choices (ticket types) display in Swedish

### Frontend Testing

- [ ] Language switcher toggles between English and Swedish
- [ ] Cookie is set when language changed
- [ ] All navigation items translate correctly
- [ ] Login page fully functional in Swedish
- [ ] Check-in page fully functional in Swedish
- [ ] Check-out page fully functional in Swedish
- [ ] QR page fully functional in Swedish
- [ ] Error messages display in selected language
- [ ] Success messages display in selected language
- [ ] Pluralization works correctly (e.g., "1 barn" vs "2 barn")
- [ ] Date/time displays use Swedish format
- [ ] Browser refresh maintains selected language
- [ ] Mobile responsive design works in both languages

### Integration Testing

- [ ] Login in Swedish → API responses in Swedish
- [ ] Language persists across page navigation
- [ ] WebSocket messages don't break with Swedish text
- [ ] Form validation errors display in selected language
- [ ] PDF/QR code generation works with Swedish text (if applicable)

---

## 9. Deployment Notes

### Environment Variables

Add to `.env`:
```bash
# Default language for the application
LANGUAGE_CODE=en

# Supported languages
LANGUAGES=en,sv

# Timezone (Sweden)
TIME_ZONE=Europe/Stockholm
```

### Docker Build

Ensure `locale/` directory is included:

**backend/Dockerfile**:
```dockerfile
# Copy Django locale files
COPY backend/locale /app/locale

# Compile translation files during build
RUN python manage.py compilemessages
```

### Git Repository

**Include in version control**:
- `backend/locale/en/LC_MESSAGES/django.po`
- `backend/locale/sv/LC_MESSAGES/django.po`
- `backend/locale/en/LC_MESSAGES/django.mo`
- `backend/locale/sv/LC_MESSAGES/django.mo`
- `frontend/src/lib/locales/en.json`
- `frontend/src/lib/locales/sv.json`

**Update `.gitignore` if needed** (remove `*.mo` if present):
```gitignore
# Don't ignore compiled translation files
!locale/**/*.mo
```

---

## 10. Future Enhancements

### Additional Languages

To add more languages (e.g., Norwegian, Danish):

1. Add to `LANGUAGES` in settings
2. Run `python manage.py makemessages -l no`
3. Translate `.po` file
4. Create `frontend/src/lib/locales/no.json`
5. Register in `i18n.ts`

### Right-to-Left (RTL) Support

For Arabic or Hebrew:
- Update CSS with RTL directives
- Use `dir="rtl"` attribute conditionally
- Mirror layouts for RTL languages

### Professional Translation Review

Current translations are machine/AI-assisted. For production:
- Hire professional Swedish translator
- Review all strings for context and accuracy
- Test with native Swedish speakers
- Consider regional variations (Sweden vs Finland Swedish)

---

## 11. Resources

### Django i18n Documentation
- https://docs.djangoproject.com/en/5.0/topics/i18n/
- https://docs.djangoproject.com/en/5.0/topics/i18n/translation/

### svelte-i18n Documentation
- https://github.com/kaisermann/svelte-i18n
- https://github.com/kaisermann/svelte-i18n/blob/main/docs/Getting%20Started.md

### Translation Tools
- Poedit (for `.po` files): https://poedit.net/
- Online JSON editor: https://jsoneditoronline.org/

### Swedish Language Resources
- Swedish Language Council: https://www.isof.se/
- Swedish locale data: https://github.com/unicode-org/cldr/tree/main/common/main

---

**End of Report**

*Generated: 2025-11-25*  
*Last Updated: 2025-11-25*  
*Version: 1.0*
