# Check-In API Integration Proposal

**Date**: 2025-12-06
**Author**: Claude Code
**Status**: PROPOSAL - AWAITING APPROVAL

---

## Executive Summary

This document proposes a **Hybrid Approach** for integrating the check-in page with the Django backend API. The approach extends real API types with computed UI properties, providing type safety while minimizing component changes.

**Recommendation**: Proceed with the Hybrid Approach (detailed below).

**Estimated Effort**: 17-23 hours (2-3 days of focused work)

---

## 1. Type Mismatch Analysis

### Key Differences Between Mock and API

| Aspect | Mock Data | Real API | Solution |
|--------|-----------|----------|----------|
| **IDs** | `number` | `string` (UUID) | Use UUIDs throughout |
| **Family Name** | `name: string` | No direct field | Compute from `parents[0].name` |
| **Child Name** | `name: string` | `first_name` + `last_name` | Create `fullName` computed property |
| **Check-In State** | `checkedIn: boolean` | Separate `CheckInRecord` | Join data during enrichment |
| **Check-In Time** | `"9:15 AM"` | ISO datetime | Format during enrichment |
| **Ticket Type** | Property on Child | Separate `Ticket` table | Default to 'event' (Phase 1) |
| **Undo Tracking** | `checkInActionId` | Not in API | Keep client-side only |

### API Type Structure

```typescript
// Real API (simplified)
Family {
  id: string;                    // UUID
  parents: Parent[];             // Array of parent objects
  children: Child[];             // Array of child objects
}

Child {
  id: string;                    // UUID
  first_name: string;
  last_name: string;
  family: string;                // UUID reference
}

CheckInRecord {
  id: string;                    // UUID
  child: string;                 // UUID reference
  session: string;               // UUID reference
  check_in_time: string;         // ISO datetime
  check_out_time?: string;
}
```

---

## 2. Proposed Approach: Hybrid (Recommended)

### Why Hybrid?

The Hybrid Approach provides the best balance of:
- **Type Safety**: Uses real API types as base
- **Developer Experience**: Adds computed properties for UI convenience
- **Maintainability**: Single source of truth (API types)
- **Minimal Changes**: Existing components mostly work as-is
- **Future-Proof**: Easy to add new API fields

### How It Works

1. **Import real API types** as base types
2. **Extend with UI-specific properties** using TypeScript interfaces
3. **Enrich data** after loading from API
4. **Components use enriched types** with minimal changes

### Type Structure

```typescript
// /lib/checkin/types.ts

import type {
  Family as ApiFamily,
  Child as ApiChild,
  CheckInRecord,
  Session
} from '$lib/api/types';

// Extend API types with UI state
export interface UiFamily extends ApiFamily {
  // Computed display properties
  displayName: string;           // From parents[0].name
  hasActiveCheckIns: boolean;    // Any children checked in?

  // Enhanced children with UI state
  children: UiChild[];
}

export interface UiChild extends ApiChild {
  // Computed display properties
  fullName: string;              // first_name + last_name

  // UI state (joined from CheckInRecord)
  checkedIn: boolean;            // Is child currently checked in?
  checkInTime?: string;          // Formatted like "9:15 AM"
  checkInRecordId?: string;      // For undo API calls

  // Ticket info (TODO: query from Ticket table)
  ticketType?: TicketType;       // Default to 'event' for now

  // Client-side undo tracking
  checkInActionId?: string;      // UUID for undo timer
}

export type TicketType = 'event' | 'session' | 'none';
```

### Enrichment Function

```typescript
// /lib/checkin/adapters.ts

export function enrichFamilyWithUiState(
  family: ApiFamily,
  activeCheckIns: CheckInRecord[],
  activeSessions: Session[]
): UiFamily {
  // Compute family display name from first parent's last name
  const displayName = family.parents?.[0]?.name
    ?.split(' ')
    ?.slice(-1)[0] || 'Unknown';

  // Enrich children with UI state
  const enrichedChildren: UiChild[] = (family.children || []).map(child => {
    // Find active check-in record for this child
    const checkInRecord = activeCheckIns.find(
      r => r.child === child.id && !r.check_out_time
    );

    return {
      ...child,                                    // Spread API fields
      fullName: `${child.first_name} ${child.last_name}`,
      checkedIn: !!checkInRecord,
      checkInTime: checkInRecord
        ? formatTime(checkInRecord.check_in_time) // "9:15 AM"
        : undefined,
      checkInRecordId: checkInRecord?.id,
      ticketType: 'event', // TODO: Query Ticket table
    };
  });

  return {
    ...family,                                     // Spread API fields
    displayName,
    hasActiveCheckIns: enrichedChildren.some(c => c.checkedIn),
    children: enrichedChildren,
  };
}

// Format ISO datetime to "9:15 AM"
function formatTime(isoTime: string): string {
  return new Date(isoTime).toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  });
}
```

### Component Changes

**Minimal changes required**:

```svelte
<!-- OLD (mock data) -->
<h2>{family.name}</h2>
<p>{child.name}</p>

<!-- NEW (API data) -->
<h2>{family.displayName}</h2>
<p>{child.fullName}</p>
```

**Most logic stays the same**:
```typescript
// OLD
if (child.checkedIn) { /* ... */ }

// NEW (no change!)
if (child.checkedIn) { /* ... */ }
```

---

## 3. Implementation Plan

### Phase 1: Type Layer (2-3 hours)

**Files to create/update**:
- [ ] `/lib/checkin/types.ts` - Extend with UiFamily/UiChild
- [ ] `/lib/checkin/adapters.ts` - Create enrichment function
- [ ] `/lib/checkin/adapters.test.ts` - Unit tests for enrichment

**Deliverables**:
- Type-safe enrichment function
- Unit tests with 100% coverage
- No UI changes yet

### Phase 2: Data Loading (3-4 hours)

**Files to update**:
- [ ] `/routes/checkin/+page.svelte` - Replace mock data with API calls

**Changes**:
```typescript
// Replace MOCK_FAMILIES with:
let families = $state<UiFamily[]>([]);
let currentSession = $state<Session | null>(null);
let isLoading = $state<boolean>(true);
let loadingError = $state<string | null>(null);

onMount(async () => {
  await loadPageData();
});

async function loadPageData() {
  isLoading = true;
  try {
    // Parallel loading
    const [sessions, rawFamilies, checkIns] = await Promise.all([
      sessionApi.active(),
      familyApi.list(),
      checkInApi.active(),
    ]);

    currentSession = sessions[0] || null;

    // Enrich families with UI state
    families = rawFamilies.map(f =>
      enrichFamilyWithUiState(f, checkIns, sessions)
    );
  } catch (err) {
    loadingError = handleError(err);
  } finally {
    isLoading = false;
  }
}
```

**Deliverables**:
- Families load from real API
- Loading states implemented
- Error handling with user-friendly messages

### Phase 3: Component Updates (2-3 hours)

**Files to update**:
- [ ] `/lib/components/checkin/FamilyCard.svelte`
- [ ] `/lib/components/checkin/SessionIndicator.svelte`

**Changes**:
- `family.name` → `family.displayName`
- `child.name` → `child.fullName`
- `family.id` type changes from `number` to `string`
- `expandedFamilies` Set type changes from `Set<number>` to `Set<string>`

**Deliverables**:
- All components use new types
- No visual regressions
- All data-testid attributes preserved

### Phase 4: Actions & WebSocket (4-5 hours)

**Check-In Action**:
```typescript
async function checkInChild(familyId: string, childId: string) {
  try {
    // Optimistic update
    updateChildState(childId, { checkedIn: true, checkInTime: formatTime(new Date()) });

    // API call
    const record = await checkInApi.checkIn({
      child: childId,
      session: currentSession!.id,
    });

    // Store record ID for undo
    const actionId = createUndoAction(familyId, [childId]);
    updateChildState(childId, {
      checkInRecordId: record.id,
      checkInActionId: actionId,
    });

    // Success toast
    successToast = $_('checkin.successCheckedIn', { name: child.fullName });

  } catch (err) {
    // Rollback optimistic update
    updateChildState(childId, { checkedIn: false, checkInTime: undefined });
    errorToast = handleError(err);
  }
}
```

**Undo Action**:
```typescript
async function undoChildCheckIn(familyId: string, childId: string) {
  const child = findChild(childId);
  if (!child?.checkInRecordId) return;

  try {
    // Optimistic update
    updateChildState(childId, { checkedIn: false });

    // API call - DELETE check-in record
    await checkInApi.delete(child.checkInRecordId);

    // Remove undo timer
    removeUndoAction(child.checkInActionId!);

    successToast = $_('checkin.undoSuccess', { name: child.fullName });

  } catch (err) {
    // Rollback
    updateChildState(childId, { checkedIn: true });
    errorToast = handleError(err);
  }
}
```

**WebSocket Integration**:
```typescript
onMount(() => {
  websocketStore.connect();

  const unsubscribe = websocketStore.onMessage((message) => {
    switch (message.type) {
      case 'child_checked_in':
        // Update child in local state (without undo timer)
        updateChildCheckInStatus(message.data.child_id, true);
        break;

      case 'child_checked_out':
        updateChildCheckInStatus(message.data.child_id, false);
        break;
    }
  });

  return () => {
    unsubscribe();
    websocketStore.disconnect();
  };
});
```

**Deliverables**:
- Check-in calls real API
- Optimistic updates for instant feedback
- Undo functionality works with real API
- WebSocket updates reflect in UI
- Undo timer only shows for our own actions

### Phase 5: Add Family (2-3 hours)

**Transform UI data to API format**:
```typescript
async function handleAddFamily(data: {
  familyName: string;
  childrenNames: string[];
  ticketType: TicketType;
}) {
  try {
    // Transform to API format
    const apiData = {
      parents: [{
        name: data.familyName, // Use family name as parent name
        relationship_type: 'OTHER',
      }],
      children: data.childrenNames.map(name => ({
        first_name: name,
        last_name: data.familyName,
        birthdate: '2020-01-01', // TODO: Ask user for birthdates
      })),
    };

    // API call
    const newFamily = await familyApi.create(apiData);

    // Enrich and add to state
    const enriched = enrichFamilyWithUiState(newFamily, [], [currentSession!]);
    families = [...families, enriched].sort((a, b) =>
      a.displayName.localeCompare(b.displayName)
    );

    // Auto-expand
    expandedFamilies.add(newFamily.id);
    showAddPanel = false;

    successToast = $_('checkin.familyAdded', { name: data.familyName });

  } catch (err) {
    errorToast = handleError(err);
  }
}
```

**Deliverables**:
- Add family form creates real family
- New family appears in list
- Validation errors displayed
- Form fields match API requirements

---

## 4. Open Questions & Decisions Needed

### Q1: Ticket System

**Question**: How should we determine a child's ticket type?

**Options**:
1. ✅ **Default to 'event' for all** (simplest, Phase 1)
2. Query Ticket table separately (requires new endpoint)
3. Enhance ChildSerializer to include tickets (backend change)
4. Infer from session rules (complex logic)

**Recommendation**: Start with option 1, add proper ticket support in Phase 2.

**Impact**: Low - ticket type is only used for UI filtering, not critical for MVP.

---

### Q2: Undo Behavior

**Question**: Should undo remove the check-in record entirely?

**Current API**: `undoCheckout()` removes check-out time (makes record active again)
**Our Need**: Remove check-in entirely during 30-second grace period

**Options**:
1. ✅ **Add DELETE endpoint** to CheckInViewSet (recommended)
2. Use existing `undoCheckout()` + immediate `checkOut()` (hacky)
3. Add `pending_undo` flag to model (complex state)

**Recommendation**: Add DELETE endpoint - cleanest solution.

**Backend Change Required**:
```python
# In checkins/views.py
class CheckInViewSet(viewsets.ModelViewSet):
    # Add destroy method to allow DELETE
    def destroy(self, request, pk=None):
        """Delete check-in record (for undo within grace period)"""
        record = self.get_object()
        # Optional: Only allow delete within 30 seconds
        if (timezone.now() - record.check_in_time).seconds > 30:
            return Response(
                {"error": "Undo period expired"},
                status=400
            )
        record.delete()
        return Response(status=204)
```

**Impact**: Medium - requires backend change, but straightforward.

---

### Q3: Family Display Name

**Question**: How should we derive the family display name?

**Options**:
1. ✅ **Use first parent's last name** (e.g., "Smith")
2. Use first parent's full name (e.g., "John Smith")
3. Add `family_name` field to Family model
4. Let users configure display name

**Recommendation**: Use option 1 for now, consider adding `family_name` field later.

**Implementation**:
```typescript
const displayName = family.parents?.[0]?.name
  ?.split(' ')
  ?.slice(-1)[0] || 'Unknown';
```

**Impact**: Low - purely cosmetic, easy to change later.

---

### Q4: Add Family Form

**Question**: What fields should we require when adding a family?

**Current Form**:
- Family name (surname)
- Children first names (array)
- Ticket type

**API Requirements**:
- At least one parent (name, relationship_type)
- At least one child (first_name, last_name, birthdate)

**Gap**: Need birthdate for children!

**Options**:
1. ✅ **Default birthdate to generic value** (e.g., "2020-01-01")
2. Ask user for each child's birthdate (more complex form)
3. Make birthdate optional in backend (violates requirements)

**Recommendation**: Default birthdate for quick add, show warning that details can be edited later.

**Impact**: Low - families can be edited afterward with full details.

---

## 5. Testing Strategy

### Unit Tests

```typescript
// /lib/checkin/adapters.test.ts
describe('enrichFamilyWithUiState', () => {
  test('computes displayName from parent', () => { /* ... */ });
  test('joins child names', () => { /* ... */ });
  test('marks child as checked in', () => { /* ... */ });
  test('formats check-in time', () => { /* ... */ });
  test('handles missing data gracefully', () => { /* ... */ });
});
```

### Integration Tests

```typescript
// /routes/checkin/+page.test.ts
describe('Check-In Page', () => {
  test('loads families from API on mount', () => { /* ... */ });
  test('shows loading state', () => { /* ... */ });
  test('shows error state', () => { /* ... */ });
  test('filters families by search', () => { /* ... */ });
  test('checks in child via API', () => { /* ... */ });
  test('undoes check-in via API', () => { /* ... */ });
  test('receives WebSocket updates', () => { /* ... */ });
});
```

### Manual Testing Checklist

- [ ] Page loads without errors
- [ ] Families display correctly
- [ ] Search filters families
- [ ] Check-in creates record in database
- [ ] Undo deletes record from database
- [ ] WebSocket updates from other stations
- [ ] Error messages display correctly
- [ ] Loading states show during API calls
- [ ] Add family form creates family
- [ ] i18n strings display correctly

---

## 6. i18n Requirements

### New Translation Keys

```json
{
  "checkin": {
    "loading": "Loading families...",
    "noSession": "No active session. Please start a session first.",
    "errors": {
      "alreadyCheckedIn": "This child is already checked in",
      "sessionNotActive": "Session is not active",
      "networkError": "Network error. Please check your connection.",
      "unauthorized": "You are not authorized. Please log in.",
      "serverError": "Server error. Please try again later.",
      "loadFailed": "Failed to load families. Please refresh the page."
    },
    "undoSuccess": "{name} check-in undone",
    "familyAdded": "{name} family added successfully"
  }
}
```

---

## 7. Constraints & Considerations

### Must Preserve

- ✅ All i18n support (existing and new keys)
- ✅ All existing UI functionality
- ✅ Undo timer behavior (30-second countdown)
- ✅ All data-testid attributes (for tests)
- ✅ Auto-expand on search
- ✅ Family visibility rules

### Breaking Changes

- ⚠️ ID types change from `number` to `string` (UUID)
  - **Impact**: Any code using numeric IDs will break
  - **Mitigation**: Use TypeScript - compiler will catch issues

- ⚠️ Family name becomes computed property
  - **Impact**: Must use `displayName` instead of `name`
  - **Mitigation**: Simple find-replace

### Performance Considerations

- **Initial load**: 3 parallel API calls (fast)
- **Search**: Client-side filtering (instant)
- **Check-in**: Optimistic update (instant UI feedback)
- **WebSocket**: Real-time updates (< 100ms latency)

---

## 8. Rollout Plan

### Step 1: Backend Changes (if needed)

Before starting frontend work:
- [ ] Add DELETE endpoint to CheckInViewSet
- [ ] Test DELETE endpoint manually
- [ ] Deploy to dev environment

### Step 2: Incremental Frontend Implementation

Follow phases 1-5 in order, testing after each phase:
- [ ] Phase 1: Type layer (no visible changes)
- [ ] Phase 2: Data loading (families load from API)
- [ ] Phase 3: Component updates (UI works with real data)
- [ ] Phase 4: Actions (check-in/undo work)
- [ ] Phase 5: Add family (form works)

### Step 3: Testing

- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing checklist complete
- [ ] i18n strings verified

### Step 4: Deployment

- [ ] Deploy to dev environment
- [ ] Test with real data
- [ ] User acceptance testing
- [ ] Deploy to production

---

## 9. Success Criteria

This integration is successful when:

1. ✅ All families load from real Django API
2. ✅ Search filters families correctly
3. ✅ Check-in creates CheckInRecord in database
4. ✅ Undo deletes CheckInRecord within 30 seconds
5. ✅ WebSocket updates reflect in UI immediately
6. ✅ Add family creates Family with parents and children
7. ✅ All existing UI functionality preserved
8. ✅ All i18n strings display correctly
9. ✅ No console errors or warnings
10. ✅ All tests pass

---

## 10. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Backend DELETE endpoint not approved | Medium | High | Implement workaround with checkOut |
| WebSocket breaks with real data | Low | Medium | Thorough testing, fallback to polling |
| Performance issues with large datasets | Medium | Medium | Add pagination, virtual scrolling |
| Type mismatches not caught by compiler | Low | High | Extensive unit tests |
| i18n keys missing | Low | Low | Review all strings before deploy |

---

## 11. Conclusion

The **Hybrid Approach** provides the best path forward for integrating the check-in page with the Django backend API. It balances type safety, developer experience, and minimal changes to existing components.

### Next Steps

1. **Review this proposal** and get approval
2. **Answer open questions** (Q1-Q4 above)
3. **Make backend changes** (if needed)
4. **Begin Phase 1 implementation** (type layer)

### Decision Required

**Approve to proceed with Hybrid Approach?**

- [ ] ✅ Approved - proceed with implementation
- [ ] ⚠️ Approved with changes - discuss modifications
- [ ] ❌ Not approved - discuss alternative approach

---

**Appendix**: See `/workspace/check-ins/docs/CHECKIN_API_INTEGRATION_ANALYSIS.md` for detailed analysis and `/workspace/check-ins/docs/CHECKIN_API_ARCHITECTURE.md` for architecture diagrams.
