# Check-In API Integration - Quick Reference

This is a quick reference guide for developers implementing the API integration.

## TL;DR

1. **Extend API types** with computed UI properties
2. **Enrich data** after loading from API
3. **Update components** to use new property names
4. **All IDs are now UUIDs** (string, not number)

---

## Key Files

| File | Purpose |
|------|---------|
| `/lib/api/types.ts` | Base API types (don't modify) |
| `/lib/api/services.ts` | API client functions (ready to use) |
| `/lib/checkin/types.ts` | ✏️ **Extend with UI types** |
| `/lib/checkin/adapters.ts` | ✏️ **Create enrichment function** |
| `/routes/checkin/+page.svelte` | ✏️ **Replace mock data** |
| `/lib/components/checkin/FamilyCard.svelte` | ✏️ **Update property names** |

---

## Find & Replace Guide

### Quick Migrations

```bash
# Family name
family.name → family.displayName

# Child name
child.name → child.fullName

# ID types
let id: number → let id: string
Set<number> → Set<string>
```

---

## Code Snippets

### 1. Type Definitions

```typescript
// /lib/checkin/types.ts

import type { Family as ApiFamily, Child as ApiChild } from '$lib/api/types';

export interface UiFamily extends ApiFamily {
  displayName: string;
  hasActiveCheckIns: boolean;
  children: UiChild[];
}

export interface UiChild extends ApiChild {
  fullName: string;
  checkedIn: boolean;
  checkInTime?: string;
  checkInRecordId?: string;
  ticketType?: TicketType;
  checkInActionId?: string;
}

export type TicketType = 'event' | 'session' | 'none';
```

### 2. Enrichment Function

```typescript
// /lib/checkin/adapters.ts

import type { Family as ApiFamily, CheckInRecord } from '$lib/api/types';
import type { UiFamily, UiChild } from './types';

export function enrichFamilyWithUiState(
  family: ApiFamily,
  activeCheckIns: CheckInRecord[]
): UiFamily {
  // Compute display name from first parent's last name
  const displayName = family.parents?.[0]?.name
    ?.split(' ')
    ?.slice(-1)[0] || 'Unknown';

  // Enrich children
  const children: UiChild[] = (family.children || []).map(child => {
    const record = activeCheckIns.find(
      r => r.child === child.id && !r.check_out_time
    );

    return {
      ...child,
      fullName: `${child.first_name} ${child.last_name}`,
      checkedIn: !!record,
      checkInTime: record ? formatTime(record.check_in_time) : undefined,
      checkInRecordId: record?.id,
      ticketType: 'event', // Default
    };
  });

  return {
    ...family,
    displayName,
    hasActiveCheckIns: children.some(c => c.checkedIn),
    children,
  };
}

function formatTime(isoTime: string): string {
  return new Date(isoTime).toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  });
}
```

### 3. Page Load

```typescript
// /routes/checkin/+page.svelte

import { onMount } from 'svelte';
import { familyApi, checkInApi, sessionApi } from '$lib/api/services';
import { enrichFamilyWithUiState } from '$lib/checkin/adapters';
import type { UiFamily } from '$lib/checkin/types';

let families = $state<UiFamily[]>([]);
let currentSession = $state<Session | null>(null);
let isLoading = $state<boolean>(true);
let loadingError = $state<string | null>(null);

onMount(async () => {
  await loadPageData();
});

async function loadPageData() {
  isLoading = true;
  loadingError = null;

  try {
    // Parallel loading
    const [sessions, rawFamilies, checkIns] = await Promise.all([
      sessionApi.active(),
      familyApi.list(),
      checkInApi.active(),
    ]);

    currentSession = sessions[0] || null;

    // Enrich families
    families = rawFamilies.map(f =>
      enrichFamilyWithUiState(f, checkIns)
    );

  } catch (err) {
    console.error('Failed to load data:', err);
    loadingError = $_('checkin.errors.loadFailed');
  } finally {
    isLoading = false;
  }
}
```

### 4. Check-In Action

```typescript
// /routes/checkin/+page.svelte

import { checkInApi } from '$lib/api/services';
import { createUndoAction } from '$lib/checkin/stores/undoTimer';

async function checkInChild(familyId: string, childId: string) {
  // Find child
  const family = families.find(f => f.id === familyId);
  const child = family?.children.find(c => c.id === childId);
  if (!child || !currentSession) return;

  try {
    // Optimistic update
    updateChildState(childId, {
      checkedIn: true,
      checkInTime: formatTime(new Date().toISOString()),
    });

    // API call
    const record = await checkInApi.checkIn({
      child: childId,
      session: currentSession.id,
    });

    // Store record ID and start undo timer
    const actionId = createUndoAction(familyId, [childId]);
    updateChildState(childId, {
      checkInRecordId: record.id,
      checkInActionId: actionId,
    });

    // Success toast
    successToast = $_('checkin.successCheckedIn', {
      values: { name: child.fullName }
    });

  } catch (err) {
    // Rollback optimistic update
    updateChildState(childId, {
      checkedIn: false,
      checkInTime: undefined,
    });

    // Error toast
    const error = err as ApiError;
    errorToast = error.status === 400
      ? $_('checkin.errors.alreadyCheckedIn')
      : $_('checkin.errors.serverError');
  }
}

// Helper to update child state
function updateChildState(childId: string, updates: Partial<UiChild>) {
  families = families.map(family => ({
    ...family,
    children: family.children.map(child =>
      child.id === childId ? { ...child, ...updates } : child
    ),
  }));
}
```

### 5. Undo Action

```typescript
// /routes/checkin/+page.svelte

import { removeUndoAction } from '$lib/checkin/stores/undoTimer';

async function undoChildCheckIn(familyId: string, childId: string) {
  const family = families.find(f => f.id === familyId);
  const child = family?.children.find(c => c.id === childId);
  if (!child?.checkInRecordId) return;

  try {
    // Optimistic update
    updateChildState(childId, {
      checkedIn: false,
      checkInTime: undefined,
    });

    // API call - DELETE check-in record
    // NOTE: Requires backend DELETE endpoint
    await fetch(`/api/checkins/${child.checkInRecordId}/`, {
      method: 'DELETE',
      credentials: 'include',
    });

    // Remove undo timer
    if (child.checkInActionId) {
      removeUndoAction(child.checkInActionId);
    }

    successToast = $_('checkin.undoSuccess', {
      values: { name: child.fullName }
    });

  } catch (err) {
    // Rollback
    updateChildState(childId, {
      checkedIn: true,
      checkInTime: child.checkInTime, // Restore previous time
    });

    errorToast = $_('checkin.errors.serverError');
  }
}
```

### 6. WebSocket Integration

```typescript
// /routes/checkin/+page.svelte

import { onMount, onDestroy } from 'svelte';
import { websocketStore } from '$lib/stores/websocket';

let wsUnsubscribe: (() => void) | null = null;

onMount(() => {
  // Connect WebSocket
  websocketStore.connect();

  // Subscribe to messages
  wsUnsubscribe = websocketStore.onMessage((message) => {
    switch (message.type) {
      case 'child_checked_in':
        handleRemoteCheckIn(message.data.child_id);
        break;
      case 'child_checked_out':
        handleRemoteCheckOut(message.data.child_id);
        break;
    }
  });
});

onDestroy(() => {
  if (wsUnsubscribe) {
    wsUnsubscribe();
  }
  websocketStore.disconnect();
});

function handleRemoteCheckIn(childId: string) {
  // Update child state (no undo timer - not our action)
  updateChildState(childId, {
    checkedIn: true,
    checkInTime: formatTime(new Date().toISOString()),
  });
}

function handleRemoteCheckOut(childId: string) {
  updateChildState(childId, {
    checkedIn: false,
    checkInTime: undefined,
    checkInRecordId: undefined,
  });
}
```

### 7. Add Family

```typescript
// /routes/checkin/+page.svelte

import { familyApi } from '$lib/api/services';

async function handleAddFamily(data: {
  familyName: string;
  childrenNames: string[];
  ticketType: TicketType;
}) {
  try {
    // Transform to API format
    const apiData = {
      parents: [{
        name: data.familyName,
        relationship_type: 'OTHER',
      }],
      children: data.childrenNames.map(name => ({
        first_name: name,
        last_name: data.familyName,
        birthdate: '2020-01-01', // Default
      })),
    };

    // API call
    const newFamily = await familyApi.create(apiData);

    // Enrich and add to state
    const enriched = enrichFamilyWithUiState(newFamily, []);
    families = [...families, enriched].sort((a, b) =>
      a.displayName.localeCompare(b.displayName)
    );

    // Auto-expand
    expandedFamilies.add(newFamily.id);
    showAddPanel = false;

    successToast = $_('checkin.familyAdded', {
      values: { name: data.familyName }
    });

  } catch (err) {
    const error = err as ApiError;
    errorToast = error.status === 400
      ? $_('checkin.errors.validationError')
      : $_('checkin.errors.serverError');
  }
}
```

---

## Common Pitfalls

### 1. Forgetting to Enrich Data

❌ **Wrong**:
```typescript
const families = await familyApi.list();
// families[0].displayName  ← Error! Not enriched yet
```

✅ **Right**:
```typescript
const rawFamilies = await familyApi.list();
const families = rawFamilies.map(f => enrichFamilyWithUiState(f, checkIns));
// families[0].displayName  ← Works!
```

### 2. Using Number IDs

❌ **Wrong**:
```typescript
let expandedFamilies = $state<Set<number>>(new Set());
expandedFamilies.add(family.id); // Type error!
```

✅ **Right**:
```typescript
let expandedFamilies = $state<Set<string>>(new Set());
expandedFamilies.add(family.id); // Works!
```

### 3. Forgetting Optimistic Updates

❌ **Wrong**:
```typescript
async function checkInChild(id: string) {
  const record = await checkInApi.checkIn({ child: id, session: sessionId });
  // User waits for API response... :(
  updateChildState(id, { checkedIn: true });
}
```

✅ **Right**:
```typescript
async function checkInChild(id: string) {
  // Update UI immediately
  updateChildState(id, { checkedIn: true });
  try {
    const record = await checkInApi.checkIn({ child: id, session: sessionId });
  } catch (err) {
    // Rollback on error
    updateChildState(id, { checkedIn: false });
  }
}
```

### 4. Not Handling Loading States

❌ **Wrong**:
```typescript
onMount(async () => {
  const families = await familyApi.list();
  // What if this fails? User sees nothing!
});
```

✅ **Right**:
```typescript
let isLoading = $state(true);
let loadingError = $state<string | null>(null);

onMount(async () => {
  try {
    const families = await familyApi.list();
  } catch (err) {
    loadingError = $_('checkin.errors.loadFailed');
  } finally {
    isLoading = false;
  }
});

// In template
{#if isLoading}
  <LoadingSpinner />
{:else if loadingError}
  <ErrorMessage message={loadingError} />
{:else}
  <!-- Normal UI -->
{/if}
```

---

## Testing Checklist

### Unit Tests
- [ ] `enrichFamilyWithUiState()` computes displayName correctly
- [ ] `enrichFamilyWithUiState()` joins child names
- [ ] `enrichFamilyWithUiState()` marks children as checked in
- [ ] `formatTime()` formats ISO dates correctly

### Integration Tests
- [ ] Page loads families from API
- [ ] Check-in calls API with correct data
- [ ] Undo calls DELETE endpoint
- [ ] WebSocket updates reflect in UI
- [ ] Error states display correctly

### Manual Tests
- [ ] Page loads without errors
- [ ] Families display with correct names
- [ ] Check-in creates database record
- [ ] Undo deletes database record
- [ ] WebSocket updates from other stations work
- [ ] Add family creates family in database

---

## Debugging Tips

### Check Enrichment

```typescript
console.log('Raw API family:', rawFamily);
console.log('Enriched UI family:', enrichedFamily);
console.log('Display name:', enrichedFamily.displayName);
console.log('Children:', enrichedFamily.children.map(c => c.fullName));
```

### Check API Calls

```typescript
try {
  const record = await checkInApi.checkIn({ child: id, session: sessionId });
  console.log('Check-in successful:', record);
} catch (err) {
  console.error('Check-in failed:', err);
  if (err instanceof ApiError) {
    console.log('Status:', err.status);
    console.log('Details:', err.details);
  }
}
```

### Check WebSocket

```typescript
websocketStore.state.subscribe(state => {
  console.log('WebSocket state:', state);
  console.log('Connected:', state.connected);
  console.log('Last message:', state.lastMessage);
});
```

---

## API Endpoints Reference

| Action | Method | Endpoint | Request | Response |
|--------|--------|----------|---------|----------|
| List families | GET | `/api/families/` | - | `Family[]` |
| Search families | GET | `/api/families/?search={query}` | - | `Family[]` |
| Create family | POST | `/api/families/` | `{ parents, children }` | `Family` |
| Active sessions | GET | `/api/sessions/active/` | - | `Session[]` |
| Active check-ins | GET | `/api/checkins/active/` | - | `CheckInRecord[]` |
| Check in | POST | `/api/checkins/check_in/` | `{ child, session }` | `CheckInRecord` |
| Undo (delete) | DELETE | `/api/checkins/{id}/` | - | `204 No Content` |

---

## Summary

1. **Load data**: `familyApi.list()`, `checkInApi.active()`
2. **Enrich data**: `enrichFamilyWithUiState()`
3. **Update components**: Use `displayName` and `fullName`
4. **Handle actions**: Optimistic updates + API calls
5. **Handle WebSocket**: Update local state on messages

**Key principle**: API types are the source of truth, UI types extend them with computed properties.
