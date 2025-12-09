# Check-In UX Specification

## Overview

This document specifies the user experience for the check-in system, including undo functionality and family management. The design prioritizes speed, clarity, and error recovery while maintaining a clean, uncluttered interface suitable for both desktop and mobile.

---

## 1. Undo Functionality

### 1.1 Core Concept

**Every check-in action is undoable for 30 seconds.** The undo mechanism is integrated directly into the action buttons - each button transforms into its own undo button.

### 1.2 Individual Child Check-In

**Initial State:**
- Button displays: `[Check In]` (green)
- User clicks button

**After Check-In (0-30 seconds):**
- Same button transforms to: `[Undo (28s)]` (orange/red)
- Countdown updates every second
- Child's status line updates: "🟢 Event Pass • Checked in at 9:15 AM"

**After Grace Period (30+ seconds):**
- Button transforms to: `[Checked In]` (gray, disabled)
- Undo is no longer possible
- This is the final state

**Undo Action:**
- User clicks `[Undo (Xs)]` button
- Child immediately reverts to unchecked state
- Button returns to: `[Check In]` (green)
- Check-in time is removed
- Success toast: "{Child name} check-in undone"

### 1.3 Family-Level Check-In

**Initial State:**
- Button displays: `[Check In Family (3)]` (blue)
- Number indicates eligible children (excludes already checked-in and no-ticket children)
- User clicks button

**After Check-In (0-30 seconds):**
- Same button transforms to: `[Undo Family (27s)]` (orange)
- All eligible children are checked in simultaneously
- Each child's status updates individually
- Success toast: "{Family name} family checked in (X children)!"

**After Grace Period (30+ seconds):**
- Button transforms to: `[All Checked In]` (gray)
- If all children are now checked in
- Family may disappear from list (if no unchecked children remain)

**Undo Action:**
- User clicks `[Undo Family (Xs)]` button
- ALL children checked in by that action revert to unchecked state
- Individual children who were already checked-in before this action are NOT affected
- Button returns to: `[Check In Family (X)]` (blue)
- Success toast: "{Family name} check-in undone"

### 1.4 Edge Cases - Undo

**Collapsed Family with Active Undo:**
- If family card is collapsed, undo buttons on individual children are not visible
- Family-level undo button remains visible in header
- User can expand card to see/undo individual children
- No special indicator needed - user will expand if they need to undo

**Multiple Individual Check-Ins:**
- Each individual check-in creates its own undo timer
- Example: Check in Isabella at 9:15, check in Lucas at 9:16
  - Isabella's undo expires at 9:15:30
  - Lucas's undo expires at 9:16:30
- Each button operates independently

**Mixed Check-In Actions:**
- User checks in Isabella individually (undo timer starts)
- Then clicks "Check In Family" which checks in Lucas
- Result: Two separate undo buttons with different timers
- Isabella: `[Undo (20s)]`
- Lucas: `[Undo (30s)]`
- Family button: Not visible (all children already checked in)

**Family Visibility During Grace Period:**
- Family remains visible in the list even if all children are checked in, AS LONG AS any undo timer is active
- Once all undo timers expire, family disappears from list (existing behavior)
- Filter logic: Show family if (hasUncheckedChildren OR hasActiveUndo)

**Search Interaction:**
- Families in grace period remain searchable
- Searching does not cancel or affect undo timers
- Undo buttons remain functional even when family is in filtered results

**QR Scanner Check-Ins:**
- QR scan triggers family-level check-in
- Undo button appears on family card
- If user returns to scanner immediately, they cannot see the undo button
- This is acceptable - undo is a secondary action, rapid scanning is primary workflow

---

## 2. Add Family

### 2.1 Location and Trigger

**Button Placement:**
- Located in the session indicator bar (top of page)
- Positioned on the right side: `[Change Session] [+ Add Family]`
- Always visible, regardless of scroll position (in header area)

**Visual Design:**
- Button style consistent with "Change Session" button
- Text: "+ Add Family" or "＋ Add Family"
- Secondary action styling (not as prominent as "Scan QR")

### 2.2 Collapsed State

```
┌─────────────────────────────────────────────────┐
│ Event: Summer Conference • Session: Morning...  │
│                           [Change] [+ Add Family]│
└─────────────────────────────────────────────────┘

     [Search: ___________________________] [Scan QR]
```

- Single button, no visual distraction
- Does not interfere with search or navigation

### 2.3 Expanded State

**When user clicks "+ Add Family":**

```
┌─────────────────────────────────────────────────┐
│ Event: Summer Conference • Session: Morning...  │
│                           [Change] [+ Add Family]│
└─────────────────────────────────────────────────┘
┌───────────────────────────────────────────────┐
│ Add New Family                            [X] │
│                                               │
│ Family Name: [____________]                   │
│                                               │
│ All children have: [No Ticket ▼]              │
│   Options: No Ticket, Session Only, Full Event│
│                                               │
│ Children:                                     │
│ Child 1: [____________]                       │
│ Child 2: [____________]                       │
│                                               │
│          [+ Add Child] [Cancel] [Add Family]  │
└───────────────────────────────────────────────┘
     [Search: ___________________________] [Scan QR]
```

- Panel expands **between** session bar and search bar
- Search bar stays in place (does not move)
- Panel pushes down the family list
- Background: white/light, border to distinguish from session bar
- Close button [X] in top right

### 2.4 Form Fields

**Family Name:**
- Required field
- Text input
- Placeholder: "Garcia", "Smith", etc.

**All children have (Ticket Type):**
- Dropdown selector
- Default: "No Ticket"
- Options:
  - No Ticket
  - Session Only
  - Full Event Pass
- Applies to ALL children in this family
- This is a family-level setting

**Children:**
- Minimum: 1 child (pre-populated empty input)
- Each child is a single text input for name
- No per-child ticket selection (family-level only)
- "+ Add Child" button below the list adds another input row
- Can remove children (X button next to each child input, except first)

**Actions:**
- **Cancel**: Close panel, discard input
- **Add Family**: Validate and create family
  - Validation: Family name required, at least one child name required
  - All children get the selected ticket type
  - Family appears in the main list
  - Panel closes automatically
  - Success toast: "{Family name} family added!"

### 2.5 Use Cases

**Use Case 1: Walk-Up Registration (No Tickets)**
1. Click "+ Add Family"
2. Enter "Garcia"
3. Leave dropdown on "No Ticket"
4. Enter children: "Isabella", "Lucas"
5. Click "Add Family"
6. Result: Garcia family added, both children have no tickets
7. At check-in: Click on each child → inline expansion → select ticket type

**Use Case 2: Pre-Registered Family (All Have Event Pass)**
1. Click "+ Add Family"
2. Enter "Smith"
3. Select "Full Event Pass" from dropdown
4. Enter children: "Emma", "Oliver"
5. Click "Add Family"
6. Result: Smith family added, both children have event passes
7. At check-in: Click "Check In Family (2)" → instant check-in

**Use Case 3: Mixed Ticket Types**
1. Click "+ Add Family"
2. Enter "Anderson"
3. Leave dropdown on "No Ticket" (even though some will have tickets)
4. Enter children: "Liam" (event pass), "Mia" (session only), "Noah" (no ticket)
5. Click "Add Family"
6. Result: Anderson family added, all three children marked as no ticket
7. At check-in:
   - Expand family
   - Click Liam's "No Ticket" → select "Full Event Pass"
   - Click Mia's "No Ticket" → select "Session Only"
   - Noah cannot check in (or use override)

**Alternative for Use Case 3:**
- Add family with most common ticket type (e.g., "Full Event Pass")
- Children who have that ticket type can check in normally
- Children who don't will show as having wrong ticket, use "No Ticket" flow to override

**Design Decision:** For mixed-ticket families, recommend adding with "No Ticket" and assigning tickets at check-in time. This keeps the add-family form simple and uses the existing ticket-assignment flow.

### 2.6 Edge Cases - Add Family

**Empty Family Name:**
- "Add Family" button disabled until family name is entered
- Or show validation error on click

**No Children:**
- Minimum 1 child required
- First child input cannot be removed

**Duplicate Family Names:**
- Allowed (families might have same last name)
- No uniqueness constraint
- Display in list alphabetically, user can differentiate by children

**Adding Child to Existing Family:**
- NOT supported in check-in UI
- This is registration management, not check-in workflow
- Recommendation: Handle in separate admin interface
- Workaround: Staff can add child as new family, or manually track

**Session Change with Open Panel:**
- If user clicks "Change Session" while add-family panel is open
- Recommend: Close panel automatically, discard input
- Or: Show confirmation: "Discard new family?"

---

## 3. No Ticket Check-In Flow

### 3.1 Concept

When a child has no ticket (or wrong ticket type for the session), checking them in requires selecting which ticket type to assign. This is done via **inline expansion** below the child, not a modal.

### 3.2 Initial State

**Child without ticket:**
```
┌────────────────────────────────────────────┐
│ Lucas Garcia          [No Ticket]          │
│ 🔴 No Ticket                               │
└────────────────────────────────────────────┘
```

- Button is red/orange: `[No Ticket]`
- Status line shows red indicator: "🔴 No Ticket"

### 3.3 User Clicks "No Ticket" Button

**Inline expansion appears:**
```
┌────────────────────────────────────────────┐
│ Lucas Garcia          [No Ticket] ▼        │
│ 🔴 No Ticket                               │
│ ┌────────────────────────────────────────┐ │
│ │ Check in Lucas with:                   │ │
│ │                                        │ │
│ │ [Session Only] [Full Event Pass]       │ │
│ └────────────────────────────────────────┘ │
└────────────────────────────────────────────┘
```

- Expansion panel appears below child info
- Light background (e.g., pale yellow/blue)
- Two action buttons: "Session Only" and "Full Event Pass"
- No "Cancel" button needed - user can click elsewhere or collapse

**Note:** There is NO "check in anyway without ticket" option. Minimum permission is "Session Only."

### 3.4 User Selects Ticket Type

**User clicks "Session Only" or "Full Event Pass":**

**Immediate result:**
```
┌────────────────────────────────────────────┐
│ Lucas Garcia          [Undo (30s)]         │
│ 🔵 Session Ticket • Checked in at 9:15 AM  │
└────────────────────────────────────────────┘
```

- Child is assigned the selected ticket type
- Child is checked in immediately
- Button transforms to undo button
- Status line updates with ticket type and check-in time
- Expansion panel closes
- Success toast: "Lucas Garcia checked in!"

### 3.5 Dismissing the Expansion

**Without checking in:**
- Click anywhere outside the expansion panel → collapses
- Click "No Ticket" button again → collapses (toggle behavior)
- Collapse family card → expansion auto-closes

### 3.6 Edge Cases - No Ticket Flow

**Family-Level "Check In Family" with No-Ticket Children:**
- "Check In Family" button ONLY appears if ALL children have valid tickets
- If ANY child has "No Ticket" status, family button is hidden
- Current behavior - maintained for clarity
- Rationale: Family check-in must be one-click, no decisions required

**User Clicks "Check In Family" → All Children No Ticket:**
- This scenario cannot occur (button is hidden)
- Family button visibility logic:
  ```
  canCheckInCount = children.filter(
    c => !c.checkedIn && c.ticket !== 'none'
  ).length

  showFamilyButton = canCheckInCount > 0
  ```

**Collapsed Family with No-Ticket Child:**
- User must expand family to access no-ticket flow
- No shortcut for this case - requires explicit action

**Multiple No-Ticket Children:**
- Each child has independent expansion
- Only one expansion visible at a time (opening one closes others)
- Or: allow multiple expansions simultaneously (implementation choice)

**Undo After Ticket Assignment:**
- Undoing check-in reverts ticket assignment
- Child returns to "No Ticket" status
- Button returns to `[No Ticket]` (red)
- Next check-in requires ticket selection again

**Child with Wrong Ticket Type:**
- Example: Child has "Session Only" ticket, but staff wants to upgrade to "Full Event Pass"
- Current design does NOT support this easily
- Options:
  1. Undo the check-in, re-check-in with new ticket type (clunky)
  2. Add ticket editing to admin interface (out of scope for check-in)
  3. Treat as edge case, handle manually

**Decision:** Do not support ticket editing in check-in UI. Check-in is for verification and admission, not registration changes.

---

## 4. Family Visibility Rules

### 4.1 Display Filter

**A family is visible in the list if:**
```
(hasUncheckedChildren) OR (hasActiveUndo)
```

Where:
- `hasUncheckedChildren = family.children.some(c => !c.checkedIn)`
- `hasActiveUndo = undoActions.some(a => a.familyId === family.id && now < a.expiresAt)`

### 4.2 Visibility Lifecycle

**State 1: Unchecked Children**
- Family visible
- Can check in children

**State 2: All Checked In, Undo Active**
- Family visible (grace period)
- Undo buttons visible
- Can undo check-ins

**State 3: All Checked In, Undo Expired**
- Family disappears from list
- No undo possible
- Final state

### 4.3 Search Interaction

**Search applies to visible families:**
- Filters by family name OR child name
- Does not change visibility rules
- Families in grace period are searchable

---

## 5. Visual Feedback & Animations

### 5.1 Check-In Success

**Immediate:**
- Button transforms (color, text change)
- Status line updates
- Toast notification appears

**Suggested Animations:**
- Subtle green glow/pulse on child row (0.5s)
- Button transform with smooth transition (0.2s)
- Toast slides in from right

### 5.2 Undo Countdown

**Timer Display:**
- Updates every second
- Format: "Undo (Xs)" where X = seconds remaining
- When < 10 seconds, consider color shift (more urgent orange/red)

### 5.3 Family Disappearance

**After grace period expires:**
- Smooth fade-out animation (0.5s)
- Family card becomes transparent then removed from DOM
- List re-flows smoothly

---

## 6. Accessibility

### 6.1 Screen Reader Announcements

**Check-In Success:**
- Announce: "{Child name} checked in successfully. Undo available for 30 seconds."

**Undo Action:**
- Announce: "{Child name} check-in undone."

**Undo Expiration:**
- Announce: "Undo period expired for {family name}."

**Family Added:**
- Announce: "{Family name} family added with X children."

### 6.2 Keyboard Navigation

**Undo Shortcut:**
- Ctrl+Z / Cmd+Z undoes most recent check-in (optional, nice-to-have)
- Focus management: After check-in, focus moves to undo button

**Add Family Panel:**
- Tab order: Family name → Ticket dropdown → Child 1 → Child 2 → ... → Add Child → Cancel → Add Family
- Escape key closes panel

### 6.3 Focus Management

**After Check-In:**
- Focus remains on (now transformed) undo button
- Allows immediate keyboard undo if needed

**After Undo:**
- Focus returns to (now transformed) check-in button

**Panel Open/Close:**
- Opening "Add Family" panel focuses family name input
- Closing panel returns focus to "+ Add Family" button

---

## 7. Mobile Considerations

### 7.1 Touch Targets

**Minimum button size:**
- 44x44px touch targets (iOS HIG standard)
- Adequate spacing between buttons to prevent mis-taps

### 7.2 Inline Expansion vs. Modal

**Why inline expansion for no-ticket flow:**
- Maintains context (can see family name, other children)
- Less disruptive than modal overlay
- Works better with collapsed/expanded cards
- Easier to dismiss

### 7.3 Add Family Panel

**On mobile:**
- Panel takes full width
- May push content significantly down (acceptable)
- Consider auto-scroll to keep panel in view when opened

---

## 8. Data Model

### 8.1 Child Structure

```typescript
interface Child {
  id: number;
  name: string;
  ticket: 'event' | 'session' | 'none';
  checkedIn: boolean;
  checkInTime?: string; // "9:15 AM"
  checkInActionId?: string; // UUID linking to undo action
}
```

### 8.2 Family Structure

```typescript
interface Family {
  id: number;
  name: string;
  children: Child[];
  lastCheckInTime?: number; // Unix timestamp
}
```

### 8.3 Undo Action Structure

```typescript
interface UndoAction {
  id: string; // UUID
  familyId: number;
  childIds: number[]; // Children affected by this action
  timestamp: number; // Unix timestamp when action occurred
  expiresAt: number; // timestamp + 30000 (30 seconds)
}
```

### 8.4 State Management

```typescript
const [families, setFamilies] = useState<Family[]>([]);
const [undoActions, setUndoActions] = useState<UndoAction[]>([]);
const GRACE_PERIOD_MS = 30000; // 30 seconds
```

---

## 9. Implementation Notes

### 9.1 Timer Management

**Undo Timer:**
- Use `setInterval` per active undo action to update countdown display
- Clean up intervals when component unmounts
- Use `setTimeout` to auto-remove undo action after grace period
- Clean up timeouts if undo is manually triggered

**Optimization:**
- Consider single interval updating all active timers
- Or use libraries like `react-use` for cleaner timer management

### 9.2 Undo Action Lifecycle

**Creation:**
1. User triggers check-in
2. Generate UUID for action
3. Update family/children state
4. Create undo action object
5. Add to undoActions array
6. Set timeout for auto-expiration

**Expiration:**
1. Timeout fires after 30 seconds
2. Remove action from undoActions array
3. Trigger re-render (family may disappear)

**Manual Undo:**
1. User clicks undo button
2. Find action by ID
3. Revert family/children state
4. Remove action from undoActions array
5. Cancel timeout (clearTimeout)

### 9.3 Family Filter Optimization

**Avoid unnecessary re-renders:**
- Memoize filtered families list
- Only recalculate when families or undoActions change
- Use `useMemo` for filter calculation

---

## 10. Future Enhancements (Out of Scope)

### 10.1 Audit Log
- Track all check-in/undo actions with timestamps
- Display in admin interface
- Export for reporting

### 10.2 Family Management
- Edit family details (name, children)
- Add child to existing family
- Remove child from family
- Separate admin interface, not in check-in UI

### 10.3 Session-Specific Tickets
- Track which sessions a "session ticket" is valid for
- More complex data model
- Requires session scheduling system

### 10.4 Batch Operations
- Check in multiple families at once
- Undo multiple actions
- Advanced user feature

### 10.5 Offline Support
- Queue check-ins when offline
- Sync when connection restored
- Disable undo for offline check-ins (consistency)

---

## 11. Open Questions for Product Review

1. **Grace period duration:** Is 30 seconds appropriate, or should it be configurable (15s, 45s, 60s)?

2. **Undo for offline check-ins:** Should we disable undo entirely for offline mode, or allow local undo before sync?

3. **Duplicate family names:** Should we show any disambiguation (e.g., "Garcia (2 children)" vs "Garcia (3 children)")?

4. **Session change behavior:** Should switching sessions auto-finalize all pending undos, or show a confirmation?

5. **No-ticket expansion:** Allow multiple expansions simultaneously, or only one at a time?

6. **Keyboard shortcut for undo:** Implement Ctrl+Z, or too risky (might conflict with browser/OS)?

7. **Add family: Minimum children:** Require at least 1 child, or allow 0 for edge cases?

---

## 12. Summary

This specification defines a streamlined check-in experience with:

- **Undo functionality** integrated into action buttons (30-second grace period)
- **Add family** via expanding panel below session bar
- **No-ticket flow** using inline expansion (not modals)
- **Family visibility rules** that keep recently checked-in families visible during grace period
- **Mobile-friendly** design with inline expansions instead of modals

The design prioritizes:
- Speed (one-click check-ins for valid tickets)
- Error recovery (undo within grace period)
- Clarity (inline feedback, no hidden states)
- Simplicity (registration management separate from check-in workflow)
