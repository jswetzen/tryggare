# Check-In API Integration - Executive Summary

## The Problem

The check-in page (`/workspace/check-ins/frontend/src/routes/checkin/+page.svelte`) currently uses mock data with a simplified type structure. We need to integrate it with the real Django backend API, but there are significant type mismatches.

## Key Differences

| Mock Data | Real API | What This Means |
|-----------|----------|-----------------|
| `id: number` | `id: string` (UUID) | All IDs need to change type |
| `family.name` | No direct field | Must compute from parent names |
| `child.name` | `first_name` + `last_name` | Must join names |
| `child.checkedIn` | Separate `CheckInRecord` table | Must join/lookup data |
| `child.ticket` | Separate `Ticket` table | Must query or default |

## Recommended Approach: Hybrid

**Use real API types as the foundation, but extend them with computed UI properties.**

### Why This Works

```typescript
// API type (from backend)
type Child = {
  id: string;
  first_name: string;
  last_name: string;
  family: string;
  ...
};

// UI type (extends API type)
interface UiChild extends Child {
  fullName: string;        // Computed: first_name + last_name
  checkedIn: boolean;      // Joined from CheckInRecord
  checkInTime?: string;    // Formatted: "9:15 AM"
  checkInRecordId?: string; // For undo API calls
  ticketType?: TicketType;  // Defaulted or queried
}

// Enrichment function
function enrichChild(child: Child, checkIns: CheckInRecord[]): UiChild {
  const record = checkIns.find(r => r.child === child.id);
  return {
    ...child,
    fullName: `${child.first_name} ${child.last_name}`,
    checkedIn: !!record,
    checkInTime: record ? formatTime(record.check_in_time) : undefined,
    checkInRecordId: record?.id,
    ticketType: 'event', // Default for now
  };
}
```

### Benefits

- ✅ **Type-safe**: Uses real API types (TypeScript catches errors)
- ✅ **Minimal changes**: Components mostly work as-is
- ✅ **Future-proof**: Easy to add new API fields
- ✅ **Clean**: Separation between API data and UI state
- ✅ **Testable**: Enrichment function is a pure function

## Implementation Phases

### Phase 1: Type Layer (2-3 hours)
Create enrichment function and extended types. No UI changes yet.

### Phase 2: Data Loading (3-4 hours)
Replace mock data with real API calls. Add loading/error states.

### Phase 3: Component Updates (2-3 hours)
Update property access (`family.name` → `family.displayName`).

### Phase 4: Actions & WebSocket (4-5 hours)
Integrate check-in, undo, and real-time updates.

### Phase 5: Add Family (2-3 hours)
Transform form data to API format and create families.

**Total: 17-23 hours** (2-3 days)

## What Stays the Same

- ✅ All UI functionality (search, expand, check-in, undo)
- ✅ All i18n support (plus new error messages)
- ✅ Undo timer (30-second countdown)
- ✅ All data-testid attributes (tests work)
- ✅ Auto-expand on search
- ✅ Family visibility rules

## What Changes

### Component Code (minimal)
```svelte
<!-- Before -->
<h2>{family.name}</h2>
<p>{child.name}</p>

<!-- After -->
<h2>{family.displayName}</h2>
<p>{child.fullName}</p>
```

### Type Definitions
```typescript
// Before
let expandedFamilies = $state<Set<number>>(new Set());

// After
let expandedFamilies = $state<Set<string>>(new Set());
```

### Data Loading
```typescript
// Before
let families = $state<Family[]>(MOCK_FAMILIES);

// After
let families = $state<UiFamily[]>([]);
onMount(async () => {
  const [rawFamilies, checkIns] = await Promise.all([
    familyApi.list(),
    checkInApi.active(),
  ]);
  families = rawFamilies.map(f => enrichFamilyWithUiState(f, checkIns));
});
```

## Decisions Needed

### 1. Undo Behavior
**Question**: Should undo delete the check-in record?

**Options**:
- ✅ **Add DELETE endpoint** (cleanest, requires backend change)
- ⚠️ Use `undoCheckout()` + immediate `checkOut()` (hacky)

**Recommendation**: Add DELETE endpoint

**Backend change**:
```python
# In checkins/views.py CheckInViewSet
def destroy(self, request, pk=None):
    """Delete check-in record (for undo within grace period)"""
    record = self.get_object()
    if (timezone.now() - record.check_in_time).seconds > 30:
        return Response({"error": "Undo period expired"}, status=400)
    record.delete()
    return Response(status=204)
```

### 2. Ticket Type
**Question**: How to determine a child's ticket type?

**Options**:
- ✅ **Default to 'event'** (simple, MVP)
- ⚠️ Query Ticket table (requires endpoint)
- ⚠️ Enhance serializer (backend change)

**Recommendation**: Default to 'event' for Phase 1

### 3. Family Display Name
**Question**: How to show family name?

**Options**:
- ✅ **Use first parent's last name** (e.g., "Smith")
- ⚠️ Add family_name field (backend change)

**Recommendation**: Compute from parent name

### 4. Add Family Form
**Question**: What about required birthdate field?

**Options**:
- ✅ **Default to generic date** (e.g., "2020-01-01")
- ⚠️ Ask user (more complex form)

**Recommendation**: Default for quick add, show "edit details" message

## Data Flow

```
[Page Mount]
    ↓
[Load Active Session, Families, Check-Ins] (parallel)
    ↓
[Enrich Families] → enrichFamilyWithUiState()
    ↓
[Render UI]
    ↓
[User Actions]
    ├─ Check-In → POST /api/checkins/check_in/
    ├─ Undo → DELETE /api/checkins/{id}/
    └─ Add Family → POST /api/families/
    ↓
[WebSocket Updates]
    └─ child_checked_in/out → Update local state
```

## Testing Approach

### Unit Tests
- ✅ Enrichment function (`enrichFamilyWithUiState`)
- ✅ Time formatting
- ✅ Name computation
- ✅ Check-in lookup logic

### Integration Tests
- ✅ Page loads families from API
- ✅ Search filters correctly
- ✅ Check-in calls API and updates UI
- ✅ Undo calls API and updates UI
- ✅ WebSocket updates reflect in UI
- ✅ Error states display correctly

### Manual Testing
- ✅ Real database interactions
- ✅ Multi-station testing (WebSocket)
- ✅ Error scenarios (network, validation)
- ✅ i18n strings in all languages

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Backend changes not approved | Implement workarounds |
| Type errors not caught | TypeScript + unit tests |
| Performance with large datasets | Pagination + client-side caching |
| WebSocket issues | Fallback to polling |
| i18n missing strings | Review all text before deploy |

## Success Criteria

✅ All families load from real API
✅ Check-in creates database record
✅ Undo deletes database record
✅ WebSocket updates work
✅ Add family creates real family
✅ All i18n strings work
✅ No console errors
✅ All tests pass

## Next Steps

1. **Review & Approve** this proposal
2. **Decide on open questions** (undo, tickets, family name)
3. **Make backend changes** (if needed)
4. **Begin Phase 1** (type layer)

## Detailed Documentation

- **Full Analysis**: `/workspace/check-ins/docs/CHECKIN_API_INTEGRATION_ANALYSIS.md`
- **Architecture**: `/workspace/check-ins/docs/CHECKIN_API_ARCHITECTURE.md`
- **Proposal**: `/workspace/check-ins/docs/CHECKIN_API_INTEGRATION_PROPOSAL.md`

---

**Ready to proceed?** Let me know which decisions you'd like to make on the open questions, and I can begin implementation.
