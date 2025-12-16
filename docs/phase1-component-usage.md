# Phase 1 Component Usage Guide

**Date:** 2025-12-16
**Status:** Complete - All components ready for use in Phases 2-3

## Overview

Phase 1 created four new reusable UI components and updated one existing component to establish a consistent design foundation across the checkout, checkin, and print-queue pages.

## Component Catalog

### 1. PageHeader

**Purpose:** Consistent page header with title and optional action buttons

**Location:** `frontend/src/lib/components/ui/PageHeader.svelte`

**Props:**
- `title: string` - Page title text (required)
- `actions?: Snippet` - Optional snippet for action buttons
- `class?: string` - Additional CSS classes

**Usage Example:**
```svelte
<script>
  import PageHeader from '$lib/components/ui/PageHeader.svelte';
  import Button from '$lib/components/ui/Button.svelte';
</script>

<PageHeader title={$t('checkout.title')}>
  {#snippet actions()}
    <Button onclick={handleRefresh}>Refresh</Button>
  {/snippet}
</PageHeader>
```

**Styling:**
- Title: `text-3xl font-bold text-blue-900`
- Container margin: `mb-5`
- Flexbox layout with space-between for title and actions

---

### 2. StickySearchBox

**Purpose:** Wraps SearchBox component with consistent sticky positioning pattern

**Location:** `frontend/src/lib/components/ui/StickySearchBox.svelte`

**Props:**
- `value: string` (bindable) - Search query value
- `placeholder?: string` - Placeholder text
- `label?: string` - Optional label
- `onInput?: (value: string) => void` - Input callback
- `class?: string` - Additional CSS classes

**Usage Example:**
```svelte
<script>
  import StickySearchBox from '$lib/components/ui/StickySearchBox.svelte';

  let searchQuery = $state('');
</script>

<StickySearchBox
  bind:value={searchQuery}
  placeholder={$t('checkout.searchPlaceholder')}
/>
```

**Styling:**
- Position: `sticky top-0 z-10`
- Background: `bg-slate-100`
- Responsive padding: `-mx-3 px-3 md:-mx-5 md:px-5`
- Bottom spacing: `pb-2`

**Key Features:**
- Automatically applies sticky positioning
- Handles negative margins for edge-to-edge appearance
- Responsive padding that matches page container

---

### 3. ExpandableListTable

**Purpose:** Generic expandable table/card component for family-based data and flat lists

**Location:** `frontend/src/lib/components/ui/ExpandableListTable.svelte`

**Props:**
- `items: ListItem[]` - Array of items to display (required)
- `columns: Column[]` - Column configuration (required)
- `onToggle?: (itemId: string, isExpanded: boolean) => void` - Expansion callback
- `headerRow?: Snippet<[ListItem]>` - Custom header row snippet
- `expandedContent?: Snippet<[ListItem]>` - Custom expanded content snippet
- `class?: string` - Additional CSS classes

**TypeScript Types:**
```typescript
interface ListItem {
  id: string;
  [key: string]: any;
  children?: any[];
}

interface Column {
  key: string;
  label: string;
  align?: 'left' | 'right' | 'center';
  class?: string;
}
```

**Usage Example:**
```svelte
<script lang="ts">
  import ExpandableListTable from '$lib/components/ui/ExpandableListTable.svelte';

  const columns = [
    { key: 'name', label: 'Family Name' },
    { key: 'count', label: 'Children', align: 'right' }
  ];

  const items = [
    {
      id: '1',
      name: 'Smith Family',
      count: 2,
      children: [
        { id: '1a', name: 'John Smith' },
        { id: '1b', name: 'Jane Smith' }
      ]
    }
  ];

  function handleToggle(itemId: string, isExpanded: boolean) {
    console.log(`Item ${itemId} is now ${isExpanded ? 'expanded' : 'collapsed'}`);
  }
</script>

<ExpandableListTable
  {items}
  {columns}
  onToggle={handleToggle}
>
  {#snippet expandedContent(item)}
    <div class="space-y-2">
      {#each item.children as child}
        <div>{child.name}</div>
      {/each}
    </div>
  {/snippet}
</ExpandableListTable>
```

**Key Features:**
- Responsive design: Card layout on mobile, table layout on desktop
- Expandable rows/cards with chevron indicators
- Sticky header on desktop view
- Keyboard accessible (Enter/Space to expand)
- Only items with children are expandable
- Smooth transitions and hover states
- Slate color palette throughout

**Styling:**
- Container: `rounded-lg border-2 border-slate-300`
- Header: `bg-slate-50` with sticky positioning
- Hover: `hover:bg-slate-50`
- Borders: `border-slate-200` between rows
- Mobile cards: Rounded with border-slate-300

---

### 4. EmptyState (Updated)

**Purpose:** Consistent empty state display with dashed border design

**Location:** `frontend/src/lib/components/ui/EmptyState.svelte`

**Changes in Phase 1:**
- ✅ Updated from `neutral-*` to `slate-*` color palette
- `neutral-50` → `slate-50` (background)
- `neutral-300` → `slate-300` (border)
- `neutral-400` → `slate-400` (empty icon color)
- `neutral-500` → `slate-500` (description text)
- `neutral-700` → `slate-700` (title text)

**Props:**
- `type?: 'empty' | 'loading' | 'error' | 'success'` - State type (default: 'empty')
- `title: string` - Main heading text (required)
- `description?: string` - Optional description
- `icon?: Snippet` - Custom icon snippet
- `action?: Snippet` - Optional action buttons snippet
- `class?: string` - Additional CSS classes

**Usage Example:**
```svelte
<script>
  import EmptyState from '$lib/components/ui/EmptyState.svelte';
  import Icon from '$lib/components/ui/Icon.svelte';
</script>

<EmptyState
  type="empty"
  title={$t('checkout.noFamilies')}
  description={$t('checkout.noFamiliesDescription')}
>
  {#snippet icon()}
    <Icon name="users" size="xl" />
  {/snippet}
</EmptyState>
```

**Key Features:**
- Dashed border design for empty states
- Centered text and icon layout
- Support for different state types (empty, loading, error, success)
- Optional action buttons in footer

---

## Design System Standards

### Color Palette (Slate)

All components use the `slate-*` color palette consistently:

| Usage | Color Class | Hex |
|-------|-------------|-----|
| Headers | `slate-700` | Dark slate for headers |
| Body text | `slate-900` | Darkest slate for content |
| Secondary text | `slate-500`, `slate-600` | Medium slate |
| Borders | `slate-200`, `slate-300` | Light slate |
| Backgrounds | `slate-50`, `slate-100` | Lightest slate |

### Container Pattern

Standard page container used across all pages:
```svelte
<div class="min-h-screen bg-slate-100">
  <div class="max-w-4xl mx-auto p-3 md:p-5">
    <!-- Content -->
  </div>
</div>
```

### Responsive Breakpoints

- Mobile: `< 768px` (Tailwind default)
- Desktop: `≥ 768px` (using `md:` prefix)

### Accessibility

All components include:
- ✅ Semantic HTML elements
- ✅ ARIA labels where appropriate
- ✅ Keyboard navigation support
- ✅ Focus states
- ✅ Screen reader friendly markup

---

## Testing

### Test Coverage Summary

| Component | Tests | Status |
|-----------|-------|--------|
| PageHeader | 5 | ✅ Passing |
| StickySearchBox | 8 | ✅ Passing |
| ExpandableListTable | 18 | ✅ Passing |
| **Total** | **31** | **✅ All Passing** |

### Running Tests

```bash
# Run all Phase 1 component tests
cd frontend
npm test -- PageHeader StickySearchBox ExpandableListTable

# Run individual component tests
npm test -- PageHeader.test.ts
npm test -- StickySearchBox.test.ts
npm test -- ExpandableListTable.test.ts
```

### Test Categories

Each component has tests for:
1. **Rendering** - Component displays correctly
2. **Props** - All props work as expected
3. **Styling** - Correct CSS classes applied
4. **Interactions** - Click, keyboard events work
5. **Accessibility** - ARIA, tabindex, semantic HTML
6. **Edge cases** - Empty states, missing props

---

## Migration Path (Phases 2-3)

### Phase 2: Update Checkin Page

Use these components:
- ✅ `PageHeader` for title
- ✅ `StickySearchBox` for search
- ✅ `ExpandableListTable` for family list (replace FamilyCard)
- ✅ `EmptyState` for no families message

### Phase 3: Update Print Queue Page

Use these components:
- ✅ `PageHeader` for title
- ✅ `EmptyState` for no labels message (already using, just verify colors)
- Update `PrintQueueTable` colors to match slate palette

---

## Implementation Notes

### ExpandableListTable - Advanced Usage

The `ExpandableListTable` supports custom snippets for maximum flexibility:

**Custom Header Row:**
```svelte
<ExpandableListTable {items} {columns}>
  {#snippet headerRow(item)}
    <div class="flex items-center gap-2">
      <span class="font-medium">{item.name}</span>
      <Badge count={item.count} />
    </div>
  {/snippet}
</ExpandableListTable>
```

**Custom Expanded Content:**
```svelte
<ExpandableListTable {items} {columns}>
  {#snippet expandedContent(item)}
    <div class="p-4 space-y-3">
      {#each item.children as child}
        <ChildCard {child} />
      {/each}

      <select class="w-full">
        <option>Select parent...</option>
        {#each item.parents as parent}
          <option>{parent.name}</option>
        {/each}
      </select>
    </div>
  {/snippet}
</ExpandableListTable>
```

### StickySearchBox - Edge Cases

The component handles edge cases:
- Works with page containers of any width
- Negative margins compensate for container padding
- Z-index ensures it stays above content when scrolling
- Background color matches page container

---

## Files Created/Modified

### New Files Created
1. `frontend/src/lib/components/ui/PageHeader.svelte`
2. `frontend/src/lib/components/ui/PageHeader.test.ts`
3. `frontend/src/lib/components/ui/StickySearchBox.svelte`
4. `frontend/src/lib/components/ui/StickySearchBox.test.ts`
5. `frontend/src/lib/components/ui/ExpandableListTable.svelte`
6. `frontend/src/lib/components/ui/ExpandableListTable.test.ts`
7. `docs/phase1-component-usage.md` (this file)

### Files Modified
1. `frontend/src/lib/components/ui/EmptyState.svelte` - Color palette update
2. `CURRENT_TASKS.md` - Marked Phase 1 as complete

---

## Next Steps

Phase 1 is complete and all components are ready for use. The next steps are:

1. **Phase 2:** Update checkin page to use new components
   - Replace `FamilyCard` with `ExpandableListTable`
   - Use `PageHeader` for title
   - Use `StickySearchBox` for search
   - Use `EmptyState` for empty message

2. **Phase 3:** Update print-queue page
   - Use `PageHeader` for title
   - Update `PrintQueueTable` colors to slate palette
   - Verify `EmptyState` usage

3. **Phase 4:** Documentation and cleanup
   - Create comprehensive design system documentation
   - Remove deprecated components
   - Final testing and verification

---

**Phase 1 Status:** ✅ COMPLETE
**Date Completed:** 2025-12-16
**Components Ready:** 4 new + 1 updated
**Tests Passing:** 31/31
