# Current Tasks - UI Fixes and Enhancements (Phase 8)

**Started**: 2025-12-10
**Goal**: Fix UI issues across check-in, check-out, and print queue pages

---

## 📋 Overview

This phase addresses multiple UI improvements:
- **Check-in page**: Session switcher visibility, WebSocket events, translations, show checked-in families toggle
- **Check-out page**: Layout consistency, family checkout button, 24-hour time format, "picked up by" field fixes
- **Print queue**: Label dimensions, simplified design, QR code generation fix

**Total Estimated Time**: 7-11 hours

---

## Phase 1: Critical Fixes (1-2 hours) ⏳

### 1.1 Fix "Picked Up By" Field - Parent Name Display
**Status**: 🔴 NOT STARTED

**Problem**: Options show "()" instead of parent names
- Backend returns: `parent.name`, `parent.relationship_type` (snake_case)
- Frontend expects: `parent.firstName`, `parent.lastName`, `parent.relationshipType` (camelCase)

**Files to modify**:
- `/frontend/src/lib/components/domain/FamilyTable.svelte` (lines 18-22, 152-156)
- `/frontend/src/lib/i18n/locales/en.json` - Add `checkout.selectPerson`
- `/frontend/src/lib/i18n/locales/sv.json` - Add Swedish translation

**Agent assignment**: Frontend agent

---

### 1.2 Fix Untranslated Strings - Check-in Page
**Status**: 🔴 NOT STARTED

**Hardcoded strings** (in `/frontend/src/routes/checkin/+page.svelte`):
1. Line 490: `${child.name} check-in undone`
2. Line 551: `${family.name} check-in undone`
3. Line 667: `${data.familyName} family added with ${count} ${childrenLabel}!`
4. Line 744: `'family' : 'families'`

**Translation keys needed**:
- `checkin.checkInUndone` (with `{name}` param)
- `checkin.familyCheckInUndone` (with `{name}` param)
- `checkin.familyAdded` (with multiple params)
- `common.family` and `common.families`

**Files to modify**:
- `/frontend/src/routes/checkin/+page.svelte`
- `/frontend/src/lib/i18n/locales/en.json`
- `/frontend/src/lib/i18n/locales/sv.json`

**Agent assignment**: Frontend agent

---

### 1.3 Fix Untranslated Strings - Checkout Page
**Status**: 🔴 NOT STARTED

**Hardcoded strings** (in `/frontend/src/routes/checkout/+page.svelte`):
- Line 344: `'family' : 'families'` singular/plural

**Solution**: Use `common.family` and `common.families` keys

**Files to modify**:
- `/frontend/src/routes/checkout/+page.svelte` (line 344)

**Agent assignment**: Frontend agent

---

### 1.4 Fix 24-Hour Time Format
**Status**: 🔴 NOT STARTED

**Current**: Shows "10:16 AM" format
**Required**: 24-hour format "10:16"

**Change**: `{ hour: '2-digit', minute: '2-digit', hour12: false }`

**Files to modify**:
- `/frontend/src/routes/checkout/+page.svelte` (lines 282-288)
- `/frontend/src/routes/checkin/+page.svelte` (lines 137-150)
- `/frontend/src/lib/components/domain/FamilyTable.svelte` (default formatTime function)

**Agent assignment**: Frontend agent

---

### 1.5 Remove White Box Wrapper from Checkout
**Status**: 🔴 NOT STARTED

**Problem**: Checkout has white box wrapper, check-in doesn't. Should match.

**Files to modify**:
- `/frontend/src/routes/checkout/+page.svelte` (line 326) - Remove wrapper div

**Agent assignment**: Frontend agent

---

## Phase 2: WebSocket & Session Features (2-3 hours) ⏳

### 2.1 Add checkin_undone WebSocket Handler
**Status**: ✅ COMPLETE

**Problem**: Backend broadcasts `checkin_undone` event but frontend doesn't handle it

**Files modified**:
- `/backend/checkins/consumers.py` - Added `checkin_undone` handler method and updated docstring
- `/frontend/src/routes/checkin/+page.svelte` (lines 242-280) - Added WebSocket event handler

**Implementation**: When a check-in is undone on another station, the frontend now receives the `checkin_undone` event and updates the child's state to reflect that they are no longer checked in. The handler only updates children that don't have a local undo action in progress to avoid conflicts.

**Agent assignment**: Full-stack agent

---

### 2.2 Implement Conditional Session Switcher Visibility
**Status**: ✅ COMPLETED

**Problem**: "Change Session" link always shows, even with only one session

**Solution**:
- Fetch active session count from API: `GET /api/sessions/?is_active=true`
- Pass `showChangeSession={activeSessions.length > 1}` to SessionIndicator
- Replace placeholder alert with actual functionality

**Files modified**:
- `/frontend/src/routes/checkin/+page.svelte` - Added session count logic and conditional prop

**Agent assignment**: Frontend agent

---

### 2.3 Add "Show Checked-In Families" Toggle
**Status**: ✅ COMPLETED

**Requirements**:
- Add checkbox at top of check-in page
- Session-only toggle (no localStorage persistence)
- Bypass `shouldShowFamily()` filtering when ON
- Show checked-in families with visual indicator

**Files modified**:
- `/frontend/src/routes/checkin/+page.svelte` - Added toggle UI and filtering logic
- `/frontend/src/lib/components/checkin/FamilyCard.svelte` - Added visual indicators (grayed out + badge)
- `/frontend/src/lib/i18n/locales/en.json` - Added translation keys
- `/frontend/src/lib/i18n/locales/sv.json` - Added Swedish translations

**Agent assignment**: Frontend agent

---

## Phase 3: Checkout Enhancements (2-3 hours) ⏳

### 3.1 Add Family Check-Out Button
**Status**: ✅ COMPLETED

**Requirements**:
- Add "Check Out Family" button in family row
- Check out all checked-in children at once
- Skip children already checked out
- Use single "picked up by" value for all

**Files modified**:
- `/frontend/src/routes/checkout/+page.svelte` - Added `performFamilyCheckOut()` function
- FamilyTable already had `onToggleFamily` prop support, just needed to wire it up
- `/frontend/src/lib/i18n/locales/en.json` - Added translation keys
- `/frontend/src/lib/i18n/locales/sv.json` - Added Swedish translations

**Agent assignment**: Frontend agent

---

## Phase 4: Print Label Overhaul (2-3 hours) ✅ COMPLETE

### 4.1 Add qrcode Library Dependency
**Status**: ✅ COMPLETE

**Files modified**:
- `/backend/pyproject.toml` - Added `qrcode>=7.4,<8.0`
- Ran: `uv add qrcode` in backend directory

**Agent assignment**: Backend agent

---

### 4.2 Update Print Label Dimensions & Design
**Status**: ✅ COMPLETE

**Changes completed**:
1. ✅ Dimensions: Updated to 54.3mm × 17mm portrait (was 29mm × 90mm)
2. ✅ Simplified design: QR code + name only (removed session, allergies)
3. ✅ Fixed QR code: Now generates as base64 data URL
4. ✅ QR code links to `/qr/{token}` (not `/api/qr/{token}`)

**Files modified**:
- `/backend/checkins/templates/print_label.html` - Updated dimensions, layout, styles (flexbox horizontal layout)
- `/backend/checkins/views.py` (lines 443-471) - Implemented QR generation with base64
- `/backend/checkins/tests.py` - Added comprehensive test suite (5 tests)
- `/backend/test_print_queue.py` - Updated existing test to match new design

**Tests added**:
- `test_print_page_returns_html` - Verifies HTML response
- `test_print_page_contains_child_name` - Verifies name is present
- `test_print_page_contains_qr_code_as_data_url` - Verifies base64 QR code
- `test_print_page_has_correct_dimensions` - Verifies 54.3mm × 17mm
- `test_print_page_does_not_contain_session_or_allergies` - Verifies simplified design

**Verification**: All tests pass ✅

**Agent assignment**: Backend agent

---

## 🎯 Success Criteria

**Phase 1 Complete When**:
- ✅ Parent names display correctly in "picked up by" dropdown
- ✅ All hardcoded strings translated (English + Swedish)
- ✅ Time displays in 24-hour format everywhere
- ✅ Checkout page layout matches check-in page

**Phase 2 Complete When**:
- ✅ Undo check-in updates visible on all stations (WebSocket)
- ✅ Session switcher only shows with multiple active sessions
- ✅ "Show checked-in families" toggle works

**Phase 3 Complete When**:
- ✅ Family checkout button checks out all children at once
- ✅ Handles partial families (some children already checked out)

**Phase 4 Complete When**:
- ✅ Labels print at correct dimensions (17mm × 54.3mm)
- ✅ QR code displays and scans to correct URL
- ✅ Layout is simplified (name + QR only)

---

## 🧪 Testing Plan

**Functional Testing**:
- [ ] Test with multiple browser tabs (WebSocket updates)
- [ ] Test session switcher with 1 vs. multiple active sessions
- [ ] Test family checkout with partial families
- [ ] Test "show checked-in families" toggle
- [ ] Verify parent names in "picked up by" dropdown

**Localization Testing**:
- [ ] Switch language English ↔ Swedish
- [ ] Verify all new translation keys work
- [ ] Check singular/plural forms

**Print Testing**:
- [ ] Print label on Brother QL printer
- [ ] Scan QR code → verify URL
- [ ] Test with long child names

---

## 📁 Critical Files

**Frontend**:
- `/frontend/src/routes/checkin/+page.svelte`
- `/frontend/src/routes/checkout/+page.svelte`
- `/frontend/src/lib/components/checkin/SessionIndicator.svelte`
- `/frontend/src/lib/components/domain/FamilyTable.svelte`
- `/frontend/src/lib/i18n/locales/en.json`
- `/frontend/src/lib/i18n/locales/sv.json`

**Backend**:
- `/backend/checkins/consumers.py`
- `/backend/checkins/views.py`
- `/backend/checkins/templates/print_label.html`
- `/backend/pyproject.toml`

---

## 🚀 Agent Coordination Strategy

**Parallel work streams**:
1. **Frontend Agent 1**: Phase 1 critical fixes (tasks 1.1-1.5)
2. **Frontend Agent 2**: Phase 2 & 3 features (tasks 2.2, 2.3, 3.1)
3. **Full-stack Agent**: WebSocket handler (task 2.1)
4. **Backend Agent**: Print label overhaul (tasks 4.1-4.2)

All agents can work in parallel with minimal conflicts.
