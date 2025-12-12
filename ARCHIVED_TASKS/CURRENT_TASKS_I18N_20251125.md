# Current Tasks - i18n Implementation (Swedish & English)

## Overview
Implement comprehensive internationalization support for Swedish and English across the Django backend and SvelteKit frontend. See `I18N_IMPLEMENTATION_PLAN.md` for complete details.

## Phase 1: Backend i18n Setup (Django)
**Goal**: Configure Django for Swedish/English translations

### 1.1 Django Configuration
- [x] Update `backend/config/settings/base.py`:
  - [x] Add `LANGUAGE_CODE = 'en'`
  - [x] Add `LANGUAGES = [('en', 'English'), ('sv', 'Swedish')]`
  - [x] Add `LOCALE_PATHS = [BASE_DIR / 'locale']`
  - [x] Ensure `USE_I18N = True` and `USE_L10N = True`
  - [x] Add `LocaleMiddleware` to MIDDLEWARE
- [x] Create `backend/locale/` directory structure

### 1.2 Model Translations
- [x] Add `verbose_name` and `verbose_name_plural` to all models:
  - [x] `families/models.py` - Family, Parent
  - [x] `children/models.py` - Child
  - [x] `events/models.py` - Event, Session
  - [x] `checkins/models.py` - CheckIn
  - [x] `accounts/models.py` - AdminUser (already had verbose_name)
- [x] Translate `TicketType` choices in `events/models.py:45-47`

### 1.3 View/API Translations
- [x] Update `checkins/views.py`:
  - [x] Line 43: "Both child and session are required" error
  - [x] Line 52: "Child or session not found" error
  - [x] Line 63: "Child is already checked in to this session" error
  - [x] Line 126: "Child is already checked out" error
- [x] Update `accounts/views.py`:
  - [x] Line 59: "Username and password are required" error
  - [x] Line 77: "Invalid credentials" error
- [x] Update `families/qr_views.py`:
  - [x] Line 30: "Invalid QR code" error
- [x] Update `checkins/serializers.py`:
  - [x] Line 49: Validation error message

### 1.4 Generate Translation Files
- [x] Create `backend/locale/en/LC_MESSAGES/django.po`
- [x] Create `backend/locale/sv/LC_MESSAGES/django.po` with Swedish translations
- [ ] Test backend API returns Swedish errors when language cookie is 'sv' (requires testing)

## Phase 2: Frontend i18n Setup (SvelteKit)
**Goal**: Configure SvelteKit with svelte-i18n for Swedish/English

### 2.1 Core i18n Infrastructure
- [x] Create `frontend/src/lib/i18n/i18n.ts` with svelte-i18n configuration
- [x] Create translation files:
  - [x] `frontend/src/lib/i18n/locales/en.json` (60+ keys)
  - [x] `frontend/src/lib/i18n/locales/sv.json` (60+ keys)
- [x] Create `frontend/src/lib/components/LanguageSwitcher.svelte`
- [x] Initialize i18n in `frontend/src/routes/+layout.svelte`
- [x] Set up language cookie synchronization with Django

### 2.2 Layout & Navigation
- [x] Update `frontend/src/routes/+layout.svelte`:
  - [x] Line 18: "Check-In System" → `$t('nav.title')`
  - [x] Line 22: "Welcome" → `$t('nav.welcome')`
  - [x] Line 23: "Check-In" → `$t('nav.checkin')`
  - [x] Line 24: "Check-Out" → `$t('nav.checkout')`
  - [x] Line 25: "Logout" → `$t('nav.logout')`
  - [x] Add LanguageSwitcher component

### 2.3 Login Page
- [x] Update `frontend/src/routes/login/+page.svelte`:
  - [x] Line 53: Page title → `$t('login.pageTitle')`
  - [x] Line 58: "Check-In System Login" → `$t('login.title')`
  - [x] Line 62: Success message → `$t('login.success')`
  - [x] Line 73: "Username" label → `$t('login.username')`
  - [x] Line 81: Username placeholder → `$t('login.usernamePlaceholder')`
  - [x] Line 87: "Password" label → `$t('login.password')`
  - [x] Line 95: Password placeholder → `$t('login.passwordPlaceholder')`
  - [x] Line 104: "Login" button → `$t('login.submit')`

### 2.4 Check-In Page
- [x] Update `frontend/src/routes/checkin/+page.svelte`:
  - [x] Page title and heading
  - [x] WebSocket status
  - [x] Session selector label and prompt
  - [x] Search label and placeholder
  - [x] Search button
  - [x] Status messages (searching, no results, error)
  - [x] Child selection UI
  - [x] Check-in button
  - [x] Success/error notifications
  - [x] All translatable strings

### 2.5 Check-Out Page
- [x] Update `frontend/src/routes/checkout/+page.svelte`:
  - [x] Page title and heading
  - [x] WebSocket status
  - [x] Currently checked-in children section
  - [x] Child display fields
  - [x] Pickup person field
  - [x] Check-out button
  - [x] Refresh button
  - [x] Success/error notifications
  - [x] All translatable strings

### 2.6 QR Info Page
- [x] Update `frontend/src/routes/qr/[token]/+page.svelte`:
  - [x] Page title
  - [x] Child information labels
  - [x] Status indicators
  - [x] Emergency contact section
  - [x] Error states
  - [x] All translatable strings

## Phase 3: Integration & Testing
**Goal**: Ensure language selection works seamlessly across Django and SvelteKit

### 3.1 Language Cookie Synchronization
- [ ] Verify `django_language` cookie is set correctly
- [ ] Test language switcher updates Django backend
- [ ] Test language preference persists across sessions
- [ ] Verify cookie path and domain settings

### 3.2 API Response Testing
- [ ] Test Django API errors return Swedish when `django_language=sv`
- [ ] Test English is default when cookie is missing
- [ ] Test validation messages in both languages
- [ ] Test model verbose names in admin (if applicable)

### 3.3 Frontend Flow Testing
- [ ] Test complete login flow in Swedish
- [ ] Test complete check-in flow in Swedish
- [ ] Test complete check-out flow in Swedish
- [ ] Test QR info page in Swedish
- [ ] Test language switching mid-session
- [ ] Test all navigation links in both languages

### 3.4 Date/Time Formatting
- [ ] Verify date formatting follows locale (DD/MM vs MM/DD)
- [ ] Test time display in both languages
- [ ] Check timestamp formatting in check-in/out records

## Phase 4: Production Deployment
**Goal**: Deploy i18n to production and document usage

### 4.1 Build & Deploy
- [ ] Test production build with both languages
- [ ] Verify compiled message files are included
- [ ] Test in Docker containers
- [ ] Verify environment variables are correct

### 4.2 Documentation
- [ ] Document how to add new translations
- [ ] Document how to add new language support
- [ ] Update README with i18n information
- [ ] Create translation maintenance guide

### 4.3 Verification
- [ ] Run `uv run python backend/verify.py`
- [ ] Test all user flows in production
- [ ] Verify performance impact is minimal
- [ ] Check browser language detection (if implemented)

## Success Criteria
- ✅ All user-facing strings translatable
- ✅ Language selection synced between Django and SvelteKit
- ✅ Swedish and English fully functional
- ✅ No hardcoded strings remain in UI
- ✅ Language preference persists across sessions
- ✅ API errors appear in selected language
- ✅ Date/time formatting follows locale
- ✅ All tests passing in both languages

## Notes
- Total estimated time: 8-10 hours
- See `I18N_IMPLEMENTATION_PLAN.md` for complete implementation details
- All Swedish translations provided in the plan
- Previous tasks archived to `CURRENT_TASKS_20251125.md`
