# Check-In Types Comparison: Mock vs API vs Proposed

## Side-by-Side Type Comparison

### Family Type

| Field | Mock Type | API Type | Proposed UI Type | Notes |
|-------|-----------|----------|------------------|-------|
| `id` | `number` | `string` (UUID) | `string` (UUID) | Breaking change |
| `name` | `string` | ❌ Not available | ❌ Removed | |
| `displayName` | ❌ Not available | ❌ Not available | ✅ `string` | Computed from `parents[0].name` |
| `parents` | ❌ Not available | ✅ `Parent[]` | ✅ `Parent[]` | Inherited from API |
| `children` | ✅ `Child[]` | ✅ `Child[]` | ✅ `UiChild[]` | Enhanced version |
| `lastCheckInTime` | ✅ `number` (timestamp) | ❌ Not available | ❌ Removed | |
| `last_participation_date` | ❌ Not available | ✅ `string` (ISO date) | ✅ `string` (ISO date) | Inherited from API |
| `hasActiveCheckIns` | ❌ Not available | ❌ Not available | ✅ `boolean` | Computed from children |

**Migration Path**: Replace `family.name` with `family.displayName`, change ID from `number` to `string`.

---

### Child Type

| Field | Mock Type | API Type | Proposed UI Type | Notes |
|-------|-----------|----------|------------------|-------|
| `id` | `number` | `string` (UUID) | `string` (UUID) | Breaking change |
| `name` | `string` | ❌ Not available | ❌ Removed | |
| `fullName` | ❌ Not available | ❌ Not available | ✅ `string` | Computed from `first_name + last_name` |
| `first_name` | ❌ Not available | ✅ `string` | ✅ `string` | Inherited from API |
| `last_name` | ❌ Not available | ✅ `string` | ✅ `string` | Inherited from API |
| `family` | ❌ Not available | ✅ `string` (UUID ref) | ✅ `string` (UUID ref) | Inherited from API |
| `ticket` | ✅ `TicketType` | ❌ Not available | ❌ Removed | |
| `ticketType` | ❌ Not available | ❌ Not available | ✅ `TicketType?` | Defaulted to 'event' |
| `checkedIn` | ✅ `boolean` | ❌ Not available | ✅ `boolean` | Derived from CheckInRecord |
| `checkInTime` | ✅ `string?` ("9:15 AM") | ❌ Not available | ✅ `string?` ("9:15 AM") | Formatted from CheckInRecord |
| `checkInActionId` | ✅ `string?` (UUID) | ❌ Not available | ✅ `string?` (UUID) | Client-side undo tracking |
| `checkInRecordId` | ❌ Not available | ❌ Not available | ✅ `string?` (UUID) | For undo API calls |
| `date_of_birth` | ❌ Not available | ✅ `string?` (ISO date) | ✅ `string?` (ISO date) | Inherited from API |
| `allergies` | ❌ Not available | ✅ `string?` | ✅ `string?` | Inherited from API |
| `medical_conditions` | ❌ Not available | ✅ `string?` | ✅ `string?` | Inherited from API |
| `special_needs` | ❌ Not available | ✅ `string?` | ✅ `string?` | Inherited from API |
| `qr_token` | ❌ Not available | ✅ `string?` | ✅ `string?` | Inherited from API |

**Migration Path**: Replace `child.name` with `child.fullName`, change ID from `number` to `string`.

---

## Code Examples

### Before (Mock Data)

```typescript
// Type definitions
type Family = {
  id: number;
  name: string;
  children: Child[];
  lastCheckInTime?: number;
};

type Child = {
  id: number;
  name: string;
  ticket: TicketType;
  checkedIn: boolean;
  checkInTime?: string;
  checkInActionId?: string;
};

// Mock data
const MOCK_FAMILIES: Family[] = [
  {
    id: 1,
    name: 'Garcia',
    children: [
      { id: 1, name: 'Isabella Garcia', ticket: 'event', checkedIn: false },
      { id: 2, name: 'Lucas Garcia', ticket: 'none', checkedIn: false },
    ],
  },
];

// Component usage
{#each families as family}
  <h2>{family.name}</h2>
  {#each family.children as child}
    <p>{child.name}</p>
    {#if child.checkedIn}
      <span>{child.checkInTime}</span>
    {/if}
  {/each}
{/each}
```

### After (API Integration)

```typescript
// Type definitions (extend API types)
import type {
  Family as ApiFamily,
  Child as ApiChild,
  CheckInRecord,
} from '$lib/api/types';

interface UiFamily extends ApiFamily {
  displayName: string;
  hasActiveCheckIns: boolean;
  children: UiChild[];
}

interface UiChild extends ApiChild {
  fullName: string;
  checkedIn: boolean;
  checkInTime?: string;
  checkInRecordId?: string;
  ticketType?: TicketType;
  checkInActionId?: string;
}

// Data loading
onMount(async () => {
  const [rawFamilies, checkIns] = await Promise.all([
    familyApi.list(),
    checkInApi.active(),
  ]);

  families = rawFamilies.map(family =>
    enrichFamilyWithUiState(family, checkIns)
  );
});

// Enrichment function
function enrichFamilyWithUiState(
  family: ApiFamily,
  checkIns: CheckInRecord[]
): UiFamily {
  const displayName = family.parents?.[0]?.name
    ?.split(' ')
    ?.slice(-1)[0] || 'Unknown';

  const children: UiChild[] = (family.children || []).map(child => {
    const record = checkIns.find(r => r.child === child.id);
    return {
      ...child,
      fullName: `${child.first_name} ${child.last_name}`,
      checkedIn: !!record,
      checkInTime: record ? formatTime(record.check_in_time) : undefined,
      checkInRecordId: record?.id,
      ticketType: 'event',
    };
  });

  return {
    ...family,
    displayName,
    hasActiveCheckIns: children.some(c => c.checkedIn),
    children,
  };
}

// Component usage (minimal changes)
{#each families as family}
  <h2>{family.displayName}</h2>  <!-- Changed: name → displayName -->
  {#each family.children as child}
    <p>{child.fullName}</p>  <!-- Changed: name → fullName -->
    {#if child.checkedIn}
      <span>{child.checkInTime}</span>  <!-- No change! -->
    {/if}
  {/each}
{/each}
```

---

## API Response Examples

### Family List Response

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "last_participation_date": "2025-12-01T10:30:00Z",
    "parents": [
      {
        "id": "660e8400-e29b-41d4-a716-446655440001",
        "name": "Maria Garcia",
        "phone": "555-0123",
        "email": "maria@example.com",
        "relationship_type": "MOM",
        "family": "550e8400-e29b-41d4-a716-446655440000"
      }
    ],
    "children": [
      {
        "id": "770e8400-e29b-41d4-a716-446655440002",
        "family": "550e8400-e29b-41d4-a716-446655440000",
        "first_name": "Isabella",
        "last_name": "Garcia",
        "birthdate": "2018-05-15",
        "allergies": "Peanuts",
        "notes": null,
        "qr_token": "ABC123",
        "last_participation_date": "2025-12-01T10:30:00Z"
      },
      {
        "id": "880e8400-e29b-41d4-a716-446655440003",
        "family": "550e8400-e29b-41d4-a716-446655440000",
        "first_name": "Lucas",
        "last_name": "Garcia",
        "birthdate": "2020-03-22",
        "allergies": null,
        "notes": null,
        "qr_token": "DEF456",
        "last_participation_date": "2025-12-01T10:30:00Z"
      }
    ]
  }
]
```

### Active Check-Ins Response

```json
[
  {
    "id": "990e8400-e29b-41d4-a716-446655440004",
    "child": "770e8400-e29b-41d4-a716-446655440002",
    "child_name": "Isabella Garcia",
    "session": "aa0e8400-e29b-41d4-a716-446655440005",
    "session_name": "Morning Care",
    "check_in_time": "2025-12-06T09:15:00Z",
    "check_out_time": null,
    "check_in_staff": "bb0e8400-e29b-41d4-a716-446655440006",
    "check_in_staff_name": "John Doe",
    "check_out_staff": null,
    "check_out_staff_name": null,
    "notes": null,
    "picked_up_by": null
  }
]
```

### Enriched UI State (what components see)

```typescript
const enrichedFamily: UiFamily = {
  // From API
  id: "550e8400-e29b-41d4-a716-446655440000",
  last_participation_date: "2025-12-01T10:30:00Z",
  parents: [ /* ... */ ],

  // Computed
  displayName: "Garcia",
  hasActiveCheckIns: true,

  // Enhanced children
  children: [
    {
      // From API
      id: "770e8400-e29b-41d4-a716-446655440002",
      family: "550e8400-e29b-41d4-a716-446655440000",
      first_name: "Isabella",
      last_name: "Garcia",
      birthdate: "2018-05-15",
      allergies: "Peanuts",
      qr_token: "ABC123",

      // Computed
      fullName: "Isabella Garcia",
      checkedIn: true,
      checkInTime: "9:15 AM",
      checkInRecordId: "990e8400-e29b-41d4-a716-446655440004",
      ticketType: "event",
      checkInActionId: undefined, // Set when we check in
    },
    {
      // From API
      id: "880e8400-e29b-41d4-a716-446655440003",
      family: "550e8400-e29b-41d4-a716-446655440000",
      first_name: "Lucas",
      last_name: "Garcia",
      birthdate: "2020-03-22",
      allergies: null,
      qr_token: "DEF456",

      // Computed
      fullName: "Lucas Garcia",
      checkedIn: false,
      checkInTime: undefined,
      checkInRecordId: undefined,
      ticketType: "event",
      checkInActionId: undefined,
    },
  ],
};
```

---

## Migration Checklist

### Type Changes

- [ ] Change all `number` IDs to `string` (UUID)
- [ ] Replace `family.name` with `family.displayName`
- [ ] Replace `child.name` with `child.fullName`
- [ ] Update `expandedFamilies` Set type: `Set<number>` → `Set<string>`
- [ ] Update all ID comparisons to use string equality

### Component Updates

- [ ] `FamilyCard.svelte`: Update property access
- [ ] `SessionIndicator.svelte`: Load real session
- [ ] `AddFamilyPanel.svelte`: Transform to API format
- [ ] Search filter: Use `displayName` and `fullName`
- [ ] Undo timer: Store `checkInRecordId` instead of just `actionId`

### State Management

- [ ] Replace `MOCK_FAMILIES` with API loading
- [ ] Add loading states (`isLoading`, `loadingError`)
- [ ] Implement enrichment function
- [ ] Update undo action store to use UUIDs
- [ ] Add WebSocket subscription

### API Integration

- [ ] Load families: `familyApi.list()`
- [ ] Load check-ins: `checkInApi.active()`
- [ ] Check-in action: `checkInApi.checkIn()`
- [ ] Undo action: `checkInApi.delete()` (or `undoCheckout()`)
- [ ] Add family: `familyApi.create()`
- [ ] Handle API errors gracefully

### Testing

- [ ] Unit tests for `enrichFamilyWithUiState()`
- [ ] Update existing tests to use UUIDs
- [ ] Add API integration tests
- [ ] Test error scenarios
- [ ] Test WebSocket updates
- [ ] Manual testing with real database

---

## Breaking Changes Summary

### What Breaks

1. **ID Types**: All code using numeric IDs will break
   - TypeScript compiler will catch these
   - Update all ID comparisons and storage

2. **Property Names**:
   - `family.name` → `family.displayName`
   - `child.name` → `child.fullName`
   - Simple find-replace

3. **Data Structure**:
   - No more `MOCK_FAMILIES` constant
   - Must load from API on mount

### What Still Works

- ✅ All UI logic (expansion, search, filters)
- ✅ Undo timer countdown
- ✅ Success toasts
- ✅ i18n translations
- ✅ Component structure
- ✅ Event handlers (with minor updates)

---

## TypeScript Compiler Help

The TypeScript compiler will catch most issues:

```typescript
// This will error after migration
const familyId: number = family.id;
//    ^^^^^^^^ Type 'string' is not assignable to type 'number'

// This will error after migration
<h2>{family.name}</h2>
//            ^^^^ Property 'name' does not exist on type 'UiFamily'

// Compiler suggests the fix:
<h2>{family.displayName}</h2>
```

This makes the migration safer - TypeScript helps find all places that need updating.

---

## Summary

The proposed UI types are a **superset** of the API types:
- ✅ All API fields are preserved
- ✅ Additional computed fields for UI convenience
- ✅ Client-side state (undo tracking) kept separate
- ✅ Type-safe with TypeScript compiler help
- ✅ Minimal component changes required

**Next Step**: Get approval on open questions, then begin implementation.
