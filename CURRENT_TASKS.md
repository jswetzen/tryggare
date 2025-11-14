# Phase 3 Implementation Checklist: UI Components & Workflows
**Duration:** 6-8 days
**Goal:** Build complete user interfaces for all workflows with proper error handling

---

## Day 1: Layout & Navigation ⏳ IN PROGRESS

### 1.1 Main Layout Component
- [ ] Create `src/components/layout/main-layout.tsx`
  - [ ] Header component with admin name from session
  - [ ] Logout button (calls NextAuth signOut)
  - [ ] Theme toggle (already exists, integrate)
  - [ ] Language selector (already exists, integrate)
  - [ ] Navigation menu with active state
    - [ ] Dashboard (/)
    - [ ] Check-In (/check-in)
    - [ ] Check-Out (/check-out)
    - [ ] Admin (/admin)

### 1.2 Navigation Component
- [ ] Create `src/components/navigation/nav-menu.tsx`
  - [ ] Desktop navigation (horizontal menu)
  - [ ] Mobile navigation (hamburger menu)
  - [ ] Active route highlighting
  - [ ] Responsive design
  - [ ] Accessibility (keyboard navigation)

### 1.3 Login Page Improvements
- [ ] Enhance `src/app/login/page.tsx`
  - [x] Username/password form (already exists)
  - [ ] Add loading state during authentication
  - [ ] Better error messages (invalid credentials, deactivated user)
  - [ ] Remember me checkbox (optional)
  - [ ] Redirect to `callbackUrl` on success

### 1.4 Admin Dashboard Enhancement
- [ ] Enhance `src/app/(authenticated)/dashboard/page.tsx`
  - [ ] Current active sessions display
    - [ ] Use `session.getActive` tRPC endpoint
    - [ ] Show session name, time, event
    - [ ] Start/Stop session buttons
  - [ ] Quick stats cards
    - [ ] Total currently checked in (all sessions)
    - [ ] By session breakdown
    - [ ] Total families in system
  - [ ] Recent activity log
    - [ ] Last 10 check-ins/check-outs
    - [ ] Show child name, action, time, staff
  - [ ] Quick action buttons
    - [ ] "Start Check-In" → /check-in
    - [ ] "Start Check-Out" → /check-out
    - [ ] "Manage Sessions" → /admin/sessions

---

## Day 2-3: Check-In Station UI

### 2.1 Search Interface
- [ ] Create `src/app/(authenticated)/check-in/page.tsx`
  - [ ] Search bar component
    - [ ] Real-time search using `family.search` tRPC endpoint
    - [ ] Search by last name, first name, phone
    - [ ] Debounced input (300ms)
    - [ ] Loading indicator
    - [ ] Case-insensitive
  - [ ] Search results list
    - [ ] Family cards with parent names
    - [ ] Number of children indicator
    - [ ] Last participation date
    - [ ] Click to select family
  - [ ] "Not found? Add new family" button
    - [ ] Opens add family modal

### 2.2 Family View Component
- [ ] Create `src/components/check-in/family-view.tsx`
  - [ ] Display family information
    - [ ] Family name (from first parent)
    - [ ] All parent contacts (name, phone, email)
    - [ ] "Edit Family" button → /admin/families/[id]/edit
  - [ ] Children list with checkboxes
    - [ ] Child name and age (calculated from birthdate)
    - [ ] Allergies badge (highlighted if present)
    - [ ] Status badge:
      - [ ] "Available" (green) if not checked in
      - [ ] "Checked in to [Session]" (blue) with time
    - [ ] Checkbox (disabled if already checked in)
  - [ ] "Select All" checkbox (only available children)
  - [ ] Real-time status updates
    - [ ] Use `child.getCurrentCheckIn` to check status

### 2.3 Session Selector Component
- [ ] Create `src/components/check-in/session-selector.tsx`
  - [ ] Fetch active sessions using `session.getActive`
  - [ ] Auto-select if only one active session
  - [ ] Display dropdown/radio buttons if multiple
    - [ ] Session name
    - [ ] Event name
    - [ ] Time range
    - [ ] Current count checked in
  - [ ] Warning if no active sessions
    - [ ] "No active sessions. Please start a session first."
    - [ ] Link to session management

### 2.4 Check-In Form Flow
- [ ] Create `src/components/check-in/check-in-form.tsx`
  - [ ] Selected children display
    - [ ] Show selected count
    - [ ] List selected children
    - [ ] "Clear Selection" button
  - [ ] Session selection (if multiple active)
  - [ ] "Check In" button
    - [ ] Disabled if no children selected
    - [ ] Disabled if no session selected
    - [ ] Loading state during submission
  - [ ] Validation and error handling
    - [ ] Use `checkIn.validate` before submission
    - [ ] Display inline errors:
      - [ ] "[Child] is already checked into [Session]"
      - [ ] Link to quick check-out or view current session
    - [ ] Toast notification on error
  - [ ] Success state
    - [ ] Show success message
    - [ ] Display QR codes for printing
    - [ ] "Check In More" button
    - [ ] Auto-clear after 3 seconds

### 2.5 QR Code Display Component
- [ ] Create `src/components/check-in/qr-code-display.tsx`
  - [ ] Generate QR codes for checked-in children
    - [ ] Use QR code library (qrcode.react or similar)
    - [ ] QR contains URL: `/qr/[token]`
    - [ ] Child name below QR code
    - [ ] Print-friendly styling
  - [ ] "Print All Labels" button
    - [ ] Opens print dialog
    - [ ] Optimized print layout (2-3 per page)
  - [ ] Individual download buttons
    - [ ] Download QR as PNG
    - [ ] Filename: `[childName]-QR.png`

### 2.6 Add Family Modal
- [ ] Create `src/components/check-in/add-family-modal.tsx`
  - [ ] Parent section
    - [ ] Dynamic "Add Parent" button
    - [ ] Parent fields: name (required), relationship type, phone, email
    - [ ] Email validation
    - [ ] Minimum 1 parent required
    - [ ] "Remove Parent" button (if > 1 parent)
  - [ ] Children section
    - [ ] Dynamic "Add Child" button
    - [ ] Child fields: firstName, lastName, birthdate, allergies, notes
    - [ ] Age calculation display
    - [ ] Minimum 1 child required
    - [ ] "Remove Child" button (if > 1 child)
  - [ ] Form validation
    - [ ] Required field indicators
    - [ ] Inline validation messages
    - [ ] Submit disabled until valid
  - [ ] Submit using `family.create` tRPC endpoint
    - [ ] Loading state
    - [ ] Error handling with toast
    - [ ] Success: close modal, auto-select new family

---

## Day 4: QR Code Info Page

### 3.1 Public QR Route Setup
- [ ] Create `src/app/qr/[token]/page.tsx`
  - [ ] Public route (no auth required for GET)
  - [ ] Fetch child by QR token using `child.getByQrToken`
  - [ ] 404 page if token invalid
    - [ ] Friendly message: "QR code not found or invalid"
    - [ ] Link to homepage

### 3.2 Child Info Display Component
- [ ] Create `src/components/qr/child-info-display.tsx`
  - [ ] Child information card
    - [ ] Child name (large, prominent)
    - [ ] Age (calculated from birthdate)
    - [ ] Photo placeholder (optional for future)
  - [ ] Allergies section
    - [ ] Highlighted warning style if allergies exist
    - [ ] "No known allergies" if none
  - [ ] Medical notes section
    - [ ] Display if present
    - [ ] Hidden if empty
  - [ ] Current status badge
    - [ ] "Checked in to [Session]" (blue) + time
    - [ ] "Not currently checked in" (gray)
    - [ ] Real-time updates

### 3.3 Parent Contact Information
- [ ] Create `src/components/qr/parent-contacts.tsx`
  - [ ] List all parents
    - [ ] Parent name and relationship type
    - [ ] Phone number (clickable tel: link)
    - [ ] Email address (clickable mailto: link)
  - [ ] Emergency contact styling
  - [ ] Responsive card layout

### 3.4 Action Buttons Component
- [ ] Create `src/components/qr/qr-actions.tsx`
  - [ ] Check-Out button
    - [ ] Only visible if child is checked in
    - [ ] Requires admin login (redirect with callbackUrl)
    - [ ] Opens check-out modal
  - [ ] Undo Check-Out button
    - [ ] Only visible if recently checked out (< 5 minutes)
    - [ ] Shows countdown timer
    - [ ] One-click undo using `checkOut.undo`
    - [ ] Confirmation message
  - [ ] Edit button
    - [ ] Requires admin login
    - [ ] Redirects to `/admin/children/[id]/edit`
  - [ ] Reprint Label button
    - [ ] Downloads QR code as PNG
    - [ ] Filename: `[childName]-QR.png`

### 3.5 Check-Out Modal (QR Page)
- [ ] Create `src/components/qr/quick-checkout-modal.tsx`
  - [ ] Child name display
  - [ ] Session name display
  - [ ] Optional "Picked up by" text field
  - [ ] Submit button using `checkOut.perform`
  - [ ] Loading state
  - [ ] Error handling
  - [ ] Success: close modal, refresh status

---

## Day 5: Check-Out Station UI

### 4.1 Search Interface (Reuse)
- [ ] Create `src/app/(authenticated)/check-out/page.tsx`
  - [ ] Reuse search component from check-in
  - [ ] Filter to show only families with checked-in children
    - [ ] Use `checkIn.getCurrentCheckIns` to filter
  - [ ] Display "No checked-in children found" if empty

### 4.2 Family View for Check-Out
- [ ] Create `src/components/check-out/family-checkout-view.tsx`
  - [ ] Show only checked-in children
    - [ ] Child name and age
    - [ ] Current session name
    - [ ] Check-in time
    - [ ] Checkbox for selection
  - [ ] "Pick Up All" quick button
    - [ ] Selects all checked-in children
  - [ ] Parent contact display (same as check-in)

### 4.3 Check-Out Form
- [ ] Create `src/components/check-out/checkout-form.tsx`
  - [ ] Selected children summary
    - [ ] Count and names
    - [ ] Session names if different
  - [ ] "Picked up by" text field (optional)
    - [ ] Auto-suggest parent names
  - [ ] Submit button using `checkOut.perform`
    - [ ] Batch check-out for selected children
    - [ ] Loading state
    - [ ] Disabled if no children selected
  - [ ] Success confirmation
    - [ ] Show success message
    - [ ] List checked-out children
    - [ ] "Check Out More" button
    - [ ] Auto-clear after 3 seconds

### 4.4 Recent Check-Outs Display
- [ ] Create `src/components/check-out/recent-checkouts.tsx`
  - [ ] Use `checkOut.getRecent` tRPC endpoint
  - [ ] Display last 10 check-outs
    - [ ] Child name
    - [ ] Session name
    - [ ] Check-out time (relative: "2 minutes ago")
    - [ ] Picked up by (if recorded)
    - [ ] Undo button (if canUndo is true)
  - [ ] Auto-refresh every 30 seconds
  - [ ] "View All" link to history page

---

## Day 6-7: Admin Management UI

### 5.1 Session Management Page
- [ ] Create `src/app/(authenticated)/admin/sessions/page.tsx`
  - [ ] Session list with filtering
    - [ ] Filter by event dropdown
    - [ ] Filter by date range
    - [ ] Filter by active status
    - [ ] Use `session.list` tRPC endpoint
  - [ ] Session cards/table
    - [ ] Session name and event
    - [ ] Start/end time
    - [ ] Active status badge
    - [ ] Current check-in count
    - [ ] Action buttons:
      - [ ] Start (if inactive) → `session.activate`
      - [ ] End (if active) → `session.deactivate`
      - [ ] Edit → opens edit modal
      - [ ] Delete (if no check-ins) → `session.delete`
  - [ ] "Create New Session" button
    - [ ] Opens create session modal
  - [ ] Pagination (if many sessions)

### 5.2 Session Create/Edit Modal
- [ ] Create `src/components/admin/session-form-modal.tsx`
  - [ ] Form fields
    - [ ] Session name (required)
    - [ ] Event selection (dropdown)
    - [ ] Start date/time (required)
    - [ ] End date/time (required)
    - [ ] Requires ticket (checkbox)
    - [ ] Active status (checkbox)
  - [ ] Validation
    - [ ] End time must be after start time
    - [ ] Event must exist
    - [ ] Inline error messages
  - [ ] Submit using `session.create` or `session.update`
  - [ ] Loading and error states
  - [ ] Success: close modal, refresh list

### 5.3 Admin User Management Page
- [ ] Create `src/app/(authenticated)/admin/users/page.tsx`
  - [ ] Admin user list
    - [ ] Use `adminUser.list` tRPC endpoint
    - [ ] Filter: active/inactive toggle
  - [ ] User cards/table
    - [ ] Username and name
    - [ ] Last login time
    - [ ] Active status badge
    - [ ] Action buttons:
      - [ ] Deactivate (if active) → `adminUser.deactivate`
      - [ ] Reactivate (if inactive) → `adminUser.reactivate`
      - [ ] View activity log
  - [ ] "Add New Admin" button
    - [ ] Opens create admin modal
  - [ ] Current user indicator
    - [ ] Cannot deactivate yourself

### 5.4 Create Admin Modal
- [ ] Create `src/components/admin/create-admin-modal.tsx`
  - [ ] Form fields
    - [ ] Username (required, unique)
    - [ ] Name (required)
    - [ ] Password (required, min 8 chars)
    - [ ] Confirm password
  - [ ] Validation
    - [ ] Username uniqueness check
    - [ ] Password strength indicator
    - [ ] Passwords match
  - [ ] Submit using `adminUser.create`
  - [ ] Loading and error states
  - [ ] Success: close modal, show credentials once

### 5.5 Family Search & Edit Page
- [ ] Create `src/app/(authenticated)/admin/families/page.tsx`
  - [ ] Advanced search
    - [ ] Search by name, phone
    - [ ] Filter by last participation date
    - [ ] Use `family.search` and `family.getByLastParticipation`
  - [ ] Family list with details
    - [ ] Family name (from parents)
    - [ ] Number of children
    - [ ] Last participation date
    - [ ] Action buttons:
      - [ ] View/Edit → /admin/families/[id]
      - [ ] View History
      - [ ] Delete (with confirmation)
  - [ ] Pagination

### 5.6 Family Detail/Edit Page
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
