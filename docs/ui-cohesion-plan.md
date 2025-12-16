# UI Cohesion Plan: Checkout, Checkin, and Print Queue Pages

**Date:** 2025-12-16
**Goal:** Create a visually cohesive design across the three main pages by reusing components and establishing consistent patterns.

## Current State Analysis

### Checkout Page (/checkout)
**Strengths:**
- ✅ Clean expandable table design (CheckoutExpandableTable)
- ✅ Responsive mobile/desktop layouts
- ✅ Sticky search box with consistent positioning
- ✅ Professional empty state with dashed border
- ✅ Session indicator at top
- ✅ Consistent button styling (blue-600)
- ✅ Smooth hover states and transitions

**Components Used:**
- `CheckoutExpandableTable` (custom, excellent design)
- `SearchBox` (shared)
- `SessionIndicator` (shared)
- `EmptyState` (shared UI component)
- `Alert` (shared UI component)
- `Button`, `Icon` (shared UI components)

### Checkin Page (/checkin)
**Needs Improvement:**
- ⚠️ Uses custom `FamilyCard` component with different visual style
- ⚠️ Cards have border-slate-300 vs checkout's table approach
- ⚠️ Different header structure (blue-900 text vs checkout's lighter approach)
- ⚠️ Custom empty state implementation instead of using EmptyState component
- ⚠️ Different expansion patterns (cards vs table rows)
- ✅ Good: Sticky search box matches checkout
- ✅ Good: Session indicator matches checkout

**Components Used:**
- `FamilyCard` (custom, inconsistent with checkout design)
- `SearchBox` (shared, good)
- `SessionIndicator` (shared, good)
- Custom empty state (should use EmptyState component)
- Custom error alert (should use Alert component)

### Print Queue Page (/print-queue)
**Strengths:**
- ✅ Excellent EmptyState usage ("No labels need printing")
- ✅ Uses PrintQueueTable component
- ✅ Clean expandable section for recently printed
- ✅ Consistent Alert components

**Needs Improvement:**
- ⚠️ Different container styling (container mx-auto vs max-w-4xl)
- ⚠️ Table uses neutral-* colors vs slate-* colors on other pages
- ⚠️ Different padding structure (p-4 vs p-3 md:p-5)
- ⚠️ No sticky search (doesn't have search, but pattern should be consistent)

**Components Used:**
- `PrintQueueTable` (custom, uses neutral-* colors)
- `EmptyState` (shared, excellent usage)
- `ExpandableSection` (shared UI component)
- `Alert`, `Button`, `Icon` (shared UI components)

## Design System Decisions

### Color Palette
**Primary Decision: Use `slate-*` consistently (not `neutral-*`)**
- Headers: `slate-700`
- Body text: `slate-900`
- Secondary text: `slate-500`, `slate-600`
- Borders: `slate-200`, `slate-300`
- Backgrounds: `slate-50`, `slate-100`
- Primary actions: `blue-600` hover:`blue-700`

### Container & Layout Standards
```svelte
<!-- Standard page container -->
<div class="min-h-screen bg-slate-100">
  <div class="max-w-4xl mx-auto p-3 md:p-5">
    <!-- Content -->
  </div>
</div>

<!-- Sticky search pattern -->
<div class="sticky top-0 z-10 bg-slate-100 pb-2 -mx-3 px-3 md:-mx-5 md:px-5">
  <SearchBox ... />
</div>
```

### Empty State Pattern
**Use EmptyState component consistently:**
```svelte
<EmptyState
  type="empty"
  title={$t('page.noItems')}
  description={$t('page.noItemsDescription')}
>
  {#snippet icon()}
    <Icon name="check-circle" size="xl" />
  {/snippet}
</EmptyState>
```

### Table/List Display Pattern
**Standard table structure:**
- Rounded container: `rounded-lg border-2 border-slate-300`
- Header background: `bg-slate-50`
- Border separation: `border-b border-slate-200`
- Hover states: `hover:bg-slate-50`
- Text sizes: `text-sm` for headers, normal for content

### Expandable Pattern
**Two approaches based on data structure:**
1. **Family-based (checkout, checkin):** Use expandable table/card pattern
2. **Flat list (print-queue):** Use simple table with ExpandableSection for secondary views

## Implementation Plan

### Phase 1: Shared Component Consolidation
**Goal:** Create reusable components that work across all pages

#### 1.1 Create `ExpandableListTable` Component
**Location:** `frontend/src/lib/components/ui/ExpandableListTable.svelte`

**Purpose:** Generic expandable table that works for both families (checkout/checkin) and flat lists

**Props:**
- `items`: Array of items with optional children
- `columns`: Column configuration
- `onExpand`: Expansion callback
- `renderRow`: Custom row renderer (slot/snippet)
- `renderExpandedContent`: Custom expanded content renderer

**Benefits:**
- Reusable across checkout and checkin
- Consistent styling
- Mobile/desktop responsive built-in
- Reduces code duplication

#### 1.2 Update EmptyState Component
**Location:** `frontend/src/lib/components/ui/EmptyState.svelte`

**Changes:**
- Ensure it uses `slate-*` colors consistently
- Add standard icon support for common cases
- Current implementation is good, just verify color consistency

#### 1.3 Create `PageHeader` Component
**Location:** `frontend/src/lib/components/ui/PageHeader.svelte`

**Purpose:** Consistent page header with title and optional actions

```svelte
<PageHeader title={$t('page.title')}>
  {#snippet actions()}
    <Button>...</Button>
  {/snippet}
</PageHeader>
```

#### 1.4 Create `StickySearchBox` Component
**Location:** `frontend/src/lib/components/ui/StickySearchBox.svelte`

**Purpose:** Wrap SearchBox with consistent sticky positioning

### Phase 2: Update Checkin Page
**Goal:** Align checkin page with checkout's superior design

#### 2.1 Replace FamilyCard with Expandable Table Pattern
- Create new `CheckinExpandableTable` component (similar to `CheckoutExpandableTable`)
- Support family expansion with child details
- Include ticket assignment UI within expansion
- Maintain undo functionality with better visual integration

#### 2.2 Standardize Empty States
- Replace custom empty state div with `EmptyState` component
- Match checkout's messaging and icon usage

#### 2.3 Update Error Handling
- Replace custom error div with `Alert` component
- Match checkout's alert positioning and styling

#### 2.4 Container & Layout Updates
- Ensure consistent padding: `p-3 md:p-5`
- Use `max-w-4xl` container
- Match checkout's sticky search implementation

### Phase 3: Update Print Queue Page
**Goal:** Align print-queue with common design patterns

#### 3.1 Update PrintQueueTable Color Scheme
- Change from `neutral-*` to `slate-*` colors
- Update header background to `bg-slate-50`
- Update borders to `border-slate-200/300`
- Update text colors to match slate palette

#### 3.2 Container Standardization
- Change container to match checkout/checkin pattern
- Update padding to `p-3 md:p-5`
- Use `max-w-4xl` instead of `max-w-7xl`

#### 3.3 Enhance Empty State
- Current EmptyState usage is excellent, keep it
- Ensure colors match slate palette

### Phase 4: Cross-Page Pattern Library
**Goal:** Document and enforce consistent patterns

#### 4.1 Create Design System Documentation
**Location:** `docs/frontend-design-system.md`

Document:
- Color usage guidelines
- Component selection guide
- Layout patterns
- Spacing standards
- Typography scale
- Icon usage

#### 4.2 Create Storybook/Component Showcase (Optional)
- Visual reference for all shared components
- Interactive examples
- Props documentation

## Component Reuse Matrix

| Component | Checkout | Checkin | Print-Queue | Status |
|-----------|----------|---------|-------------|--------|
| `SessionIndicator` | ✅ | ✅ | ❌ N/A | ✅ Shared |
| `SearchBox` | ✅ | ✅ | ❌ N/A | ✅ Shared |
| `EmptyState` | ✅ | ⚠️ Custom | ✅ | ⚠️ Needs update |
| `Alert` | ✅ | ⚠️ Custom | ✅ | ⚠️ Needs update |
| `Button` | ✅ | ✅ | ✅ | ✅ Shared |
| `Icon` | ✅ | ✅ | ✅ | ✅ Shared |
| `ExpandableSection` | ❌ | ❌ | ✅ | ⚠️ Potential use |
| Expandable Table | ✅ Custom | ❌ Cards | ✅ Table | 🔄 Needs creation |

## Detailed Task Breakdown

### Priority 1 (High Impact, Foundational)
1. **Create ExpandableListTable component** - Replaces custom implementations
2. **Update EmptyState color scheme** - Ensures consistency
3. **Replace checkin FamilyCard with table pattern** - Biggest visual change
4. **Update PrintQueueTable colors** - Quick wins

### Priority 2 (Visual Consistency)
5. **Standardize page containers** - All pages use same wrapper
6. **Unify sticky search pattern** - Same implementation everywhere
7. **Update error/alert components** - Remove custom implementations
8. **Create PageHeader component** - Consistent page titles

### Priority 3 (Polish & Documentation)
9. **Create design system docs** - Future reference
10. **Add prop type consistency** - Ensure all components use similar prop patterns
11. **Accessibility audit** - Ensure all interactive elements are accessible
12. **Performance optimization** - Reduce bundle size with shared components

## Expected Benefits

### Code Quality
- **Reduced code duplication:** ~30-40% reduction in component code
- **Easier maintenance:** Single source of truth for patterns
- **Better type safety:** Shared interfaces across components

### User Experience
- **Consistent interactions:** Same expansion, hover, click behaviors
- **Visual harmony:** Unified color palette and spacing
- **Reduced cognitive load:** Users learn patterns once

### Developer Experience
- **Faster feature development:** Reusable components reduce implementation time
- **Clear patterns:** New developers understand structure quickly
- **Better testing:** Shared components = shared tests

## Migration Strategy

### Approach: Incremental Updates
1. **Build new components** alongside existing ones
2. **Test in isolation** before integrating
3. **Update one page at a time** (Print Queue → Checkin → Polish)
4. **Maintain backward compatibility** during transition
5. **Clean up old components** after migration

### Testing Strategy
- Visual regression testing with screenshots
- E2E tests for each page before/after
- Accessibility testing with screen readers
- Mobile responsiveness testing

## Success Metrics

- [ ] All three pages use same color palette (slate-*)
- [ ] All three pages use same container structure
- [ ] EmptyState component used consistently
- [ ] Alert component used instead of custom error divs
- [ ] At least 2 shared expandable/table components created
- [ ] Code reduction of 30%+ in page-specific components
- [ ] No visual regressions in E2E tests
- [ ] Accessibility score maintained or improved

## Next Steps

1. **Get approval** on this design plan
2. **Delegate to frontend-test-driven-dev agent** for implementation
3. **Start with Phase 1** (shared components)
4. **Iterate through phases** with reviews after each
5. **Document learnings** in design system docs
