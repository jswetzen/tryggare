# Undo Timer Fix - December 6, 2025

## Problem
After checking in a child, the undo timer countdown was not appearing. The button immediately showed "Checked In" instead of showing "Undo (30s)", "Undo (29s)", etc.

## Root Cause
The issue was with how remaining time was calculated in the `FamilyCard` component. The component was calling `getRemainingTime()` function which uses `get(undoActionsStore)` to retrieve the current state of the undo actions store. However, this approach was not properly reactive in the Svelte 5 context.

### Technical Details

**Before (Broken):**
```svelte
<!-- In FamilyCard.svelte -->
{@const childRemainingSeconds = child.checkInActionId && _tick >= 0 ? getRemainingTime(child.checkInActionId) : null}
```

The problem: Even though `_tick` was reactive and updated every second, the `getRemainingTime()` function call used `get(undoActionsStore)` which retrieves a snapshot of the store but doesn't establish a reactive dependency in this context.

**After (Fixed):**
```svelte
<!-- In +page.svelte -->
{@const childRemainingTimes = new Map(
  family.children
    .filter(c => c.checkInActionId)
    .map(c => [c.id, _tick >= 0 ? getRemainingTime(c.checkInActionId!) : null])
)}
```

The solution: Calculate all remaining times in the parent component (+page.svelte) where we have access to the reactive `undoActionsData` derived store, then pass them down to FamilyCard as a Map.

## Changes Made

### 1. `/workspace/check-ins/frontend/src/routes/checkin/+page.svelte`

**Added:** Calculation of `childRemainingTimes` Map in the reactive block (lines 682-686):
```typescript
{@const childRemainingTimes = new Map(
  family.children
    .filter(c => c.checkInActionId)
    .map(c => [c.id, _tick >= 0 ? getRemainingTime(c.checkInActionId!) : null])
)}
```

**Changed:** FamilyCard component props (line 701):
- Removed: `{getRemainingTime}`
- Added: `{childRemainingTimes}`

### 2. `/workspace/check-ins/frontend/src/lib/components/checkin/FamilyCard.svelte`

**Changed:** Component props interface (lines 18-44):
- Removed: `getRemainingTime: (actionId: string) => number | null`
- Added: `childRemainingTimes: Map<string, number | null>`

**Simplified:** Child remaining time calculation (line 140):
```typescript
// Before:
{@const childRemainingSeconds = child.checkInActionId && _tick >= 0 ? getRemainingTime(child.checkInActionId) : null}

// After:
{@const childRemainingSeconds = childRemainingTimes.get(child.id) ?? null}
```

## Why This Fix Works

1. **Proper Reactivity**: The `childRemainingTimes` Map is calculated in a reactive block (`{@const ...}`) in the parent component, which re-runs every time `_tick` updates (every second).

2. **Centralized Calculation**: All remaining time calculations happen in one place (+page.svelte) where we have clear access to the reactive `undoActionsData` store.

3. **Simple Data Flow**: FamilyCard now receives pre-calculated remaining times as a simple Map lookup, eliminating the need for it to understand the undo timer store's internals.

4. **Performance**: The Map provides O(1) lookup time for child remaining times.

## Testing

After this fix:
1. Check in a child
2. The button immediately shows "Undo (30s)"
3. The countdown updates every second: "Undo (29s)", "Undo (28s)", etc.
4. After 30 seconds, the button changes to "Checked In" (disabled)

## Files Modified
- `/workspace/check-ins/frontend/src/routes/checkin/+page.svelte`
- `/workspace/check-ins/frontend/src/lib/components/checkin/FamilyCard.svelte`
