# Timer Countdown Fix Summary

## Problem
The undo countdown timer was updating internally (the timer was running) but **not triggering UI reactivity** in Svelte. Users would see "Undo (30s)" and it would stay frozen at 30 seconds unless they interacted with the page (clicked, typed, etc).

## Root Cause
The `undoActionsWithTick` derived store was returning the same array reference every time it updated:

```typescript
// OLD - BROKEN
export const undoActionsWithTick = derived(
  [undoActionsStore, tickStore],
  ([$actions]) => $actions  // Same array reference = no reactivity
);
```

Even though `tickStore` was updating every second, Svelte couldn't detect changes because the returned value was the same object reference.

## Solution
Modified the derived store to return a **new object on every tick**, ensuring Svelte detects the change:

```typescript
// NEW - WORKING
export const undoActionsWithTick = derived(
  [undoActionsStore, tickStore],
  ([$actions, $tick]) => ({
    actions: $actions,
    tick: $tick,
  })
);
```

### Files Changed

1. **`/workspace/check-ins/frontend/src/lib/checkin/stores/undoTimer.ts`**
   - Modified `undoActionsWithTick` to return `{ actions, tick }` object
   - This creates a new object reference on every tick

2. **`/workspace/check-ins/frontend/src/routes/checkin/+page.svelte`**
   - Updated to extract `actions` from the store: `let undoActions = $derived(undoActionsData.actions);`
   - Removed the `{@const _tick = undoActions.length}` hack (no longer needed)

3. **`/workspace/check-ins/frontend/src/lib/components/checkin/FamilyCard.svelte`**
   - Same changes as +page.svelte
   - Removed the `_tick` hack

4. **`/workspace/check-ins/frontend/src/lib/checkin/stores/undoTimer.test.ts`**
   - Added 3 new tests to verify tick behavior:
     - `should update tick value every second when actions exist`
     - `should emit new object reference on each tick for Svelte reactivity`
     - `should stop tick interval when all actions are removed`

## How It Works

1. When an undo action is created, the store starts a 1-second interval
2. Every second, `tickStore` increments
3. The derived store creates a NEW object `{ actions, tick }`
4. Svelte detects the new object reference and re-renders components
5. Components call `getRemainingTime()` which calculates fresh countdown values
6. When all actions are removed, the interval stops (performance optimization)

## Testing

### Unit Tests
```bash
cd /workspace/check-ins/frontend
pnpm test undoTimer.test.ts
```

All 16 tests pass, including the new reactivity tests.

### Manual Browser Testing
1. Navigate to `http://localhost:8080/checkin`
2. Login (username: `admin`, password: `admin123`)
3. Expand a family and check in a child
4. Observe the "Undo (30s)" button
5. **Wait 3-5 seconds WITHOUT touching the page**
6. The countdown should automatically decrease: "Undo (25s)", "Undo (24s)", etc.

### Automated E2E Test
A Selenium test has been created at `/workspace/check-ins/backend/test_timer_countdown.py` that:
1. Logs in
2. Navigates to check-in page
3. Checks in a child
4. Waits 3 seconds without interaction
5. Verifies the countdown decreased by at least 2 seconds

## Performance Notes

- The tick interval only runs when there are active undo actions
- When all actions expire or are undone, the interval stops automatically
- Each family/child that needs countdown updates will reactively respond to the tick
- No polling or manual refresh needed

## Before vs After

**Before:**
- Timer text: "Undo (30s)" → stays frozen
- User clicks something → "Undo (28s)" (updates only on interaction)
- User types in search → "Undo (26s)" (updates only on interaction)

**After:**
- Timer text: "Undo (30s)" → "Undo (29s)" → "Undo (28s)" (updates automatically every second)
- No user interaction required
- Smooth, real-time countdown experience
