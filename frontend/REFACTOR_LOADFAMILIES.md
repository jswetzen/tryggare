# Refactor: In-Place Merge for loadFamilies()

## Overview

Currently, `loadFamilies()` completely replaces the `families` array with fresh API data. This causes problems:
- **Loses local state**: Undo timers (`checkInActionId`, `checkInRecordId`, `checkInTime`) are lost
- **Poor UX**: Loading spinner appears, scroll position resets, expanded families collapse
- **Excessive reloads**: WebSocket messages trigger full API calls when another station checks in a child

**Solution**: Refactor `loadFamilies()` to merge fresh API data with existing local state instead of replacing everything.

## Files to Modify

1. **Create new utility**: `frontend/src/lib/checkin/utils/mergeFamilies.ts`
   - Extract the `mergeFamilies()` function from the test file
   - Add proper TypeScript types
   - Export for use in components

2. **Update page component**: `frontend/src/routes/checkin/+page.svelte`
   - Import the new `mergeFamilies()` utility
   - Modify `loadFamilies()` to use merge instead of replace
   - Keep the `loading` state management

3. **Tests already exist**: `frontend/src/routes/checkin/loadFamilies.test.ts`
   - 16 comprehensive tests already written and passing
   - Update imports once utility is extracted
   - All tests should continue passing

## Implementation Steps

### Step 1: Extract mergeFamilies utility

Create `frontend/src/lib/checkin/utils/mergeFamilies.ts`:

```typescript
import type { Family, Child } from '$lib/checkin/types';
import type { FamilyApiResponse } from '$lib/api/types';

/**
 * Transform API family response to frontend Family type
 * Note: Does NOT include local-only fields like checkInActionId
 */
function transformFamilyResponse(apiFamily: FamilyApiResponse): Omit<Family, 'children'> & {
  children: Omit<Child, 'checkInActionId' | 'checkInRecordId' | 'checkInTime'>[]
} {
  return {
    id: apiFamily.id,
    last_name: apiFamily.last_name,
    display_name: apiFamily.display_name,
    name: apiFamily.display_name,
    children: apiFamily.children.map((child) => ({
      id: child.id,
      first_name: child.first_name,
      last_name: child.last_name,
      name: `${child.first_name} ${child.last_name}`,
      ticket: child.ticket_type || 'none',
      ticket_type: child.ticket_type || 'none',
      ticket_details: child.ticket_details,
      checkedIn: child.is_checked_in || false,
      family: child.family,
      birthdate: child.birthdate,
      allergies: child.allergies,
      notes: child.notes,
      qr_token: child.qr_token,
    })),
    parents: apiFamily.parents,
    last_participation_date: apiFamily.last_participation_date,
  };
}

/**
 * Merges fresh API family data with existing local state
 *
 * Preserves local-only fields:
 * - checkInActionId: UUID linking to undo timer
 * - checkInRecordId: Backend record ID for API calls
 * - checkInTime: Formatted time string for display
 *
 * Updates from API:
 * - checkedIn status (backend is source of truth)
 * - All other child/family properties
 * - Family and child additions/removals
 *
 * @param existingFamilies - Current local state with undo timers
 * @param apiFamilies - Fresh data from backend API
 * @returns Merged families array with preserved local state
 */
export function mergeFamilies(
  existingFamilies: Family[],
  apiFamilies: FamilyApiResponse[]
): Family[] {
  // Transform API responses
  const freshFamilies = apiFamilies.map(transformFamilyResponse);

  // Create map of existing families for O(1) lookup
  const existingFamilyMap = new Map(
    existingFamilies.map(f => [f.id, f])
  );

  // Merge fresh data with existing local state
  return freshFamilies.map(freshFamily => {
    const existingFamily = existingFamilyMap.get(freshFamily.id);

    if (!existingFamily) {
      // New family - return as-is (with undefined local fields)
      return freshFamily as Family;
    }

    // Create map of existing children for O(1) lookup
    const existingChildMap = new Map(
      existingFamily.children.map(c => [c.id, c])
    );

    // Merge children, preserving local state
    const mergedChildren: Child[] = freshFamily.children.map(freshChild => {
      const existingChild = existingChildMap.get(freshChild.id);

      if (!existingChild) {
        // New child - return as-is
        return freshChild as Child;
      }

      // Merge: use fresh API data but preserve local-only fields
      return {
        ...freshChild,
        // Preserve local check-in state for undo timers
        checkInActionId: existingChild.checkInActionId,
        checkInRecordId: existingChild.checkInRecordId,
        checkInTime: existingChild.checkInTime,
      } as Child;
    });

    return {
      ...freshFamily,
      children: mergedChildren,
    } as Family;
  });
}
```

### Step 2: Update loadFamilies() in +page.svelte

Find this code in `frontend/src/routes/checkin/+page.svelte`:

```typescript
async function loadFamilies() {
  try {
    loading = true;
    error = null;
    const response = await checkinApi.getFamilies();
    families = response.map(transformFamilyResponse);  // ❌ Complete replacement
  } catch (err) {
    const apiError = err as ApiError;
    error = apiError.message || 'Failed to load families';
    console.error('Error loading families:', err);
  } finally {
    loading = false;
  }
}
```

Replace with:

```typescript
import { mergeFamilies } from '$lib/checkin/utils/mergeFamilies';

async function loadFamilies() {
  try {
    loading = true;
    error = null;
    const response = await checkinApi.getFamilies();
    families = mergeFamilies(families, response);  // ✅ In-place merge
  } catch (err) {
    const apiError = err as ApiError;
    error = apiError.message || 'Failed to load families';
    console.error('Error loading families:', err);
  } finally {
    loading = false;
  }
}
```

**Key change**: `mergeFamilies(families, response)` instead of `response.map(transformFamilyResponse)`

**Note**: Remove the old `transformFamilyResponse()` function from `+page.svelte` since it's now in the utility.

### Step 3: Update test imports

In `frontend/src/routes/checkin/loadFamilies.test.ts`:

Replace this:
```typescript
// Mock transform function (simplified version of actual)
function transformFamilyResponse(apiFamily: FamilyApiResponse): ... {
  // ... inline implementation
}

function mergeFamilies(...) {
  // ... inline implementation
}
```

With this:
```typescript
import { mergeFamilies } from '$lib/checkin/utils/mergeFamilies';
```

Remove the inline function definitions since they're now imported from the utility.

### Step 4: Run tests

```bash
cd /workspace/check-ins/frontend
npm test -- loadFamilies.test.ts
```

**Expected result**: All 16 tests should pass ✅

### Step 5: Verify in browser

1. Start the dev server (should already be running)
2. Open check-in page at `http://localhost:5173/checkin`
3. Check in a child
4. Verify undo timer appears
5. In another browser window/tab, check in a different child
6. **Verify in first window**:
   - First child's undo timer still shows (preserved local state)
   - Second child appears as checked in (updated from WebSocket/reload)
   - No loading spinner
   - Page doesn't reset/scroll

## Benefits of This Refactor

### Before (Current)
- `loadFamilies()` → Complete array replacement
- Loses all local state (undo timers lost)
- Every WebSocket message causes full page reload
- Poor UX: loading spinners, scroll resets

### After (Refactored)
- `loadFamilies()` → Smart merge preserving local state
- Undo timers preserved during reload
- WebSocket updates less disruptive (still full API call, but state preserved)
- Better UX: no state loss, smoother updates

### Next Phase (Future Enhancement)
Once this refactor is stable, we can further optimize by:
- Using incremental WebSocket updates (no API call at all)
- Only updating the specific child/family that changed
- Even better performance and UX

## Testing Checklist

- [ ] Extract `mergeFamilies` utility function
- [ ] Update `loadFamilies()` to use merge
- [ ] Remove old `transformFamilyResponse()` from page component
- [ ] Update test imports
- [ ] All 16 tests pass
- [ ] Manual browser test: undo timer survives reload
- [ ] Manual multi-window test: first window preserves timers when second window checks in
- [ ] No TypeScript errors
- [ ] No console errors

## Edge Cases Covered by Tests

1. ✅ Preserves undo timers during reload
2. ✅ Updates backend check-in status
3. ✅ Handles new families/children from API
4. ✅ Handles removed families/children
5. ✅ Handles multiple children with undo timers
6. ✅ Handles backend state changes (child checked out)
7. ✅ Maintains API-specified family order
8. ✅ Works with empty arrays (edge cases)

## Rollback Plan

If issues arise:
1. Revert `+page.svelte` changes
2. Restore original `loadFamilies()` implementation
3. Keep tests and utility for future attempts

## Success Criteria

✅ All tests pass
✅ Undo timers persist during `loadFamilies()` calls
✅ WebSocket updates don't lose local state
✅ No TypeScript errors
✅ No degradation in existing functionality
