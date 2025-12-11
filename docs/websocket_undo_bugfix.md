# WebSocket Check-In Undo Bug Fix

## Date
2025-12-11

## Issue Description
When a check-in was undone on one station, other stations did not receive the WebSocket event update to show the child as no longer checked in. The child would remain showing as checked in on other stations until a manual reload.

## Root Cause Analysis

### Backend (Correct)
- **File:** `/workspace/check-ins/backend/checkins/views.py` (line 301-315)
- **Event Type:** `checkin_undone`
- **Broadcast:** Working correctly via WebSocket

```python
# Broadcast undo check-in event via WebSocket
channel_layer = get_channel_layer()
async_to_sync(channel_layer.group_send)(
    "checkins_broadcast",
    {
        "type": "checkin_undone",
        "data": {
            "record_id": record_id,
            "child_id": child_id,
            "child_name": child_name,
            "session_id": session_id,
            "session_name": session_name,
        }
    }
)
```

### WebSocket Consumer (Correct)
- **File:** `/workspace/check-ins/backend/checkins/consumers.py` (line 88-93)
- **Handler:** `checkin_undone` method exists and forwards events correctly

```python
async def checkin_undone(self, event):
    """Broadcast check-in undo event to client"""
    await self.send(text_data=json.dumps({
        "type": "checkin_undone",
        "data": event["data"]
    }))
```

### Frontend (Bug Found)
- **File:** `/workspace/check-ins/frontend/src/routes/checkin/+page.svelte` (line 247-285)
- **Problem:** The handler had a conditional check that prevented updates when `checkInActionId` was present

```typescript
// BROKEN CODE:
if (child.id === childId) {
  childFound = true;
  updated = true;
  // Clear check-in state if this wasn't our own undo action
  // (don't overwrite local undos that are in progress)
  if (!child.checkInActionId) {  // <-- BUG: This prevents updates!
    return {
      ...child,
      checkedIn: false,
      // ...
    };
  }
}
```

**Why this was a bug:**
1. When Station A checks in a child, it sets `checkInActionId` for undo tracking
2. When Station B undoes that same check-in, Station A receives a WebSocket `checkin_undone` event
3. Station A's handler sees that `child.checkInActionId` exists (from its own check-in)
4. The conditional `if (!child.checkInActionId)` blocks the update
5. Station A's UI never updates to show the child is no longer checked in

## Solution Implemented

### Pattern Match with Check-In Logic
The fix follows the same pattern already used for `child_checked_in` events:
- Track locally-initiated actions in a Set
- Filter out WebSocket events for our own actions
- Process all other events unconditionally

### Changes Made

#### 1. Added tracking for locally-undone children (line ~161)
```typescript
// Track children we've recently undone to avoid reloading on our own actions
let recentlyUndoneChildren = $state<Set<string>>(new Set());
```

#### 2. Updated WebSocket handler for `checkin_undone` (line ~250-294)
```typescript
} else if (message.type === 'checkin_undone') {
  const childId = message.data?.child_id;

  // Only process if this wasn't our own undo action
  // This preserves local state for our own undos
  if (childId && recentlyUndoneChildren.has(childId)) {
    // We triggered this - remove from our tracking set
    recentlyUndoneChildren.delete(childId);
    recentlyUndoneChildren = new Set(recentlyUndoneChildren);
    return;
  }

  if (childId) {
    // Another station undid a check-in - update incrementally
    let childFound = false;
    families = families.map((fam) => {
      let updated = false;
      const updatedChildren = fam.children.map((child) => {
        if (child.id === childId) {
          childFound = true;
          updated = true;
          // Clear check-in state unconditionally for remote undo events
          return {
            ...child,
            checkedIn: false,
            checkInTime: undefined,
            checkInActionId: undefined,
            checkInRecordId: undefined,
          };
        }
        return child;
      });
      // ...
    });
  }
}
```

#### 3. Updated `undoChildCheckIn` function (line ~512-530)
```typescript
async function undoChildCheckIn(familyId: string, childId: string) {
  // ...
  try {
    // Track this child to prevent WebSocket reload from clobbering local state
    recentlyUndoneChildren.add(childId);
    recentlyUndoneChildren = new Set(recentlyUndoneChildren);

    // Call backend undo endpoint
    await checkInApi.undo(child.checkInRecordId);
    // ...
  }
}
```

#### 4. Updated `undoFamilyCheckIn` function (line ~560-590)
```typescript
async function undoFamilyCheckIn(familyId: string) {
  // ...
  try {
    // Find all children affected by this family action
    const affectedChildren = family.children.filter(
      (c) => familyAction.childIds.includes(c.id) && c.checkInActionId === familyAction.id
    );

    // Track all children to prevent WebSocket reload from clobbering local state
    for (const child of affectedChildren) {
      recentlyUndoneChildren.add(child.id);
    }
    recentlyUndoneChildren = new Set(recentlyUndoneChildren);

    // Call backend undo endpoint for each child
    await Promise.all(/* ... */);
    // ...
  }
}
```

## Testing Verification

### Test Scenario
1. Open check-in page on two different browser tabs/windows (simulating two stations)
2. Check in a child on Station A
3. Verify child shows as checked in on both stations
4. Click "Undo" on Station A
5. **Expected:** Child should immediately show as not checked in on Station B
6. **Before fix:** Child remained checked in on Station B
7. **After fix:** Child correctly shows as not checked in on Station B

### Related Code Paths
- Check-in WebSocket updates: Working correctly (uses `recentlyCheckedInChildren`)
- Check-out WebSocket updates: Working correctly (no undo tracking needed)
- Undo WebSocket updates: **Now fixed** (uses `recentlyUndoneChildren`)

## Files Modified
- `/workspace/check-ins/frontend/src/routes/checkin/+page.svelte`

## Lessons Learned
1. WebSocket event handlers must carefully distinguish between local and remote actions
2. Conditional updates based on local state can block remote updates
3. The pattern of tracking "recently X'd children" is critical for maintaining consistency
4. Always test multi-station scenarios for real-time features
