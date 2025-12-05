# Check-In Page Testing Guide

## Access the Page

Development: http://localhost:5173/checkin
Production: http://localhost:8080/checkin

## Mock Data Available

The page now uses mock data with 4 families:

### Garcia Family
- Isabella Garcia (Event ticket)
- Lucas Garcia (No ticket)

### Johnson Family
- Sophia Johnson (Session ticket)

### Smith Family
- Emma Smith (Event ticket)
- Oliver Smith (Event ticket)

### Anderson Family
- Liam Anderson (Event ticket)
- Mia Anderson (Event ticket)
- Noah Anderson (Session ticket)

## Test Scenarios

### 1. Initial Load
- [ ] Page displays "Check-In Station" header
- [ ] Session indicator shows "Summer Conference 2025 - Morning Care (8:00 AM - 12:00 PM)"
- [ ] Search box is visible and empty
- [ ] All 4 families are displayed
- [ ] Family count shows "4 families"

### 2. Search Functionality

#### Test: Search by family name
1. Type "Garcia" in search box
2. **Expected:** Only Garcia family shows
3. **Expected:** Count shows "1 family matching search"
4. **Expected:** Clear (X) button appears in search box

#### Test: Search by child name
1. Type "Isabella" in search box
2. **Expected:** Garcia family shows
3. **Expected:** Garcia family automatically expands
4. **Expected:** Isabella is visible in the child list

#### Test: Clear search
1. Type any search term
2. Click the X button
3. **Expected:** Search clears
4. **Expected:** All families visible again
5. **Expected:** Count shows "4 families"

### 3. Individual Check-In

#### Test: Check in child with ticket
1. Expand Garcia family (click anywhere on the card)
2. Click "Check In" button for Isabella Garcia
3. **Expected:** Green success toast appears: "Isabella Garcia checked in!"
4. **Expected:** Check In button changes to "Undo" button with countdown (30s)
5. **Expected:** Check-in time appears next to child name
6. Wait 30 seconds
7. **Expected:** Undo button disappears
8. **Expected:** Family card disappears (all eligible children checked in)

#### Test: Undo individual check-in
1. Expand Garcia family
2. Click "Check In" for Isabella Garcia
3. Immediately click "Undo (30s)" button
4. **Expected:** Success toast: "Isabella Garcia check-in undone"
5. **Expected:** Child shows as not checked in
6. **Expected:** "Check In" button is back

### 4. Child Without Ticket

#### Test: Expand child with no ticket
1. Expand Garcia family
2. Click on Lucas Garcia row (he has no ticket)
3. **Expected:** Row expands to show ticket assignment options
4. **Expected:** Three buttons appear:
   - "Event Pass (with Check-In)"
   - "Session Ticket (with Check-In)"
   - "Cancel"

#### Test: Assign ticket and check in
1. Expand Lucas Garcia
2. Click "Event Pass (with Check-In)"
3. **Expected:** Lucas gets event ticket
4. **Expected:** Lucas is checked in
5. **Expected:** Success toast appears
6. **Expected:** Undo button with countdown appears

### 5. Family Check-In

#### Test: Check in entire family
1. Ensure Garcia family has unchecked children with tickets
2. Click "Check In Family" button at bottom of family card
3. **Expected:** All children with tickets (not "none") are checked in
4. **Expected:** Success toast: "Garcia family checked in (X children)!"
5. **Expected:** "Undo Family (30s)" button appears
6. **Expected:** Individual children show undo buttons too

#### Test: Undo family check-in
1. Check in a family
2. Click "Undo Family" button
3. **Expected:** All children in that action are unchecked
4. **Expected:** Success toast: "Garcia check-in undone"
5. **Expected:** Family card shows "Check In Family" again

### 6. Add Family

#### Test: Open add family panel
1. Click "+ Add Family" button in session indicator
2. **Expected:** Add family panel slides in from right
3. **Expected:** Form shows fields:
   - Family Name
   - Child Names (with + Add Child button)
   - Ticket Type dropdown
   - Add Family button
   - Cancel button

#### Test: Add new family
1. Click "+ Add Family"
2. Enter family name: "TestFamily"
3. Enter first child: "John"
4. Click "+ Add Child"
5. Enter second child: "Jane"
6. Select ticket type: "Event Pass"
7. Click "Add Family"
8. **Expected:** Panel closes
9. **Expected:** Success toast: "TestFamily family added with 2 children!"
10. **Expected:** New family appears in alphabetical order
11. **Expected:** Family is auto-expanded
12. **Expected:** Children have correct names and tickets

#### Test: Cancel add family
1. Click "+ Add Family"
2. Start entering data
3. Click "Cancel"
4. **Expected:** Panel closes
5. **Expected:** No family added

### 7. Visibility Rules

#### Test: Family disappears when fully checked in
1. Find Smith family (Emma and Oliver both have event tickets)
2. Click "Check In Family"
3. **Expected:** Family shows undo buttons
4. Wait 30 seconds for grace period to expire
5. **Expected:** Smith family disappears from list
6. **Expected:** Family count decreases

#### Test: Family stays visible during grace period
1. Check in a family
2. **Expected:** Family stays visible
3. **Expected:** Can still undo within 30 seconds

### 8. Visual Elements

#### Test: Animations
- [ ] Success toast slides in from right
- [ ] Family expansion animates smoothly
- [ ] Child expansion animates smoothly
- [ ] Undo countdown updates every second

#### Test: Styling matches React prototype
- [ ] Blue theme colors match
- [ ] Card borders and shadows match
- [ ] Button styles match
- [ ] Font sizes and weights match
- [ ] Spacing and padding match

### 9. Edge Cases

#### Test: Empty search results
1. Type "XYZ123" (non-existent)
2. **Expected:** Shows "No families found matching 'XYZ123'"
3. **Expected:** Shows "Try a different search term"

#### Test: Check in child without expanding
1. Family should show "Check In Family" button even when collapsed
2. Click it
3. **Expected:** All eligible children check in without expanding

#### Test: Multiple undo timers
1. Check in Isabella from Garcia
2. Check in Sophia from Johnson
3. Check in Emma from Smith
4. **Expected:** All three show individual undo countdowns
5. **Expected:** All timers count down independently

## Browser Developer Tools

### Check Console (F12)
- [ ] No errors in console
- [ ] No warnings about missing props
- [ ] No React/Svelte reconciliation errors

### Check Network Tab
- [ ] No API calls (using mock data)
- [ ] Page loads without external dependencies

## Responsive Testing

### Test: Mobile view (< 640px)
- [ ] Layout stacks vertically
- [ ] Buttons remain readable
- [ ] Touch targets are adequate
- [ ] Session indicator wraps properly

### Test: Tablet view (640px - 1024px)
- [ ] Max width container keeps content readable
- [ ] Spacing remains appropriate

### Test: Desktop view (> 1024px)
- [ ] Content stays in max-width container (4xl = 896px)
- [ ] Doesn't stretch too wide

## Performance

- [ ] Page loads quickly
- [ ] Search filters instantly
- [ ] Check-in actions respond immediately
- [ ] No lag when expanding/collapsing families
- [ ] Undo countdown updates smoothly (1 second intervals)

## Accessibility

- [ ] All buttons have clear labels
- [ ] Search input has placeholder
- [ ] Can tab through all interactive elements
- [ ] Screen reader announces check-in actions
- [ ] Color contrast meets WCAG standards

## Success Criteria

The page is working correctly if:

1. All 4 mock families load and display
2. Search filters correctly
3. Individual and family check-ins work
4. Undo timers countdown and expire correctly
5. Adding families works and sorts alphabetically
6. Styling matches the React prototype exactly
7. No console errors or warnings
8. All animations play smoothly

## Known Limitations (Mock Data Mode)

- No actual backend calls
- No persistence (refresh loses state)
- Session is hardcoded
- Family/child IDs are numeric (not UUIDs)
- No actual ticket validation

These are expected and will be addressed when integrating the real API.
