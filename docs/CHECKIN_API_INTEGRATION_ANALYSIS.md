# Check-In Page API Integration Analysis

## Executive Summary

This document analyzes the type mismatch between the mock data in the check-in page and the real Django backend API, and proposes an approach for integration.

**Recommendation**: **Hybrid Approach (Option C)** - Use API types with a lightweight adapter layer that adds computed/derived properties for UI state management.

---

## 1. Type Mismatch Analysis

### 1.1 Current Mock Data Structure

**Location**: `/workspace/check-ins/frontend/src/routes/checkin/+page.svelte` (lines 27-60)
**Type Definitions**: `/workspace/check-ins/frontend/src/lib/checkin/types.ts`

```typescript
// Mock Checkin Types (UI-centric)
type Family = {
  id: number;                    // Simple numeric ID
  name: string;                  // Just the family surname
  children: Child[];
  lastCheckInTime?: number;      // Unix timestamp
};

type Child = {
  id: number;                    // Simple numeric ID
  name: string;                  // Full name (first + last combined)
  ticket: TicketType;            // 'event' | 'session' | 'none'
  checkedIn: boolean;            // UI state
  checkInTime?: string;          // Formatted time like "9:15 AM"
  checkInActionId?: string;      // UUID for undo tracking
};

type TicketType = 'event' | 'session' | 'none';
```

### 1.2 Real API Data Structure

**Location**: `/workspace/check-ins/frontend/src/lib/api/types.ts`
**Backend Models**:
- `/workspace/check-ins/backend/families/models.py`
- `/workspace/check-ins/backend/events/models.py`
- `/workspace/check-ins/backend/checkins/models.py`

```typescript
// Real API Types (Database-centric)
type Family = {
  id: string;                           // UUID string
  last_participation_date?: string;     // ISO datetime
  parents?: Parent[];                   // Array of parent objects
  children?: Child[];                   // Array of child objects
};

type Parent = {
  id: string;                           // UUID string
  name: string;
  phone?: string;
  email?: string;
  relationship_type: string;            // 'MOM' | 'DAD' | 'OTHER'
  family: string;                       // UUID reference
};

type Child = {
  id: string;                           // UUID string
  family: string;                       // UUID reference
  first_name: string;                   // Separate fields
  last_name: string;
  date_of_birth?: string;               // ISO date
  allergies?: string;
  medical_conditions?: string;
  special_needs?: string;
  qr_token?: string;
  last_participation_date?: string;
};

type CheckInRecord = {
  id: string;                           // UUID string
  child: string;                        // UUID reference
  child_name: string;                   // Computed field from serializer
  session: string;                      // UUID reference
  session_name: string;                 // Computed field
  check_in_time: string;                // ISO datetime
  check_out_time?: string;              // ISO datetime
  check_in_staff: string;               // UUID reference
  check_in_staff_name: string;          // Computed field
  check_out_staff?: string;
  check_out_staff_name?: string;
  notes?: string;
  picked_up_by?: string;
};

type Ticket = {
  id: string;                           // UUID string
  type: 'EVENT_PASS' | 'SESSION_TICKET' | 'NONE';
  child: string;                        // UUID reference
  session?: string;                     // UUID reference (nullable)
};
```

### 1.3 Key Differences

| Aspect | Mock Data | Real API | Impact |
|--------|-----------|----------|--------|
| **IDs** | `number` | `string` (UUID) | Type mismatch - need conversion |
| **Family Name** | Single `name` field | Inferred from `parents[0].name` | Need to compute display name |
| **Child Name** | Combined `name` | Separate `first_name`, `last_name` | Need to join/split |
| **Check-In State** | `checkedIn: boolean` on Child | Separate `CheckInRecord` table | Need to query/join data |
| **Check-In Time** | Formatted string "9:15 AM" | ISO datetime | Need formatting |
| **Ticket Type** | Direct property on Child | Separate `Ticket` table | Need to query/join |
| **Undo Tracking** | `checkInActionId` on Child | Not in API (client-side only) | Keep client-side |
| **Last Check-In** | `lastCheckInTime` on Family | `last_participation_date` | Semantic difference |

---

## 2. API Endpoint Analysis

### 2.1 Available Endpoints

From `/workspace/check-ins/frontend/src/lib/api/services.ts`:

```typescript
// Family endpoints
familyApi.list()                    // GET /api/families/
familyApi.search(query)             // GET /api/families/?search={query}
familyApi.create(data)              // POST /api/families/

// Session endpoints
sessionApi.active()                 // GET /api/sessions/active/

// Check-in endpoints
checkInApi.checkIn(data)            // POST /api/checkins/check_in/
checkInApi.active()                 // GET /api/checkins/active/
checkInApi.checkOut(id, picker)     // POST /api/checkins/{id}/check_out/
checkInApi.undoCheckout(id)         // POST /api/checkins/{id}/undo_checkout/
```

### 2.2 Search Functionality

The backend uses Django REST Framework's search filters:

**Parent Search Fields**: `name`, `email`, `phone`
**Child Search Fields**: `first_name`, `last_name`, `qr_token`

The `familyApi.search()` returns families with nested parents and children, similar to `familyApi.list()`.

### 2.3 Data Relationships

```
Family
  ├─ parents[] (1:many)
  │    └─ Parent {name, phone, email, relationship_type}
  └─ children[] (1:many)
       └─ Child {first_name, last_name, birthdate, allergies, notes}
            └─ tickets[] (1:many)
                 └─ Ticket {type, session}

Session
  └─ checkin_records[] (1:many)
       └─ CheckInRecord {child, check_in_time, check_out_time}
```

### 2.4 Ticket System

The real system has a **separate `Ticket` model** with:
- `type`: 'EVENT_PASS' | 'SESSION_TICKET' | 'NONE'
- `child`: Foreign key to Child
- `session`: Optional foreign key (required for SESSION_TICKET)

**Important**: The current `Child` API doesn't include tickets. We'd need to:
1. Query tickets separately, OR
2. Enhance the serializer to include tickets (backend change), OR
3. Determine ticket type based on check-in rules

---

## 3. Proposed Approaches

### Option A: Update Check-In Types to Match API

**Approach**: Replace `/workspace/check-ins/frontend/src/lib/checkin/types.ts` to use API types directly.

**Pros**:
- Single source of truth
- No conversion overhead
- Easier to maintain long-term

**Cons**:
- Major refactor of UI components
- All child components need updates (FamilyCard, etc.)
- Breaks existing test data-testid selectors
- More complex UI code (accessing nested properties)

**Complexity**: HIGH

### Option B: Create Adapter Layer

**Approach**: Transform API data to match existing UI types.

```typescript
// New file: /workspace/check-ins/frontend/src/lib/checkin/adapters.ts

function apiToUiFamily(
  apiFamily: ApiFamily,
  checkInRecords: CheckInRecord[],
  tickets: Ticket[]
): UiFamily {
  return {
    id: parseInt(apiFamily.id, 16), // Convert UUID to number
    name: apiFamily.parents?.[0]?.name.split(' ').slice(-1)[0] || 'Unknown',
    children: apiFamily.children?.map(c =>
      apiToUiChild(c, checkInRecords, tickets)
    ) || [],
  };
}
```

**Pros**:
- Minimal UI changes
- Existing components work as-is
- Clean separation of concerns
- Easy to test adapters

**Cons**:
- UUID to number conversion is lossy (potential collisions)
- Conversion overhead on every render
- Two parallel type systems to maintain
- Harder to add new API fields

**Complexity**: MEDIUM

### Option C: Hybrid Approach (RECOMMENDED)

**Approach**: Use API types but extend with UI-specific computed properties.

```typescript
// Enhanced types in /workspace/check-ins/frontend/src/lib/checkin/types.ts

import type {
  Family as ApiFamily,
  Child as ApiChild,
  CheckInRecord
} from '$lib/api/types';

// Extend API types with UI state
export interface UiFamily extends ApiFamily {
  // Computed display properties
  displayName: string;           // From parents[0].name
  hasActiveCheckIns: boolean;    // Computed from check-ins

  // Enhanced children with UI state
  children: UiChild[];
}

export interface UiChild extends ApiChild {
  // Computed display properties
  fullName: string;              // first_name + last_name

  // UI state (not persisted)
  checkedIn: boolean;            // From CheckInRecord lookup
  checkInTime?: string;          // Formatted time
  checkInRecordId?: string;      // For undo functionality
  ticketType?: TicketType;       // From Ticket lookup

  // Client-side undo tracking
  checkInActionId?: string;      // UUID for undo timer
}

export type TicketType = 'event' | 'session' | 'none';

// Helper to enrich API data with UI state
export function enrichFamilyWithUiState(
  family: ApiFamily,
  activeCheckIns: CheckInRecord[],
  activeSessions: Session[]
): UiFamily {
  const displayName = family.parents?.[0]?.name.split(' ').slice(-1)[0] || 'Unknown';

  const enrichedChildren: UiChild[] = (family.children || []).map(child => {
    const checkInRecord = activeCheckIns.find(
      r => r.child === child.id && !r.check_out_time
    );

    return {
      ...child,
      fullName: `${child.first_name} ${child.last_name}`,
      checkedIn: !!checkInRecord,
      checkInTime: checkInRecord
        ? formatTime(checkInRecord.check_in_time)
        : undefined,
      checkInRecordId: checkInRecord?.id,
      ticketType: 'event', // TODO: Determine from Ticket table
    };
  });

  return {
    ...family,
    displayName,
    hasActiveCheckIns: enrichedChildren.some(c => c.checkedIn),
    children: enrichedChildren,
  };
}
```

**Pros**:
- Best of both worlds
- Uses real API types (type safety)
- Computed properties for UI convenience
- Minimal component changes
- Easy to add new API fields
- Type-safe UUID handling

**Cons**:
- Some duplication (computed fields)
- Enrichment function needs testing
- Slightly more complex types

**Complexity**: MEDIUM

---

## 4. Recommended Approach: Hybrid (Option C)

### 4.1 Implementation Strategy

1. **Phase 1: Type Layer**
   - Update `/workspace/check-ins/frontend/src/lib/checkin/types.ts`
   - Create `enrichFamilyWithUiState()` helper
   - Add type tests

2. **Phase 2: Data Loading**
   - Replace mock data with API calls
   - Load families, check-ins, and sessions on mount
   - Implement error handling and loading states

3. **Phase 3: Component Updates**
   - Update property access (e.g., `family.name` → `family.displayName`)
   - Update child property access (e.g., `child.name` → `child.fullName`)
   - Minimal changes due to computed properties

4. **Phase 4: Actions**
   - Implement check-in with `checkInApi.checkIn()`
   - Add optimistic updates for UX
   - Implement undo using `checkInApi.undoCheckout()`
   - Handle WebSocket updates for real-time sync

5. **Phase 5: Add Family**
   - Integrate with `familyApi.create()`
   - Transform UI form data to API format
   - Handle validation errors

### 4.2 Ticket Type Strategy

**Problem**: The API has a separate `Ticket` table, but current serializers don't include it.

**Options**:
1. **Backend enhancement** (preferred): Update `ChildSerializer` to include tickets
2. **Separate query**: Load tickets via a new endpoint
3. **Assumption-based**: Default to 'event' for now, add tickets later

**Recommendation**: Start with option 3 (default to 'event'), then enhance backend in a follow-up task.

### 4.3 Undo Functionality

**Current Mock Behavior**:
- 30-second grace period to undo check-ins
- Client-side timer tracks undo actions
- Family becomes visible again after all children are undone

**Real API Support**:
- Backend has `undoCheckout()` endpoint
- Removes check-out time, making check-in active again
- No built-in grace period (we implement client-side)

**Integration Strategy**:
1. Keep client-side undo timer (`undoTimer.ts`)
2. Store `checkInRecordId` instead of `checkInActionId`
3. On undo, call `checkInApi.undoCheckout(recordId)`
4. Handle race conditions with WebSocket updates

### 4.4 WebSocket Integration

**Existing Infrastructure**: `/workspace/check-ins/frontend/src/lib/stores/websocket.ts`

**Message Types**:
- `child_checked_in`: Another station checked in a child
- `child_checked_out`: Another station checked out a child
- `session_started`: New session became active
- `session_ended`: Session was ended

**Integration**:
- Subscribe to WebSocket on page mount
- On `child_checked_in`: Update local state if family is loaded
- On `child_checked_out`: Remove check-in from local state
- Preserve undo timer for our own actions (don't show undo for remote actions)

---

## 5. Data Flow Architecture

### 5.1 Initial Load

```
[Page Mount]
    ↓
[Load Active Session] ← sessionApi.active()
    ↓
[Load All Families] ← familyApi.list() or familyApi.search('')
    ↓
[Load Active Check-Ins] ← checkInApi.active()
    ↓
[Enrich Families] → enrichFamilyWithUiState()
    ↓
[Render UI]
```

### 5.2 Search Flow

```
[User Types in Search]
    ↓
[Debounce 300ms]
    ↓
[Query API] ← familyApi.search(query)
    ↓
[Enrich Results]
    ↓
[Filter Client-Side] → getVisibleFamilies()
    ↓
[Render Filtered List]
```

### 5.3 Check-In Flow

```
[User Clicks Check-In]
    ↓
[Optimistic Update] → Update local state immediately
    ↓
[API Call] ← checkInApi.checkIn({ child: childId, session: sessionId })
    ↓
[Success]
    ├─ [Store Record ID] → For undo functionality
    ├─ [Start Undo Timer] → 30-second countdown
    └─ [Show Toast] → Success message
    ↓
[Error]
    ├─ [Rollback Optimistic Update]
    └─ [Show Error Toast]
```

### 5.4 Undo Flow

```
[User Clicks Undo]
    ↓
[Optimistic Update] → Remove check-in locally
    ↓
[API Call] ← checkInApi.undoCheckout(recordId)
    ↓
[Success]
    ├─ [Remove Undo Timer]
    └─ [Show Toast] → "Check-in undone"
    ↓
[Error]
    ├─ [Rollback Optimistic Update]
    └─ [Show Error Toast]
```

### 5.5 WebSocket Updates

```
[WebSocket Message]
    ↓
[Parse Message Type]
    ↓
[child_checked_in]
    ├─ [Find Family in State]
    ├─ [Update Child Check-In Status]
    ├─ [Don't Show Undo] → Not our action
    └─ [Re-render]
    ↓
[child_checked_out]
    ├─ [Find Family in State]
    ├─ [Remove Check-In Status]
    └─ [Re-render]
```

---

## 6. Error Handling Strategy

### 6.1 API Error Types

```typescript
interface ApiError {
  message: string;
  status: number;
  details?: unknown;
}
```

### 6.2 Error Scenarios

| Scenario | API Response | User Message (i18n key) |
|----------|-------------|-------------------------|
| Already checked in | 400 + validation error | `checkin.errors.alreadyCheckedIn` |
| Session not active | 400 + validation error | `checkin.errors.sessionNotActive` |
| Network error | status: 0 | `checkin.errors.networkError` |
| Unauthorized | 401 | `checkin.errors.unauthorized` |
| Server error | 500 | `checkin.errors.serverError` |

### 6.3 Loading States

```typescript
// Add to page state
let isLoading = $state<boolean>(true);
let loadingError = $state<string | null>(null);
let isCheckingIn = $state<Set<string>>(new Set()); // Track per-child

// Use in UI
{#if isLoading}
  <LoadingSpinner />
{:else if loadingError}
  <ErrorMessage message={loadingError} />
{:else}
  <!-- Render families -->
{/if}
```

---

## 7. Migration Checklist

### 7.1 Files to Update

- [ ] `/workspace/check-ins/frontend/src/lib/checkin/types.ts` - Extend types
- [ ] `/workspace/check-ins/frontend/src/lib/checkin/adapters.ts` - New file for enrichment
- [ ] `/workspace/check-ins/frontend/src/routes/checkin/+page.svelte` - Replace mock data
- [ ] `/workspace/check-ins/frontend/src/lib/components/checkin/FamilyCard.svelte` - Update property access
- [ ] `/workspace/check-ins/frontend/src/lib/components/checkin/SessionIndicator.svelte` - Load real session
- [ ] `/workspace/check-ins/frontend/src/lib/components/checkin/AddFamilyPanel.svelte` - Integrate API

### 7.2 Testing Requirements

- [ ] Unit tests for `enrichFamilyWithUiState()`
- [ ] Integration tests for API calls
- [ ] Error handling tests
- [ ] WebSocket integration tests
- [ ] Undo timer tests with real API
- [ ] Search functionality tests
- [ ] Optimistic update tests

### 7.3 i18n Keys to Add

```typescript
// Add to translation files
{
  "checkin": {
    "errors": {
      "alreadyCheckedIn": "This child is already checked in",
      "sessionNotActive": "Session is not active",
      "networkError": "Network error. Please check your connection.",
      "unauthorized": "You are not authorized. Please log in.",
      "serverError": "Server error. Please try again later.",
      "loadFailed": "Failed to load families. Please refresh the page."
    },
    "loading": "Loading families...",
    "noSession": "No active session. Please start a session first."
  }
}
```

---

## 8. Performance Considerations

### 8.1 Initial Load Optimization

**Problem**: Loading all families, check-ins, and tickets separately is slow.

**Solutions**:
1. **Parallel loading**: Use `Promise.all()` for families and check-ins
2. **Pagination**: Load families in batches (API already supports this)
3. **Caching**: Store in localStorage with TTL
4. **Backend enhancement**: Create a dedicated check-in endpoint that returns enriched data

### 8.2 Search Optimization

**Problem**: Searching on every keystroke hits the API too frequently.

**Solutions**:
1. **Debouncing**: 300ms delay (already implemented in React prototype)
2. **Client-side filtering**: After initial load, filter locally
3. **Minimum query length**: Require 2+ characters

### 8.3 Re-rendering Optimization

**Problem**: WebSocket updates cause full page re-renders.

**Solutions**:
1. **Granular updates**: Only update affected family in state
2. **Svelte stores**: Use reactive stores for families
3. **Virtual scrolling**: For large family lists (future enhancement)

---

## 9. Open Questions

### 9.1 Ticket System

**Question**: How should we determine a child's ticket type?

**Options**:
1. Query the `Ticket` table separately (new endpoint needed)
2. Enhance `ChildSerializer` to include tickets (backend change)
3. Default to 'event' for all (simplification)
4. Infer from session rules (requires session configuration)

**Recommendation**: Start with option 3, then add proper ticket support in Phase 2.

### 9.2 Undo Behavior

**Question**: Should undo remove the check-in record, or just mark it as "pending undo"?

**Current API**: `undoCheckout()` removes the check-out time, making the record active again.
**Our Need**: We want to remove the check-in entirely during grace period.

**Options**:
1. Add `deleteCheckIn()` endpoint to backend
2. Use `undoCheckout()` and immediately `checkOut()`
3. Add `pending_undo` flag to CheckInRecord model

**Recommendation**: Add a DELETE endpoint for check-in records (option 1).

### 9.3 Family Display Name

**Question**: How should we derive the family display name?

**Current Mock**: Uses a single `name` field (e.g., "Garcia")
**Real API**: No family name field, only parent names

**Options**:
1. Use first parent's last name (e.g., "Smith")
2. Use first parent's full name (e.g., "John Smith")
3. Add `family_name` field to Family model (backend change)
4. Let users configure display name

**Recommendation**: Use option 1 (first parent's last name) for now, add configurable family name in Phase 2.

---

## 10. Conclusion

The **Hybrid Approach (Option C)** provides the best balance of:
- Type safety (using real API types)
- Developer experience (computed properties for UI)
- Maintainability (single source of truth)
- Minimal component changes (backward compatible)

### Next Steps

1. **Review this analysis** with the team
2. **Decide on open questions** (ticket system, undo behavior, family names)
3. **Update backend** if needed (delete check-in endpoint, ticket inclusion)
4. **Implement Phase 1** (type layer and enrichment)
5. **Test thoroughly** before moving to Phase 2

### Estimated Effort

- Phase 1 (Types & Adapters): 2-3 hours
- Phase 2 (Data Loading): 3-4 hours
- Phase 3 (Component Updates): 2-3 hours
- Phase 4 (Actions & WebSocket): 4-5 hours
- Phase 5 (Add Family): 2-3 hours
- Testing & Refinement: 4-5 hours

**Total: 17-23 hours** (2-3 days of focused work)
