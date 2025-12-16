# Mobile Family Card Expand/Collapse Fix

## Issue
Family cards on the checkin page could not be expanded on mobile devices (screen width < 768px). Clicks on the family header were not registering properly.

## Root Cause
The mobile layout had a nested `<button>` element inside the family header, which created a small clickable area. This pattern didn't work well on mobile touch devices.

## Solution
Changed the mobile layout to match the checkout page pattern:
- Made the **entire header div clickable** instead of just a button inside it
- Added `cursor-pointer`, `role="button"`, `tabindex="0"` to the outer div
- Added `active:bg-slate-100` for visual feedback on mobile touch
- Moved onclick/onkeydown handlers to the outer div
- The `toggleFamily` function already prevents button clicks from triggering expansion (lines 57-62)

## Changes Made
**File:** `/workspace/check-ins/frontend/src/lib/components/checkin/CheckinExpandableTable.svelte`

**Lines 152-234:** Restructured the mobile family header from:
```svelte
<div class="bg-slate-50 p-2.5 sm:p-3">
  <button onclick={...}>
    <!-- Chevron and family info -->
  </button>
  <div onclick={(e) => e.stopPropagation()}>
    <!-- Action buttons -->
  </div>
</div>
```

To:
```svelte
<div
  class="bg-slate-50 p-2.5 sm:p-3 cursor-pointer active:bg-slate-100"
  onclick={(e) => toggleFamily(family.id, e)}
  role="button"
  tabindex="0"
  ...
>
  <div class="flex items-start justify-between gap-2">
    <!-- Chevron and family info -->
    <!-- Action buttons -->
  </div>
</div>
```

## Testing Results

### Manual Testing with Playwright (Mobile - 375x667)
✅ **Before fix:** Card collapsed, showing right chevron
✅ **After clicking header:** Card expanded successfully, showing down chevron and children list
✅ **After clicking again:** Card collapsed successfully

### Manual Testing with Playwright (Desktop - 1024x768)
✅ **Table layout:** Still works perfectly
✅ **Expand/collapse:** Works on desktop
✅ **No regressions:** Desktop functionality unchanged

### E2E Tests
The existing E2E test failures are unrelated to this fix - they're due to outdated test fixtures using deprecated `qr_token` field.

## Success Criteria
✅ Mobile cards expand/collapse when clicking anywhere on header
✅ Action buttons don't trigger expansion (handled by toggleFamily function)
✅ Desktop table layout still works
✅ Keyboard navigation works (Tab + Enter/Space)
✅ Visual feedback on touch (active:bg-slate-100)

## Screenshots
- Mobile collapsed: `/tmp/playwright-output/checkin-mobile-before-click.png`
- Mobile expanded: `/tmp/playwright-output/checkin-mobile-after-click-expanded.png`
- Desktop view: `/tmp/playwright-output/checkin-desktop-view.png`
- Desktop expanded: `/tmp/playwright-output/checkin-desktop-expanded.png`

## Date
2025-12-16
