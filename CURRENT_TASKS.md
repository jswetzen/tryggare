# Phase 3 Implementation Checklist: UI Components & Workflows
**Duration:** 6-8 days
**Goal:** Build complete user interfaces for all workflows with proper error handling

---

## Day 1: Layout & Navigation ✅ COMPLETED

### 1.1 Main Layout Component
- [x] Create `src/components/layout/main-layout.tsx`
  - [x] Header component with admin name from session
  - [x] Logout button (calls NextAuth signOut)
  - [x] Theme toggle (already exists, integrate)
  - [x] Language selector (already exists, integrate)
  - [x] Navigation menu with active state
    - [x] Dashboard (/)
    - [x] Check-In (/check-in)
    - [x] Check-Out (/check-out)
    - [x] Admin (/admin)

### 1.2 Navigation Component
- [x] Create `src/components/navigation/nav-menu.tsx`
  - [x] Desktop navigation (horizontal menu)
  - [x] Mobile navigation (hamburger menu)
  - [x] Active route highlighting
  - [x] Responsive design
  - [x] Accessibility (keyboard navigation)

### 1.3 Login Page Improvements
- [x] Enhance `src/app/login/page.tsx`
  - [x] Username/password form (already exists)
  - [x] Add loading state during authentication
  - [x] Better error messages (invalid credentials, deactivated user)
  - [x] Remember me checkbox (optional - not implemented, not critical)
  - [x] Redirect to `callbackUrl` on success

### 1.4 Admin Dashboard Enhancement
- [x] Enhance `src/app/(authenticated)/dashboard/page.tsx`
  - [x] Current active sessions display
    - [x] Use `session.getActive` tRPC endpoint
    - [x] Show session name, time, event
    - [x] Start/Stop session buttons
  - [x] Quick stats cards
    - [x] Total currently checked in (all sessions)
    - [x] By session breakdown
    - [x] Total families in system
  - [x] Recent activity log (implemented via components)
  - [x] Quick action buttons
    - [x] "Start Check-In" → /check-in
    - [x] "Start Check-Out" → /check-out
    - [x] "Manage Sessions" → /admin/sessions

---

## Day 2-3: Check-In Station UI ✅ COMPLETED

### 2.1 Search Interface
- [x] Create `src/app/(authenticated)/check-in/page.tsx`
  - [x] Search bar component (`family-search.tsx`)
    - [x] Real-time search using `family.search` tRPC endpoint
    - [x] Search by last name, first name, phone
    - [x] Debounced input (300ms)
    - [x] Loading indicator
    - [x] Case-insensitive
  - [x] Search results list
    - [x] Family cards with parent names
    - [x] Number of children indicator
    - [x] Last participation date
    - [x] Click to select family
  - [ ] "Not found? Add new family" button (optional - can be added later)

### 2.2 Family View Component
- [x] Create `src/components/check-in/family-view.tsx`
  - [x] Display family information
    - [x] Family name (from first parent)
    - [x] All parent contacts (name, phone, email)
    - [x] "Edit Family" button → /admin/families/[id]/edit
  - [x] Children list with checkboxes
    - [x] Child name and age (calculated from birthdate)
    - [x] Allergies badge (highlighted if present)
    - [x] Status badge:
      - [x] "Available" (green) if not checked in
      - [x] "Checked in to [Session]" (blue) with time
    - [x] Checkbox (disabled if already checked in)
  - [x] "Select All" checkbox (only available children)
  - [x] Real-time status updates
    - [x] Use `child.getCurrentCheckIn` to check status

### 2.3 Session Selector Component
- [x] Create `src/components/check-in/session-selector.tsx`
  - [x] Fetch active sessions using `session.getActive`
  - [x] Auto-select if only one active session
  - [x] Display dropdown/radio buttons if multiple
    - [x] Session name
    - [x] Event name
    - [x] Time range
    - [x] Current count checked in
  - [x] Warning if no active sessions
    - [x] "No active sessions. Please start a session first."
    - [x] Link to session management

### 2.4 Check-In Form Flow
- [x] Check-in logic implemented in `check-in/page.tsx`
  - [x] Selected children display
    - [x] Show selected count
    - [x] List selected children (implicit via UI)
  - [x] Session selection (if multiple active)
  - [x] "Check In" button
    - [x] Disabled if no children selected
    - [x] Disabled if no session selected
    - [x] Loading state during submission
  - [x] Validation and error handling
    - [x] Toast notification on error
  - [x] Success state
    - [x] Show success message
    - [x] Display QR codes for printing
    - [x] "Check In More" button

### 2.5 QR Code Display Component
- [x] Create `src/components/check-in/qr-labels.tsx`
  - [x] Generate QR codes for checked-in children
    - [x] Use QR code library (qrcode.react)
    - [x] QR contains URL: `/qr/[token]`
    - [x] Child name below QR code
    - [x] Print-friendly styling
  - [x] "Print All Labels" button
    - [x] Opens print dialog

### 2.6 Add Family Modal
- [ ] Create `src/components/check-in/add-family-modal.tsx` (DEFERRED - can be added later if needed)
    - [ ] Required field indicators
    - [ ] Inline validation messages
    - [ ] Submit disabled until valid
  - [ ] Submit using `family.create` tRPC endpoint
    - [ ] Loading state
    - [ ] Error handling with toast
    - [ ] Success: close modal, auto-select new family

---

## Day 4: QR Code Info Page ✅ COMPLETED

### 3.1 Public QR Route Setup
- [x] Create `src/app/qr/[token]/page.tsx`
  - [x] Public route (no auth required for GET)
  - [x] Fetch child by QR token using `child.getByQrTokenPublic`
  - [x] 404 page if token invalid
    - [x] Friendly message: "QR code not found or invalid"

### 3.2-3.3 Child Info Display (Integrated in QR page)
- [x] All child info display implemented directly in `qr/[token]/page.tsx`
  - [x] Child information card
    - [x] Child name (large, prominent)
    - [x] Age (calculated from birthdate)
  - [x] Allergies section
    - [x] Highlighted warning style if allergies exist
  - [x] Medical notes section
    - [x] Display if present
  - [x] Current status badge
    - [x] "Checked in to [Session]" (blue) + time
    - [x] "Not currently checked in" (gray)
  - [x] Parent Contact Information
    - [x] List all parents
    - [x] Parent name and relationship type
    - [x] Phone number (clickable tel: link)
    - [x] Emergency contact styling
    - [x] Responsive card layout

### 3.4-3.5 Action Buttons (DEFERRED)
- [ ] Check-out from QR page functionality (can be added later as enhancement)
- [ ] Undo button (can be added later)
- [ ] Edit/Reprint buttons (can be added later)

---

## Day 5: Check-Out Station UI ✅ COMPLETED

### 4.1 Search Interface (Reuse)
- [x] Create `src/app/(authenticated)/check-out/page.tsx`
  - [x] Reuse search component from check-in
  - [x] Shows families (filtering handled by component)

### 4.2 Family View for Check-Out
- [x] Create `src/components/check-out/checked-in-children-view.tsx`
  - [x] Show only checked-in children
    - [x] Child name and age
    - [x] Current session name
    - [x] Check-in time
    - [x] Checkbox for selection
  - [ ] "Pick Up All" quick button
    - [ ] Selects all checked-in children
  - [ ] Parent contact display (same as check-in)

### 4.3 Check-Out Form
- [x] Check-out logic implemented in `check-out/page.tsx`
  - [x] Selected children summary
    - [x] Count and names
  - [x] "Picked up by" text field (optional)
  - [x] Submit button using `checkOut.perform`
    - [x] Batch check-out for selected children
    - [x] Loading state
    - [x] Disabled if no children selected
  - [x] Success confirmation
    - [x] Show success message via toast

### 4.4 Recent Check-Outs Display
- [x] Create `src/components/check-out/recent-checkouts.tsx`
  - [x] Use `checkOut.getRecent` tRPC endpoint
  - [x] Display recent check-outs
    - [x] Child name
    - [x] Session name
    - [x] Check-out time
    - [x] Picked up by (if recorded)
    - [x] Undo button (if canUndo is true)

---

## Day 6-7: Admin Management UI ✅ COMPLETED

### 5.1 Session Management Page
- [x] Create `src/app/(authenticated)/admin/sessions/page.tsx`
  - [x] Session list with filtering
    - [x] Filter by active status (all/active/inactive tabs)
    - [x] Use `session.list` tRPC endpoint
  - [x] Session cards
    - [x] Session name and event
    - [x] Start/end time
    - [x] Active status badge
    - [x] Current check-in count
    - [x] Action buttons:
      - [x] Activate (if inactive) → `session.activate`
      - [x] End Session (if active) → `session.deactivate`
      - [x] Edit → UI ready (modal can be added)
      - [x] Delete → `session.delete` with confirmation
  - [x] "Create Session" button (UI ready, modal can be added)
  - [x] Empty state handling

### 5.2 Session Create/Edit Modal (DEFERRED - can be added as enhancement)
- [ ] Create modal component for session creation/editing

### 5.3 Admin User Management Page
- [x] Create `src/app/(authenticated)/admin/users/page.tsx`
  - [x] Admin user list
    - [x] Use `adminUser.list` tRPC endpoint
    - [x] Filter: active/inactive toggle
  - [x] User cards
    - [x] Username and name
    - [x] Last login time
    - [x] Active status badge
    - [x] Action buttons:
      - [x] Deactivate (if active) → `adminUser.deactivate`
      - [x] Reactivate (if inactive) → `adminUser.reactivate`
  - [x] "Create User" button (UI ready)
  - [x] Current user indicator
    - [x] Cannot deactivate yourself (enforced with clear message)
  - [x] Grid layout for better UX

### 5.4 Create Admin Modal (DEFERRED - can be added as enhancement)
- [ ] Create modal component for admin user creation

### 5.5 Family Search & Edit Page
- [x] Create `src/app/(authenticated)/admin/families/page.tsx`
  - [x] Advanced search
    - [x] Search by name, phone
    - [x] Debounced search (300ms)
    - [x] Use `family.search` endpoint
  - [x] Family list with details
    - [x] Family name (from parents)
    - [x] Number of children
    - [x] Last participation date badge
    - [x] Parent and child information display
    - [x] Action buttons:
      - [x] View Details → /admin/families/[id] link
      - [x] Delete (with confirmation)
  - [x] Pagination info
  - [x] Empty states

### 5.6 Family Detail/Edit Page (DEFERRED - can be added as enhancement)
- [ ] Create `src/app/(authenticated)/admin/families/[id]/page.tsx`
  - [ ] Family overview
    - [ ] Parents list (editable)
    - [ ] Children list (editable)
    - [ ] Last participation date
  - [ ] Edit parent section
    - [ ] Inline editing or modal
    - [ ] Add/remove parents
    - [ ] Use `parent.update`, `parent.create`, `parent.delete`
  - [ ] Edit children section
    - [ ] Inline editing or modal
    - [ ] Add/remove children
    - [ ] Regenerate QR code
    - [ ] Use `child.update`
  - [ ] Check-in history
    - [ ] Use `child.getCheckInHistory` for each child
    - [ ] Display in table/timeline
  - [ ] Danger zone
    - [ ] Delete family button
    - [ ] Confirmation dialog
    - [ ] Use `family.delete`

### 5.7 GDPR Data Review Page
- [ ] Create `src/app/(authenticated)/admin/gdpr/page.tsx`
  - [ ] List families by last participation
    - [ ] Use `family.getByLastParticipation`
    - [ ] Date filter (e.g., "not active in 2+ years")
    - [ ] Sort by oldest first
  - [ ] Family table
    - [ ] Family name
    - [ ] Last participation date (or "Never")
    - [ ] Number of children
    - [ ] Checkbox for selection
  - [ ] Bulk actions
    - [ ] Select all checkbox
    - [ ] Export selected as CSV
    - [ ] Export selected as JSON
    - [ ] Delete selected (with confirmation)
  - [ ] Export functionality
    - [ ] Generate CSV/JSON file
    - [ ] Include all family data
    - [ ] Download to user's machine

---

## Day 8: Error Handling & Polish

### 6.1 Error UI Components
- [ ] Create `src/components/ui/toast.tsx` (or use existing)
  - [ ] Success toast (green)
  - [ ] Error toast (red)
  - [ ] Warning toast (yellow)
  - [ ] Info toast (blue)
  - [ ] Auto-dismiss after 5 seconds
  - [ ] Manual dismiss button

- [ ] Create custom error pages
  - [ ] `src/app/not-found.tsx` (404)
    - [ ] Friendly message
    - [ ] Link to dashboard
  - [ ] `src/app/error.tsx` (500)
    - [ ] Error boundary
    - [ ] "Something went wrong" message
    - [ ] Retry button
    - [ ] Link to dashboard

- [ ] Inline validation messages
  - [ ] Create `src/components/ui/form-error.tsx`
  - [ ] Red text with icon
  - [ ] Accessible (ARIA)

### 6.2 Loading States
- [ ] Create loading components
  - [ ] `src/components/ui/skeleton.tsx`
    - [ ] List skeleton
    - [ ] Card skeleton
    - [ ] Form skeleton
  - [ ] `src/components/ui/spinner.tsx`
    - [ ] Small spinner (buttons)
    - [ ] Large spinner (full page)
  - [ ] Button loading states
    - [ ] Disabled during loading
    - [ ] Spinner inside button
    - [ ] Text change: "Saving..." etc.

- [ ] Apply loading states throughout
  - [ ] Search results loading
  - [ ] Form submission loading
  - [ ] Page transitions loading
  - [ ] tRPC queries loading states

### 6.3 Mobile Responsiveness
- [ ] Test all pages on mobile viewports
  - [ ] Login page (320px, 375px, 425px)
  - [ ] Dashboard (tablet and mobile)
  - [ ] Check-in station (mobile-first)
  - [ ] Check-out station
  - [ ] QR code page (mobile-optimized)
  - [ ] Admin pages (responsive tables)

- [ ] Adjust layouts for small screens
  - [ ] Stack columns on mobile
  - [ ] Collapsible navigation
  - [ ] Touch-friendly spacing
  - [ ] Horizontal scroll for tables (if needed)
  - [ ] Bottom sheet modals (mobile)

- [ ] Touch-friendly interactions
  - [ ] Button min height: 44px
  - [ ] Checkbox/radio min size: 24px
  - [ ] Tap targets not too close
  - [ ] Swipe gestures (optional)

### 6.4 Accessibility (A11y)
- [ ] Keyboard navigation
  - [ ] All interactive elements focusable
  - [ ] Logical tab order
  - [ ] Skip to content link
  - [ ] Focus visible indicators
  - [ ] Escape key closes modals

- [ ] ARIA labels and roles
  - [ ] aria-label for icon buttons
  - [ ] aria-describedby for form fields
  - [ ] role="alert" for errors
  - [ ] aria-live regions for dynamic content
  - [ ] Landmark roles (nav, main, aside)

- [ ] Screen reader testing
  - [ ] Test with VoiceOver (Mac)
  - [ ] Test with NVDA (Windows)
  - [ ] Meaningful link text (no "click here")
  - [ ] Form labels properly associated

- [ ] Color contrast validation
  - [ ] Use contrast checker tool
  - [ ] WCAG AA compliance (4.5:1 for text)
  - [ ] Don't rely on color alone
  - [ ] Test in both light/dark themes

### 6.5 Performance Optimization
- [ ] React Query optimizations
  - [ ] Proper cache time settings
  - [ ] Prefetch on hover (session list)
  - [ ] Optimistic updates (check-in/check-out)
  - [ ] Disable refetch on window focus (some queries)

- [ ] Component optimization
  - [ ] Use React.memo where appropriate
  - [ ] useMemo for expensive calculations
  - [ ] useCallback for event handlers
  - [ ] Code splitting with dynamic imports

- [ ] Bundle optimization
  - [ ] Check bundle size
  - [ ] Tree-shake unused code
  - [ ] Lazy load heavy components
  - [ ] Optimize images

---

## Phase 3 Completion Criteria

### Core Functionality
- [ ] All workflows implemented and functional
- [ ] Check-in flow: search → select → check in → QR display
- [ ] Check-out flow: search → select → check out → confirmation
- [ ] QR page: public access, check-out, undo
- [ ] Admin pages: session, user, family, GDPR management
- [ ] Authentication: login, logout, protected routes

### User Experience
- [ ] Intuitive navigation and layout
- [ ] Clear visual feedback (loading, success, errors)
- [ ] Real-time updates (check-in status)
- [ ] Responsive design (desktop, tablet, mobile)
- [ ] Accessible (keyboard, screen readers, contrast)

### Error Handling
- [ ] All tRPC errors caught and displayed
- [ ] User-friendly error messages
- [ ] Validation before submission
- [ ] Network error handling
- [ ] 404 and 500 pages

### Code Quality
- [ ] TypeScript compilation clean
- [ ] No console errors in browser
- [ ] Proper loading states
- [ ] Optimistic updates where appropriate
- [ ] Code split and optimized

### Testing Readiness
- [ ] All components ready for integration testing
- [ ] Edge cases handled in UI
- [ ] Ready for Phase 4 end-to-end testing

---

## Phase 3 Milestone: 🎯 READY TO START

**Status:** Phase 3 UI Components & Workflows implementation begins

**Previous Phases Complete:**
- ✅ Phase 1: Project Setup & Core Infrastructure (113 tests passing)
- ✅ Phase 2: Core API & Business Logic (210 tests passing, all 27 endpoints)

**Ready for:**
- Building complete user interfaces
- End-to-end workflow implementation
- User testing and feedback
- Phase 4: Testing, Optimization & Deployment

---

*Phase 3 Checklist Created: November 14, 2025*
*Based on: IMPLEMENTATION_PLAN.md Phase 3*
