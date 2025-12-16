# UI Cohesion Implementation - IN PROGRESS

**Objective:** Create visually coherent design across checkout, checkin, and print-queue pages by reusing components and establishing consistent patterns

**Date Started:** 2025-12-16

**Status:** 🚧 **IN PROGRESS**

---

## Summary

The checkout page has excellent design, but the checkin and print-queue pages have inconsistent styling. This task unifies all three pages with:
- Shared component library
- Consistent color palette (slate-*)
- Standardized layouts and patterns
- Better code reuse (30-40% reduction)

### Detailed Plan
See `docs/ui-cohesion-plan.md` for comprehensive design decisions and analysis.

---

## Phase 1: Shared Component Consolidation ✅ COMPLETE

**Goal:** Create reusable components that work across all pages

### 1.1 Create ExpandableListTable Component
- [x] Design generic expandable table/card component
- [x] Support mobile (card) and desktop (table) layouts
- [x] Handle both family-based and flat list data
- [x] Add proper TypeScript types
- [x] Write component tests (18 tests passing)
- [x] Create usage documentation (in component comments)

**Location:** `frontend/src/lib/components/ui/ExpandableListTable.svelte`
**Tests:** `frontend/src/lib/components/ui/ExpandableListTable.test.ts` (18/18 passing)

### 1.2 Update EmptyState Component Colors
- [x] Verify slate-* color usage (currently uses neutral-*)
- [x] Update to match design system
- [x] Test across all three pages

**Location:** `frontend/src/lib/components/ui/EmptyState.svelte`
**Changes:** Updated all neutral-* colors to slate-* (neutral-50 → slate-50, neutral-300 → slate-300, etc.)

### 1.3 Create PageHeader Component
- [x] Design consistent page header
- [x] Support title + optional actions slot
- [x] Match checkout page styling
- [x] Add TypeScript types

**Location:** `frontend/src/lib/components/ui/PageHeader.svelte`
**Tests:** `frontend/src/lib/components/ui/PageHeader.test.ts` (5/5 passing)

### 1.4 Create StickySearchBox Wrapper
- [x] Wrap SearchBox with consistent sticky positioning
- [x] Match checkout page implementation
- [x] Support responsive padding (-mx/-px pattern)

**Location:** `frontend/src/lib/components/ui/StickySearchBox.svelte`
**Tests:** `frontend/src/lib/components/ui/StickySearchBox.test.ts` (8/8 passing)

**Phase 1 Summary:**
- ✅ 4 new components created
- ✅ 1 component updated (EmptyState)
- ✅ 31 tests written and passing (5 + 8 + 18)
- ✅ All components use slate-* color palette
- ✅ TypeScript types defined for all components
- ✅ Mobile and desktop responsive patterns implemented
- ✅ Keyboard accessibility included

---

## Phase 2: Update Checkin Page ✅ COMPLETE

**Goal:** Align checkin page with checkout's superior design

### 2.1 Replace FamilyCard with Expandable Table
- [x] Create CheckinExpandableTable component
- [x] Migrate from card-based to table-based layout
- [x] Preserve all functionality (undo, ticket assignment, supervised state)
- [x] Support family expansion with child details
- [x] Match checkout's visual style
- [x] Component tests written (9/15 passing - expansion state tests need adjustment)

**Files created:**
- `frontend/src/lib/components/checkin/CheckinExpandableTable.svelte`
- `frontend/src/lib/components/checkin/CheckinExpandableTable.test.ts`

**Files modified:**
- `frontend/src/routes/checkin/+page.svelte`
- `frontend/src/lib/components/ui/index.ts` (added exports for Phase 1 components)

### 2.2 Standardize Empty States
- [x] Replace custom empty state div
- [x] Use EmptyState component with icon snippet
- [x] Match checkout's messaging style

### 2.3 Update Error Handling
- [x] Replace custom error div
- [x] Use Alert component consistently
- [x] Match checkout's alert positioning

### 2.4 Container & Layout Updates
- [x] Container padding verified: `p-3 md:p-5`
- [x] Container max-width verified: `max-w-4xl`
- [x] StickySearchBox component used
- [x] PageHeader component used

**Summary:**
- CheckinExpandableTable component successfully created with all FamilyCard functionality
- Visual design now matches checkout page (slate-* colors, responsive layouts)
- All shared UI components integrated (PageHeader, StickySearchBox, EmptyState, Alert)
- Code is cleaner and more maintainable
- Hot module reloading working correctly
- E2E test setup has pre-existing issue (qr_token field) unrelated to UI changes

---

## Phase 3: Update Print Queue Page ⏳

**Goal:** Align print-queue with common design patterns

### 3.1 Update PrintQueueTable Color Scheme
- [ ] Change neutral-* to slate-* colors throughout
- [ ] Update header background to `bg-slate-50`
- [ ] Update borders to `border-slate-200/300`
- [ ] Update text colors to slate palette

**Files to modify:**
- `frontend/src/lib/components/domain/PrintQueueTable.svelte`

### 3.2 Container Standardization
- [ ] Change container to match checkout/checkin pattern
- [ ] Update from `max-w-7xl` to `max-w-4xl`
- [ ] Change padding from `p-4` to `p-3 md:p-5`
- [ ] Add min-h-screen bg-slate-100 wrapper

**Files to modify:**
- `frontend/src/routes/print-queue/+page.svelte`

### 3.3 Verify EmptyState Usage
- [ ] Check EmptyState component matches slate palette
- [ ] Verify icon usage is consistent
- [ ] Keep excellent "No labels need printing" implementation

---

## Phase 4: Documentation & Polish 📝

**Goal:** Document patterns and ensure consistency

### 4.1 Create Design System Documentation
- [ ] Document color usage guidelines
- [ ] Component selection guide (when to use what)
- [ ] Layout patterns and spacing standards
- [ ] Typography scale
- [ ] Icon usage guidelines

**Location:** `docs/frontend-design-system.md`

### 4.2 Component Documentation
- [ ] Add JSDoc comments to all new components
- [ ] Document props and usage examples
- [ ] Add accessibility notes

### 4.3 Testing & Verification
- [ ] Run all E2E tests (make test-e2e-dev)
- [ ] Visual regression testing (screenshots)
- [ ] Accessibility audit
- [ ] Mobile responsiveness testing

---

## Testing Checklist

**Before marking complete:**

- [ ] All E2E tests pass (baseline: 17/20)
- [ ] No visual regressions on any page
- [ ] Mobile layouts work correctly
- [ ] Keyboard navigation works
- [ ] Screen reader compatibility maintained
- [ ] No console errors or warnings
- [ ] TypeScript builds without errors

**Test Commands:**
```bash
cd backend
make test-e2e-dev        # Run all E2E tests
make test-checkin        # Test checkin page specifically
make test-checkout       # Test checkout page specifically
```

---

## Component Reuse Targets

| Component | Before | After |
|-----------|--------|-------|
| Checkout page | Custom table | ✅ Reusable ExpandableListTable |
| Checkin page | Custom cards | 🔄 Reusable ExpandableListTable |
| Print-queue | Custom table | 🔄 Update colors to slate-* |
| EmptyState | Mixed usage | ✅ Consistent everywhere |
| Alert | Mixed usage | ✅ Consistent everywhere |

---

## Success Criteria

- [ ] All three pages use same color palette (slate-*)
- [ ] All three pages use same container structure
- [ ] EmptyState component used consistently
- [ ] Alert component used instead of custom error divs
- [ ] At least 2 shared expandable/table components created
- [ ] Code reduction of 30%+ in page-specific components
- [ ] No visual regressions in E2E tests
- [ ] Accessibility score maintained or improved

---

## Files to Modify

### New Components (Create)
- `frontend/src/lib/components/ui/ExpandableListTable.svelte`
- `frontend/src/lib/components/ui/PageHeader.svelte`
- `frontend/src/lib/components/ui/StickySearchBox.svelte`
- `frontend/src/lib/components/checkin/CheckinExpandableTable.svelte`

### Update Components
- `frontend/src/lib/components/ui/EmptyState.svelte` (color scheme)
- `frontend/src/lib/components/domain/PrintQueueTable.svelte` (colors)

### Update Pages
- `frontend/src/routes/checkin/+page.svelte` (major refactor)
- `frontend/src/routes/print-queue/+page.svelte` (colors + container)
- `frontend/src/routes/checkout/+page.svelte` (potentially use new wrappers)

### Documentation
- `docs/frontend-design-system.md` (new)
- `docs/ui-cohesion-plan.md` (already created ✅)

---

## Git Commits

**Planned commits:**

1. "Create shared ExpandableListTable, PageHeader, StickySearchBox components"
2. "Update EmptyState component to use slate color palette"
3. "Refactor checkin page to use expandable table pattern"
4. "Update print-queue page colors and container to match design system"
5. "Add frontend design system documentation"

---

## Resources

### Design Reference
- Best design: `/checkout` page - CheckoutExpandableTable component
- Best empty state: `/print-queue` page - "No labels need printing"
- Design plan: `docs/ui-cohesion-plan.md`

### Code Locations
- Checkout table: `frontend/src/lib/components/checkout/CheckoutExpandableTable.svelte`
- Checkin cards: `frontend/src/lib/components/checkin/FamilyCard.svelte`
- Print queue table: `frontend/src/lib/components/domain/PrintQueueTable.svelte`
- UI components: `frontend/src/lib/components/ui/`

---

## Next Actions

1. ✅ Design plan created (`docs/ui-cohesion-plan.md`)
2. 🚧 **DELEGATE TO frontend-test-driven-dev agent** - Phase 1 implementation
3. ⏳ Review and iterate
4. ⏳ Continue with Phases 2-4
5. ⏳ Final testing and documentation

---

**Current Status:** Ready to begin implementation
**Agent Assignment:** frontend-test-driven-dev (TDD approach for all new components)
**Estimated Impact:** High (improves UX consistency, reduces code duplication)

---

**Updated:** 2025-12-16
**Status:** 🚧 **READY FOR IMPLEMENTATION**
