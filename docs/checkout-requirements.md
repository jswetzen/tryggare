# Checkout Page Requirements Document

## Purpose
The checkout page allows staff to check out children who are currently checked in to an event session. Parents/guardians arrive to pick up their children, and staff must verify pickup authorization and record who collected each child.

## User Roles
- **Primary User**: Event staff operating the checkout station
- **Context**: Fast-paced environment during pickup times
- **Device**: Typically a tablet or desktop computer at a checkout desk

## Core Functionality

### 1. Display Checked-In Children
**Requirement**: Show all children currently checked in to the active session.

**Data to Display Per Child**:
- Child's full name (first and last)
- Check-in time (format: HH:MM, 24-hour)
- Family/surname (to group siblings)
- Supervision status (if checked in as "supervised" - indicates guardian is present in facility)

**Data to Display Per Family**:
- Family surname
- Count of checked-in children in that family
- Parent/guardian contact information (names and relationship types)

### 2. Search and Filter
**Requirement**: Allow staff to quickly locate specific children or families.

**Search Criteria**:
- Child's name (first or last)
- Family surname
- Real-time filtering as user types

**Behavior**:
- Search should be case-insensitive
- Should match partial names
- Results update immediately without requiring submit action

### 3. Individual Child Checkout
**Requirement**: Check out a single child.

**Action**:
- Staff selects a specific child to check out
- Optional: Record who picked up the child (parent/guardian name)
- System records checkout time automatically
- Child is removed from the active checkout list

**Validation**:
- None required (staff discretion on who can pick up)
- Pickup person recording is optional but encouraged

### 4. Family Checkout (Bulk Action)
**Requirement**: Check out all children from the same family simultaneously.

**Action**:
- Staff selects "check out family" action
- All checked-in children with the same surname are checked out
- Optional: Record who picked up all children (single selection applies to all)
- System records same checkout time for all siblings

**Use Case**: Parent arrives to pick up multiple children at once

### 5. Pickup Authorization Recording
**Requirement**: Optionally record who picked up the child(ren).

**Data Elements**:
- Dropdown/selector of authorized parents/guardians for that family
- Each family has pre-registered parents with:
  - Name
  - Relationship type (Parent, Grandparent, Guardian, etc.)
  - Contact information (phone, email)
- "Select person" default option (allows skipping this step)

**Behavior**:
- Selection persists per family during the session
- Not required to complete checkout
- Stored with checkout record for later audit

### 6. Session Awareness
**Requirement**: Only show children checked in to the currently active session.

**Data Display**:
- Event name
- Session name
- Session time range (start - end)
- Ability to switch between active sessions if multiple are running

**Behavior**:
- Default to first active session
- Allow manual session selection if needed
- Filter checkout list based on selected session

### 7. Real-Time Updates
**Requirement**: Reflect changes made at other checkout stations immediately.

**Events to Handle**:
- Another station checks out a child → remove from local list
- Child checks in at another station → add to local list
- Undo action at another station → update status accordingly

**Technology**: WebSocket connection for live updates

### 8. Refresh Data
**Requirement**: Manual refresh option to reload current state.

**Use Case**:
- Connection issues
- Staff wants to verify current state
- System has been idle

## Information Architecture

### Grouping
- Children should be grouped by family/surname
- Within each family, children listed individually

### Sorting
- Families: Alphabetical by surname
- Children within family: Any logical order (by age, check-in time, or alphabetical by first name)

## Interaction Requirements

### Speed and Efficiency
- **Critical**: Checkout process must be fast (single action preferred)
- Minimize clicks/taps required to check out a child
- Common action (checking out a family) should be equally fast as individual checkout

### Mobile Considerations
- Must work on tablets (landscape and portrait)
- Touch-friendly targets (minimum 44x44px for buttons)
- Readable text sizes on small screens
- Should handle multiple families without excessive scrolling
- **Performance**: Low scrolling requirement (user feedback indicates current design requires too much scrolling)

### Desktop Considerations
- Take advantage of available screen space
- Can display more information density
- Efficient use of horizontal space
- Quick scanning of multiple families

### Error Handling
- Handle network disconnections gracefully
- Show loading states during data fetch
- Provide feedback for successful checkout actions
- Display errors clearly if checkout fails

## Data Flow

### Input Data
1. Active session information (from session API)
2. List of all currently checked-in children (from check-in records API)
3. Family information including parents/guardians (from families API)

### Output Actions
1. Check out individual child (POST to checkout API with child check-in record ID)
2. Check out multiple children (batch POST to checkout API)
3. Record pickup authorization (include in checkout POST request)

### Data Transformation
- Merge check-in records with family information
- Group children by family ID
- Filter by selected session
- Apply search query filtering

## Accessibility Requirements
- Keyboard navigation support
- Screen reader friendly labels
- Clear focus indicators
- Sufficient color contrast
- Touch target sizes meet WCAG AA standards

## Localization
- All text must support internationalization (i18n)
- Currently supporting: English, Swedish
- Date/time formatting respects locale

## Success Metrics
- **Speed**: Staff can check out a single child in < 3 seconds
- **Accuracy**: Zero missed checkouts due to UI confusion
- **Efficiency**: Family checkout reduces time by 50% vs individual
- **Usability**: Staff can operate without training

## Out of Scope
- Child registration or editing
- Check-in functionality (separate page)
- Payment processing
- Generating reports
- Sending notifications to parents

## Technical Constraints
- Frontend: SvelteKit with Svelte 5 runes syntax
- Styling: Tailwind CSS utility classes
- Backend: Django REST API
- Real-time: WebSocket via Django Channels
- Must work in development (localhost:5173) and production (localhost:8080)

## Design Flexibility
The following are NOT requirements and are open to design interpretation:
- Visual layout (cards, table, list, hybrid)
- Color scheme (maintain consistency with check-in page)
- Typography choices (within existing design system)
- Spacing and density
- Animation/transitions
- Iconography

## Design Constraints
The following MUST be consistent with the check-in page:
- Overall color palette (blue primary, red for checkout actions)
- Rounded corners on card-like elements
- Border and shadow styles
- Button styles and states
- Input field styling (search box, dropdowns)
- Navigation header appearance
