# React to Svelte Migration Plan

## Overview
This document outlines the complete migration strategy for converting the Check-In Station React prototype to production Svelte implementation, using test-driven development to ensure functional parity.

---

## Phase 0: Pre-Migration Preparation

### 0.1 Documentation
- [ ] Document all React prototype features and behaviors
- [ ] List all user interactions and workflows
- [ ] Document edge cases and error states
- [ ] Create visual specification (screenshots of key states)

### 0.2 Test Data Setup
- [ ] Extract mock data into shared fixtures file
- [ ] Create reusable test data factories
- [ ] Document data models (Family, Child, TicketType)

### 0.3 Test Infrastructure
- [ ] Verify Vitest is configured for Svelte
- [ ] Install @testing-library/svelte
- [ ] Set up Playwright for E2E tests
- [ ] Configure test coverage reporting

### 0.4 Add data-testid to React Prototype
- [x] Add `data-testid="session-indicator"` to SessionIndicator component
- [x] Add `data-testid="change-session-button"` to Change Session button
- [x] Add `data-testid="add-family-button"` to Add Family button
- [x] Add `data-testid="search-input"` to search input
- [x] Add `data-testid="clear-search-button"` to search clear button
- [x] Add `data-testid="family-count-text"` to family count display
- [x] Add `data-testid="family-card-{familyId}"` to each FamilyCard
- [x] Add `data-testid="family-toggle-button-{familyId}"` to family expand/collapse buttons
- [x] Add `data-testid="family-check-in-button-{familyId}"` to Check In Family buttons
- [x] Add `data-testid="family-undo-button-{familyId}"` to family undo buttons
- [x] Add `data-testid="child-row-{childId}"` to each child row
- [x] Add `data-testid="child-check-in-button-{childId}"` to individual Check In buttons
- [x] Add `data-testid="child-undo-button-{childId}"` to individual undo buttons
- [x] Add `data-testid="child-expand-button-{childId}"` to child expansion buttons
- [x] Add `data-testid="ticket-assign-event-{childId}"` to Event Pass assignment buttons
- [x] Add `data-testid="ticket-assign-session-{childId}"` to Session Ticket assignment buttons
- [x] Add `data-testid="success-toast"` to success toast notification
- [x] Add `data-testid="add-family-panel"` to AddFamilyPanel
- [x] Add `data-testid="add-family-name-input"` to family name input
- [x] Add `data-testid="add-family-submit-button"` to submit button
- [x] Add `data-testid="add-family-cancel-button"` to cancel button

---

## Phase 1: Write Framework-Agnostic Tests

### 1.1 E2E Test Suite (Playwright)
- [ ] Test: Navigate to app and verify page loads
- [ ] Test: Search for family by name
- [ ] Test: Search for child by name (verify auto-expand)
- [ ] Test: Clear search query
- [ ] Test: Expand/collapse family card
- [ ] Test: Check in individual child
- [ ] Test: Verify check-in success toast appears
- [ ] Test: Check in entire family
- [ ] Test: Undo individual child check-in (within timer)
- [ ] Test: Undo family check-in (within timer)
- [ ] Test: Verify undo timer countdown
- [ ] Test: Verify undo button disappears after timer expires
- [ ] Test: Expand child row for ticket assignment
- [ ] Test: Assign Event Pass ticket to child without ticket
- [ ] Test: Assign Session Ticket to child without ticket
- [ ] Test: Open Add Family panel
- [ ] Test: Add new family with children
- [ ] Test: Verify new family appears in sorted list
- [ ] Test: Verify new family auto-expands after creation
- [ ] Test: Cancel Add Family panel
- [ ] Test: Empty search results display
- [ ] Test: Family visibility after all children checked in

### 1.2 Run Tests Against React Prototype
- [ ] Execute full E2E suite against React app
- [ ] Verify 100% pass rate
- [ ] Document baseline performance metrics
- [ ] Take screenshots for visual regression baseline

### 1.3 Integration Tests
- [ ] Test: FamilyCard component with various states
- [ ] Test: Search + expand interaction
- [ ] Test: Check-in + undo timer interaction
- [ ] Test: AddFamilyPanel form validation and submission
- [ ] Test: Multiple simultaneous undo timers

---

## Phase 2: Component Inventory & Styling

### 2.1 Component Audit
- [ ] List all React components:
  - [ ] App (main container)
  - [ ] SessionIndicator
  - [ ] SuccessToast
  - [ ] FamilyCard
  - [ ] ChildCheckInButton
  - [ ] AddFamilyPanel
- [ ] List all hooks/utilities:
  - [ ] useUndoTimer
  - [ ] familyVisibility utility
- [ ] List all types (types.ts)

### 2.2 Create Svelte Component Structure
- [ ] Create `/src/lib/components/` directory
- [ ] Create component stub: `SessionIndicator.svelte`
- [ ] Create component stub: `SuccessToast.svelte`
- [ ] Create component stub: `FamilyCard.svelte`
- [ ] Create component stub: `ChildCheckInButton.svelte`
- [ ] Create component stub: `AddFamilyPanel.svelte`

### 2.3 Extract and Apply Styling
- [ ] Document all Tailwind classes used in React components
- [ ] Verify Tailwind configuration is compatible
- [ ] Apply base styling to SessionIndicator.svelte
- [ ] Apply base styling to SuccessToast.svelte
- [ ] Apply base styling to FamilyCard.svelte
- [ ] Apply base styling to ChildCheckInButton.svelte
- [ ] Apply base styling to AddFamilyPanel.svelte
- [ ] Create CSS animations for slide-in effect
- [ ] Create CSS animations for expand effect

### 2.4 Visual Verification
- [ ] Preview SessionIndicator styling in Storybook/isolation
- [ ] Preview SuccessToast styling
- [ ] Preview FamilyCard styling
- [ ] Preview ChildCheckInButton styling
- [ ] Preview AddFamilyPanel styling

---

## Phase 3: Port Utilities and Types

### 3.1 TypeScript Types
- [ ] Create `/src/lib/types.ts`
- [ ] Port Family interface
- [ ] Port Child interface
- [ ] Port TicketType type
- [ ] Port UndoAction interface (if needed)

### 3.2 Utility Functions
- [ ] Create `/src/lib/utils/` directory
- [ ] Port `familyVisibility.ts` utility
- [ ] Write unit tests for familyVisibility utility
- [ ] Verify tests pass in Svelte context
- [ ] Port time formatting utility

### 3.3 State Management (Svelte Stores)
- [ ] Create `/src/lib/stores/` directory
- [ ] Create `undoTimer.ts` store (port useUndoTimer hook)
- [ ] Create `families.ts` store for family data
- [ ] Create `search.ts` store for search state
- [ ] Create `ui.ts` store for UI state (expanded families, panels, etc.)
- [ ] Write unit tests for stores
- [ ] Document store APIs

---

## Phase 4: Implement Svelte Components

### 4.1 Leaf Components (No Dependencies)
- [ ] Implement SessionIndicator.svelte
  - [ ] Add props interface
  - [ ] Add event handlers (on:changeSession, on:addFamily)
  - [ ] Add data-testid attributes
  - [ ] Write component tests
- [ ] Implement SuccessToast.svelte
  - [ ] Add auto-dismiss timer
  - [ ] Add slide-in animation
  - [ ] Add data-testid attributes
  - [ ] Write component tests

### 4.2 Child Components
- [ ] Implement ChildCheckInButton.svelte
  - [ ] Add child data props
  - [ ] Add check-in/undo logic
  - [ ] Add timer display
  - [ ] Add ticket assignment expansion
  - [ ] Add data-testid attributes
  - [ ] Write component tests

### 4.3 Container Components
- [ ] Implement FamilyCard.svelte
  - [ ] Add family data props
  - [ ] Add expand/collapse logic
  - [ ] Integrate ChildCheckInButton components
  - [ ] Add Check In Family button logic
  - [ ] Add family-level undo button
  - [ ] Add data-testid attributes
  - [ ] Write component tests
- [ ] Implement AddFamilyPanel.svelte
  - [ ] Add form inputs
  - [ ] Add form validation
  - [ ] Add dynamic child name inputs
  - [ ] Add submit/cancel handlers
  - [ ] Add data-testid attributes
  - [ ] Write component tests

### 4.4 Main App Component
- [ ] Implement App.svelte (or +page.svelte)
  - [ ] Wire up all stores
  - [ ] Add search input with clear button
  - [ ] Add family list rendering
  - [ ] Add filtered/sorted family logic
  - [ ] Add auto-expand on search logic
  - [ ] Add success toast rendering
  - [ ] Add data-testid attributes
  - [ ] Connect all event handlers

---

## Phase 5: Run Tests

### 5.1 Unit Tests
- [ ] Run all utility function tests
- [ ] Run all store tests
- [ ] Run SessionIndicator component tests
- [ ] Run SuccessToast component tests
- [ ] Run ChildCheckInButton component tests
- [ ] Run FamilyCard component tests
- [ ] Run AddFamilyPanel component tests
- [ ] Verify 100% pass rate

### 5.2 Integration Tests
- [ ] Run search + expand integration tests
- [ ] Run check-in + undo timer integration tests
- [ ] Run family visibility integration tests
- [ ] Run add family integration tests
- [ ] Verify 100% pass rate

### 5.3 E2E Tests
- [ ] Run full Playwright suite against Svelte app
- [ ] Compare results with React baseline
- [ ] Document any differences

---

## Phase 6: Debug & Iterate

### 6.1 Fix Failing Tests
- [ ] Identify all failing E2E tests
- [ ] Debug behavior mismatches
- [ ] Fix Svelte component implementations
- [ ] Re-run tests until 100% pass rate

### 6.2 Visual Regression Testing
- [ ] Take screenshots of all Svelte app states
- [ ] Compare with React baseline screenshots
- [ ] Fix styling discrepancies
- [ ] Verify animations match

### 6.3 Edge Cases
- [ ] Test empty state (no families)
- [ ] Test search with no results
- [ ] Test undo timer expiration edge cases
- [ ] Test adding family with empty names
- [ ] Test rapid check-in/undo interactions
- [ ] Test search query auto-expand behavior
- [ ] Test family visibility after full check-in

### 6.4 Accessibility Audit
- [ ] Test keyboard navigation (Tab, Enter, Escape)
- [ ] Test screen reader announcements
- [ ] Verify ARIA labels and roles
- [ ] Test focus management
- [ ] Verify color contrast ratios

### 6.5 Performance Testing
- [ ] Measure initial load time
- [ ] Measure search performance with large datasets
- [ ] Measure re-render performance
- [ ] Compare with React baseline
- [ ] Optimize if needed

---

## Phase 7: Cross-Browser Testing

### 7.1 Browser Compatibility
- [ ] Run E2E suite on Chromium
- [ ] Run E2E suite on Firefox
- [ ] Run E2E suite on WebKit
- [ ] Fix any browser-specific issues

### 7.2 Mobile Testing
- [ ] Test responsive layout on mobile viewport
- [ ] Test touch interactions
- [ ] Test mobile keyboard behavior

---

## Phase 8: Cleanup & Documentation

### 8.1 Code Cleanup
- [ ] Remove React prototype code (or move to archive)
- [ ] Remove React dependencies from package.json
- [ ] Remove unused utilities/hooks
- [ ] Clean up test files
- [ ] Update .gitignore if needed

### 8.2 Documentation
- [ ] Update README with Svelte setup instructions
- [ ] Document component APIs
- [ ] Document store usage
- [ ] Add inline code comments where needed
- [ ] Create development guide

### 8.3 Final Verification
- [ ] Run all tests one final time
- [ ] Verify build succeeds
- [ ] Test production build
- [ ] Verify dev server works
- [ ] Code review

---

## Success Criteria

- ✅ All E2E tests pass (100% parity with React)
- ✅ All unit and integration tests pass
- ✅ Visual appearance matches React prototype
- ✅ Animations and transitions work smoothly
- ✅ Accessibility requirements met (WCAG AA)
- ✅ Performance is equal to or better than React
- ✅ Cross-browser compatibility verified
- ✅ Code is clean, documented, and maintainable

---

## Notes

- Use `data-testid` attributes consistently for all interactive elements
- Maintain same naming conventions as React prototype where possible
- Svelte stores should mirror React hook behavior
- Keep component structure similar to ease migration
- Focus on functional parity first, optimizations second
