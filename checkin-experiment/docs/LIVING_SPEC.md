# Check-In System - Living Design Specification

## Document Purpose

This is the living design specification for the check-in system. It contains UI/UX flows, visual descriptions, and interaction patterns—no implementation code. This document should be consulted and updated as the primary source of truth for design decisions.

**Last Updated**: December 4, 2025

---

## Overview

The check-in system provides a fast, error-correctable interface for checking children into events and sessions. The design prioritizes:

- **Speed**: One-click check-ins for children with valid tickets
- **Error Recovery**: 30-second undo grace period for all check-ins
- **Clarity**: Inline feedback, no hidden states, clear visual hierarchy
- **Mobile-First**: Touch-friendly design suitable for tablets and phones

---

## Core Concepts

### Sessions and Events

- **Events** are containers for multiple sessions (e.g., "Summer Conference")
- **Sessions** are time-based slots within an event (e.g., "Morning Session")
- Staff select an event and session before checking in families
- Children can have three ticket types:
  - **Full Event Pass**: Valid for all sessions
  - **Session Only**: Valid for specific session
  - **No Ticket**: Cannot check in without ticket assignment

### Family Structure

- Each family has a surname and one or more children
- Children have first names and ticket types
- Families are displayed alphabetically by surname
- Each child checks in independently

---

## Main Interface Layout

### Header Section

```
┌─────────────────────────────────────────────────────────────┐
│ Event: Summer Conference • Session: Morning                 │
│                               [Change Session] [+ Add Family]│
└─────────────────────────────────────────────────────────────┘

     [Search: _______________________________] [Scan QR]

     ┌─────────────────────────────────────────────────────┐
     │ Garcia Family                    [Check In Family (2)]│
     │ 2 children • 0 checked in                             │
     └─────────────────────────────────────────────────────┘
```

**Components:**
1. **Session indicator bar** (fixed at top)
   - Shows current event and session
   - "Change Session" button on right
   - "+ Add Family" button on right (next to Change Session)

2. **Search and actions bar**
   - Search input (left, expands to fill available space)
   - "Scan QR" button (right, prominent blue)

3. **Family list**
   - Scrollable list of family cards
   - Sorted: Unchecked families first, then checked-in families with active undo, then fully checked-in families disappear

### Family Card States

**Collapsed State:**
```
┌─────────────────────────────────────────────────────────┐
│ Garcia Family                    [Check In Family (2)] ▼│
│ 2 children • 0 checked in                                │
└─────────────────────────────────────────────────────────┘
```

**Expanded State:**
```
┌─────────────────────────────────────────────────────────┐
│ Garcia Family                    [Check In Family (2)] ▲│
│ 2 children • 0 checked in                                │
│                                                           │
│   Isabella Garcia                        [Check In]      │
│   🟢 Event Pass                                          │
│                                                           │
│   Lucas Garcia                           [No Ticket]     │
│   🔴 No Ticket                                           │
└─────────────────────────────────────────────────────────┘
```

**Interaction:**
- **Entire family card is clickable** to expand/collapse (not just the arrow)
- Arrow indicator (▲/▼) shows current state
- Expansion reveals individual children with their check-in buttons

---

## Family List Sorting

Families are displayed in priority order:

1. **Unchecked families** (any child not checked in)
   - Sorted alphabetically by family name
   - Shown at the top of the list

2. **Families with active undo** (all checked in, but grace period active)
   - Sorted alphabetically by family name
   - Shown below unchecked families

3. **Fully checked-in families** (all checked in, grace period expired)
   - Not visible (filtered out of list)

**Example Order:**
```
Anderson Family  (0/3 checked in)        ← Unchecked
Garcia Family    (1/2 checked in)        ← Unchecked
Smith Family     (0/4 checked in)        ← Unchecked
─────────────────────────────────────────
Martinez Family  (3/3 checked in, undo active) ← Checked-in with undo
Williams Family  (2/2 checked in, undo active) ← Checked-in with undo
```

---

## Search Functionality

### Basic Search

- Search applies to visible families
- Matches against:
  - Family surname (e.g., "Garcia")
  - Child first names (e.g., "Isabella")
- Live filtering as user types
- Case-insensitive matching

### Search with Child Name Match

When search matches a child's first name (not the family surname):

1. **Automatically expand the family card**
2. Highlight remains at family level (not individual child)
3. User can immediately see which children match

**Example:**

User types: "Emma"

```
     [Search: Emma___________________________] [Scan QR]

     ┌─────────────────────────────────────────────────────┐
     │ Anderson Family                  [Check In Family (2)]│
     │ 3 children • 0 checked in                            │▲
     │                                                       │
     │   Emma Anderson                          [Check In]  │
     │   🟢 Event Pass                                      │
     │                                                       │
     │   Liam Anderson                          [Check In]  │
     │   🟢 Event Pass                                      │
     │                                                       │
     │   Noah Anderson                          [No Ticket] │
     │   🔴 No Ticket                                       │
     └───────────────────────────────────────────────────────┘

     ┌─────────────────────────────────────────────────────┐
     │ Smith Family                     [Check In Family (1)]│
     │ 2 children • 0 checked in                            │▲
     │                                                       │
     │   Emma Smith                             [Check In]  │
     │   🟢 Event Pass                                      │
     │                                                       │
     │   Oliver Smith                           [Checked In]│
     │   🟢 Event Pass • Checked in at 9:05 AM              │
     └───────────────────────────────────────────────────────┘
```

Both Anderson and Smith families are expanded because they contain a child named "Emma".

### Empty Search Results

If no families match:
```
     [Search: Xyz___________________________] [Scan QR]

     ┌─────────────────────────────────────────────────────┐
     │                No families found                     │
     │                                                       │
     │     Try different search terms or clear the search   │
     └───────────────────────────────────────────────────────┘
```

---

## Check-In Button States

### Individual Child Buttons

**1. Check In (Green)**
```
[Check In]
```
- Child has valid ticket (Event Pass or Session Only)
- Not yet checked in
- Click triggers check-in

**2. Undo with Countdown (Orange)**
```
[Undo (23s)]
```
- Child was just checked in
- Within 30-second grace period
- Shows remaining seconds
- Click undoes the check-in

**3. Checked In (Gray, Disabled)**
```
[Checked In]
```
- Child checked in, grace period expired
- Cannot be undone
- Button disabled

**4. No Ticket (Red)**
```
[No Ticket] ▼
```
- Child has no ticket or wrong ticket type
- Click expands ticket assignment panel below
- Shows down arrow (▼) when collapsed
- Shows up arrow (▲) when expanded

### Family-Level Buttons

**Check In Family**
```
[Check In Family (3)]
```
- Shows count of eligible children (excludes already checked-in and no-ticket)
- Only visible when at least one child can be checked in
- Blue, prominent styling
- Click checks in all eligible children simultaneously

**Undo Family**
```
[Undo Family (27s)]
```
- Appears after family-level check-in
- Shows countdown timer
- Undoes the entire family check-in action
- Orange color for urgency

**All Checked In**
```
[All Checked In]
```
- All children checked in
- No active undo
- Gray, disabled
- Family will disappear from list after grace period

---

## Undo Functionality

### Grace Period Concept

Every check-in action has a **30-second undo window**. During this time:
- Button transforms from "Check In" to "Undo (Xs)"
- Countdown updates every second
- User can click to reverse the action
- After 30 seconds, undo button becomes "Checked In" (disabled)

### Individual Child Undo

**Initial State:**
```
Isabella Garcia                        [Check In]
🟢 Event Pass
```

**After Check-In (0-30 seconds):**
```
Isabella Garcia                        [Undo (28s)]
🟢 Event Pass • Checked in at 9:15 AM
```

**After Grace Period (30+ seconds):**
```
Isabella Garcia                        [Checked In]
🟢 Event Pass • Checked in at 9:15 AM
```

**Undo Action:**
- Click "Undo (Xs)" button
- Child reverts to unchecked state
- Check-in time removed
- Button returns to "Check In" (green)
- Toast notification: "Isabella Garcia check-in undone"

### Family-Level Undo

**Initial State:**
```
┌─────────────────────────────────────────────────────────┐
│ Garcia Family                    [Check In Family (2)] ▼│
│ 2 children • 0 checked in                                │
└─────────────────────────────────────────────────────────┘
```

**After Family Check-In (0-30 seconds):**
```
┌─────────────────────────────────────────────────────────┐
│ Garcia Family                    [Undo Family (27s)]   ▼│
│ 2 children • 2 checked in                                │
└─────────────────────────────────────────────────────────┘
```

**If Expanded During Grace Period:**
```
┌─────────────────────────────────────────────────────────┐
│ Garcia Family                    [Undo Family (27s)]   ▲│
│ 2 children • 2 checked in                                │
│                                                           │
│   Isabella Garcia                        [Undo (27s)]    │
│   🟢 Event Pass • Checked in at 9:15 AM                  │
│                                                           │
│   Lucas Garcia                           [Undo (27s)]    │
│   🟢 Event Pass • Checked in at 9:15 AM                  │
└─────────────────────────────────────────────────────────┘
```

Both individual undo buttons and family undo button show same countdown (they're part of the same action).

**Family Undo Action:**
- Click "Undo Family (Xs)" button
- ALL children checked in by that action revert to unchecked
- Family button returns to "Check In Family (X)" (blue)
- Toast notification: "Garcia family check-in undone"

**Individual Undo After Family Check-In:**
- If user expands family and clicks individual "Undo" button
- Only that child's check-in is undone
- Other children remain checked in
- Family button shows updated count: "Check In Family (1)"

### Edge Cases - Undo

**Multiple Individual Check-Ins:**
- Each individual check-in creates its own undo timer
- Example: Check in Isabella at 9:15, check in Lucas at 9:16
  - Isabella's undo expires at 9:15:30
  - Lucas's undo expires at 9:16:30
- Each button operates independently

**Family Visibility During Grace Period:**
- Family remains visible even if all children are checked in
- As long as any undo timer is active, family stays in list
- Once all undo timers expire, family disappears
- Family moves to bottom of list (below unchecked families)

**Collapsed Family with Active Undo:**
- Family card can be collapsed while undo is active
- Family-level undo button remains visible in collapsed header
- Individual child undo buttons hidden when collapsed
- User can expand to see individual undo options

---

## No Ticket Check-In Flow

### Concept

When a child has no ticket (or wrong ticket type), checking them in requires assigning a ticket type first. This is done via **inline expansion** below the child row, not a modal.

### Initial State

```
Lucas Garcia                           [No Ticket] ▼
🔴 No Ticket
```

- Button is red: "No Ticket"
- Shows down arrow (▼)
- Status line shows red indicator

### User Clicks "No Ticket"

**Expansion appears below:**
```
Lucas Garcia                           [No Ticket] ▲
🔴 No Ticket
┌───────────────────────────────────────────────────────┐
│ Check in Lucas with:                                  │
│                                                       │
│          [Session Only]  [Full Event Pass]           │
└───────────────────────────────────────────────────────┘
```

- Light background (e.g., pale yellow/blue)
- Button now shows up arrow (▲)
- Two action buttons: "Session Only" and "Full Event Pass"
- No "check in anyway without ticket" option

### User Selects Ticket Type

**User clicks "Session Only" or "Full Event Pass":**

**Immediate result:**
```
Lucas Garcia                           [Undo (30s)]
🔵 Session Ticket • Checked in at 9:15 AM
```

- Child is assigned the selected ticket type
- Child is checked in immediately
- Button transforms to undo button
- Status line updates with new ticket type and check-in time
- Expansion panel closes
- Toast notification: "Lucas Garcia checked in!"

### Dismissing Without Checking In

**Options:**
- Click "No Ticket" button again (toggle behavior)
- Click anywhere outside the expansion
- Collapse the family card (auto-closes expansion)
- Search for different family (auto-closes expansion)

### Undo After Ticket Assignment

**Behavior:**
- Undoing check-in **reverts ticket assignment**
- Child returns to "No Ticket" status
- Button returns to red "No Ticket" button
- Next check-in requires ticket selection again

**Rationale:** The no-ticket flow is for walk-up registrations and corrections. Undoing should return to the pre-assignment state.

---

## Add Family

### Location and Trigger

**Button Placement:**
- Located in session indicator bar (top of page)
- Right side, next to "Change Session" button
- Text: "+ Add Family"
- Always visible, regardless of scroll position

### Panel Expansion

**When user clicks "+ Add Family":**

```
┌─────────────────────────────────────────────────────────────┐
│ Event: Summer Conference • Session: Morning                 │
│                               [Change Session] [+ Add Family]│
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ Add New Family                                          [X] │
│                                                             │
│ Family Name: [________________________]                    │
│                                                             │
│ Ticket: [No Ticket ▼]                                      │
│   Options: No Ticket, Session Only, Full Event Pass        │
│                                                             │
│ Children:                                                   │
│ Child 1: [________________________]                         │
│ Child 2: [________________________]                         │
│                                                             │
│          [+ Add Child] [Cancel] [Add Family]               │
└─────────────────────────────────────────────────────────────┘
     [Search: _______________________________] [Scan QR]
```

- Panel expands **between** session bar and search bar
- Search bar stays in place (pushed down)
- Panel pushes down the family list
- White/light background with border
- Close button [X] in top-right corner

### Form Fields

**Family Name:**
- Required field
- Text input
- Placeholder: "Garcia", "Smith", etc.
- Auto-focused when panel opens

**Ticket:**
- Dropdown selector
- Default: "No Ticket"
- Options:
  - No Ticket
  - Session Only
  - Full Event Pass
- Applies to ALL children in this family

**Children:**
- Minimum: 1 child (first input cannot be removed)
- Each child is a single text input for name
- [X] button next to each child input (except first) to remove
- "+ Add Child" button adds another input row
- Empty child names are filtered out on submit

**Actions:**
- **Cancel**: Close panel, discard input
- **Add Family**:
  - Validate (family name required, at least one non-empty child name)
  - Create family with all children having selected ticket type
  - Close panel
  - Family appears in main list (sorted alphabetically)
  - Family card auto-expands to show children
  - Toast notification: "Garcia family added!"

### Use Cases

**Use Case 1: Walk-Up Registration (No Tickets)**
1. Click "+ Add Family"
2. Enter "Garcia"
3. Leave dropdown on "No Ticket"
4. Enter children: "Isabella", "Lucas"
5. Click "Add Family"
6. Result: Garcia family added, both children have no tickets
7. At check-in: Expand Garcia family → click child "No Ticket" button → select ticket type

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
4. Enter children: "Liam", "Mia", "Noah"
5. Click "Add Family"
6. Result: Anderson family added, all three marked as no ticket
7. At check-in:
   - Expand Anderson family
   - Click Liam's "No Ticket" → select "Full Event Pass"
   - Click Mia's "No Ticket" → select "Session Only"
   - Noah stays as no ticket (or use same flow to assign)

**Design Decision:** For mixed-ticket families, recommend adding with "No Ticket" and assigning tickets at check-in time. This keeps the add-family form simple and uses the existing ticket-assignment flow.

### Keyboard Support

**Tab Order:**
1. Family name input
2. Ticket dropdown
3. Child 1 name input
4. Child 2 name input
5. ...
6. "+ Add Child" button
7. "Cancel" button
8. "Add Family" button

**Keyboard Shortcuts:**
- **Escape**: Close panel without saving
- **Enter** (in any input field): Submit form (same as clicking "Add Family")

---

## QR Scanner Flow

### Scanner Button

**Location:** Right side of search bar
**Text:** "Scan QR"
**Styling:** Prominent blue button

### Scanner View

**When user clicks "Scan QR":**
- Full-screen camera view
- "Back" button in top-left to exit
- Scans QR codes associated with families

### After Successful Scan

**Flow:**
1. QR code scanned and family identified
2. Family card slides up from bottom
3. Family is automatically expanded
4. "Check In Family" button prominently displayed
5. User clicks "Check In Family"
6. Camera view returns immediately for next scan

**Design:** Optimized for rapid batch check-ins (e.g., event entrance).

**Note:** Undo buttons remain functional, but user may need to exit scanner to see them. This is acceptable—rapid scanning is the primary workflow.

---

## Visual Design Details

### Status Indicators

**Ticket Type Icons:**
- 🟢 **Event Pass** - Green circle
- 🔵 **Session Ticket** - Blue circle
- 🔴 **No Ticket** - Red circle

**Status Line Format:**
```
🟢 Event Pass • Checked in at 9:15 AM
```

### Button Colors

**Green:** Check In (ready to proceed)
**Blue:** Check In Family (primary action, prominent)
**Orange:** Undo buttons (urgent, time-limited)
**Red:** No Ticket (requires attention)
**Gray:** Checked In, All Checked In (disabled, completed)

### Touch Targets

- Minimum 44x44px touch target (iOS HIG standard)
- Adequate spacing between buttons to prevent mis-taps
- **Entire family card is clickable** for expand/collapse (not just the arrow)

### Animations

**Check-In Success:**
- Subtle green glow/pulse on child row (0.5s)
- Button transform with smooth transition (0.2s)
- Toast notification slides in from right

**Undo Countdown:**
- Updates every second
- Consider color shift when < 10 seconds (more urgent orange/red)

**Family Disappearance:**
- After grace period expires
- Smooth fade-out animation (0.5s)
- List re-flows smoothly

### Toast Notifications

**Duration:** 3 seconds
**Position:** Top-right corner
**Animation:** Slide in from right
**Auto-dismiss:** Yes
**Examples:**
- "Garcia family checked in (2 children)!"
- "Isabella Garcia checked in!"
- "Lucas Garcia check-in undone"
- "Smith family added!"

---

## Accessibility

### Screen Reader Announcements

**Check-In Success:**
- Announce: "{Child name} checked in successfully. Undo available for 30 seconds."

**Undo Action:**
- Announce: "{Child name} check-in undone."

**Family Added:**
- Announce: "{Family name} family added with X children."

### Keyboard Navigation

**General:**
- All interactive elements keyboard accessible
- Tab order follows logical flow
- Focus indicators clearly visible

**Potential Shortcuts (Nice-to-Have):**
- Ctrl+Z / Cmd+Z: Undo most recent check-in
- / (slash): Focus search input

### Focus Management

**After Check-In:**
- Focus remains on (now transformed) undo button
- Allows immediate keyboard undo if needed

**After Undo:**
- Focus returns to (now transformed) check-in button

**Panel Open/Close:**
- Opening "Add Family" panel focuses family name input
- Closing panel returns focus to "+ Add Family" button

**Card Expand/Collapse:**
- Focus remains on family card header
- Allows quick keyboard navigation through families

---

## Data and State

### Child Data

```
Child:
  - id: unique identifier
  - name: first name (string)
  - ticket: 'event' | 'session' | 'none'
  - checkedIn: boolean
  - checkInTime: time string (e.g., "9:15 AM") - optional
  - checkInActionId: UUID linking to undo action - optional
```

### Family Data

```
Family:
  - id: unique identifier
  - name: family surname (string)
  - children: array of Child objects
  - lastCheckInTime: Unix timestamp of last check-in - optional
```

### Undo Action

```
UndoAction:
  - id: UUID
  - familyId: family identifier
  - childIds: array of child IDs affected by this action
  - timestamp: Unix timestamp when action occurred
  - expiresAt: timestamp + 30000 (30 seconds in milliseconds)
```

### Family Visibility Rules

A family is visible in the list if:
```
(hasUncheckedChildren) OR (hasActiveUndo)
```

Where:
- `hasUncheckedChildren`: at least one child has `checkedIn === false`
- `hasActiveUndo`: exists an UndoAction for this family where `now < expiresAt`

### Family Sort Order

Families are sorted by:
1. **Primary:** Checked-in status
   - Families with unchecked children first
   - Families with all checked-in (and active undo) last
2. **Secondary:** Alphabetical by family name

---

## Edge Cases and Special Scenarios

### Duplicate Family Names

**Behavior:** Allowed (families might have same surname)
**No uniqueness constraint**
**Disambiguation:** By children names when displayed

### Empty Search After Filtering

**Show empty state message:**
```
No families found

Try different search terms or clear the search
```

### All Families Checked In

**Show empty list with message:**
```
All families checked in!

Great job! All registered families have been checked in.
```

### Session Change with Open Add Family Panel

**Behavior:**
- Close add-family panel automatically
- Discard unsaved input
- Or: Show confirmation modal: "Discard new family?"

### Session Change with Active Undo

**Behavior:**
- Show modal: "You have 3 families with active undo timers. Switch sessions anyway?"
- Options: [Cancel] [Switch Session]
- If user switches: all undo actions finalized (cannot undo)

### Browser Refresh

**Current behavior:** All state lost (no persistence)
**Future enhancement:** Consider localStorage backup

---

## Out of Scope (Future Enhancements)

These features are documented for future consideration but are not part of the current design:

1. **Audit Log:** Track all check-in/undo actions with timestamps for reporting
2. **Family Management:** Edit family details, add children to existing families (separate admin interface)
3. **Session-Specific Tickets:** Track which sessions a "session ticket" is valid for
4. **Batch Operations:** Check in multiple families at once
5. **Offline Support:** Queue check-ins when offline, sync when connection restored
6. **Backend Integration:** API for data persistence and multi-device sync
7. **Advanced QR Features:** Generate QR codes, print labels
8. **Keyboard Shortcuts:** Comprehensive keyboard-only workflow

---

## Open Questions for Product Review

1. **Grace period duration:** Is 30 seconds appropriate, or should it be configurable?

2. **Undo for offline check-ins:** Should we disable undo entirely for offline mode, or allow local undo before sync?

3. **Duplicate family names:** Should we show any disambiguation UI?

4. **Session change behavior:** Should switching sessions auto-finalize all pending undos, or show a confirmation?

5. **QR scanner undo visibility:** Should we show a floating undo button on scanner screen?

6. **Ticket type editing:** Should we support changing a child's ticket type after initial assignment (without undo/redo)?

---

## Design Principles

### Speed Over Safety

- One-click actions for common cases
- No confirmation modals for check-ins
- Undo provides safety net instead of upfront confirmation

### Inline Over Modal

- Expansions instead of modal overlays
- Maintains context (family visible)
- Less disruptive workflow
- Better for touch interfaces

### Forgiving Over Restrictive

- 30-second undo window
- Can fix mistakes without backend access
- Reduces stress for check-in staff

### Visible Over Hidden

- Active states shown explicitly (countdown timers)
- No hidden undo actions
- Families stay visible during grace period

### Simple Over Comprehensive

- Check-in interface focused on check-in only
- Registration management separate (out of scope)
- Minimal form fields in "Add Family"

---

## Summary

This specification defines a streamlined check-in experience with:

✅ **Undo functionality** - 30-second grace period for all check-ins
✅ **Smart sorting** - Unchecked families prioritized, checked-in families drop below
✅ **Full card interaction** - Entire family card clickable to expand/collapse
✅ **Smart search** - Auto-expands families when child name matches
✅ **Add family** - Simple form via expanding panel
✅ **No-ticket flow** - Inline expansion for ticket assignment
✅ **Family visibility rules** - Families stay visible during grace period
✅ **Mobile-friendly** - Touch targets, inline expansions, responsive design

The design prioritizes speed, error recovery, clarity, and simplicity.
