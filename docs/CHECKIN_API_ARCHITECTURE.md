# Check-In Page API Architecture

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Check-In Page Component                       │
│                    /routes/checkin/+page.svelte                     │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │   Initial Load        │
                    │   - sessionApi        │
                    │   - familyApi         │
                    │   - checkInApi        │
                    └───────────┬───────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                         Enrichment Layer                             │
│                   /lib/checkin/adapters.ts                          │
│                                                                      │
│  enrichFamilyWithUiState(family, checkIns, sessions)                │
│    ├─ Compute displayName from parents[0].name                     │
│    ├─ Join first_name + last_name → fullName                       │
│    ├─ Lookup CheckInRecord → checkedIn, checkInTime                │
│    ├─ Lookup Ticket → ticketType                                   │
│    └─ Add client-side state (checkInActionId for undo)             │
└───────────────────────────────┬─────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                         UI State Layer                               │
│                    /lib/checkin/types.ts                            │
│                                                                      │
│  UiFamily extends ApiFamily {                                       │
│    displayName: string;          // Computed                        │
│    hasActiveCheckIns: boolean;   // Computed                        │
│    children: UiChild[];          // Enhanced                        │
│  }                                                                   │
│                                                                      │
│  UiChild extends ApiChild {                                         │
│    fullName: string;             // first_name + last_name          │
│    checkedIn: boolean;           // From CheckInRecord lookup       │
│    checkInTime?: string;         // Formatted display time          │
│    checkInRecordId?: string;     // For API undo calls              │
│    ticketType?: TicketType;      // From Ticket lookup              │
│    checkInActionId?: string;     // Client-side undo tracking       │
│  }                                                                   │
└───────────────────────────────┬─────────────────────────────────────┘
                                ↓
                    ┌───────────┴───────────┐
                    │   UI Components       │
                    │   - FamilyCard        │
                    │   - AddFamilyPanel    │
                    │   - SessionIndicator  │
                    └───────────────────────┘
```

## Data Flow Sequences

### 1. Page Load Sequence

```
User navigates to /checkin
        │
        ├─► [Parallel Fetch]
        │       │
        │       ├─► sessionApi.active()
        │       │       └─► Session { id, name, start_time, ... }
        │       │
        │       ├─► familyApi.list()
        │       │       └─► Family[] with nested parents[], children[]
        │       │
        │       └─► checkInApi.active()
        │               └─► CheckInRecord[] for current session
        │
        ├─► [Enrich Data]
        │       │
        │       └─► enrichFamilyWithUiState()
        │               ├─ Map families → UiFamily[]
        │               ├─ Join check-in records
        │               └─ Compute display properties
        │
        └─► [Render UI]
                ├─ Show session indicator
                ├─ Render family cards
                └─ Setup WebSocket listener
```

### 2. Check-In Action Sequence

```
User clicks "Check In" on child
        │
        ├─► [Optimistic Update]
        │       │
        │       └─► Update local state: child.checkedIn = true
        │               └─► UI shows "Checked In" immediately
        │
        ├─► [API Call]
        │       │
        │       └─► checkInApi.checkIn({ child: id, session: id })
        │               │
        │               ├─► [Success: 201 Created]
        │               │       └─► CheckInRecord { id, child, session, ... }
        │               │               │
        │               │               ├─► Store record ID for undo
        │               │               ├─► Start 30-second undo timer
        │               │               └─► Show success toast
        │               │
        │               └─► [Error: 400 Bad Request]
        │                       └─► Rollback optimistic update
        │                               └─► Show error toast
        │
        └─► [WebSocket Broadcast]
                │
                └─► Other stations receive child_checked_in message
                        └─► Update their local state
```

### 3. Undo Action Sequence

```
User clicks "Undo" within 30 seconds
        │
        ├─► [Optimistic Update]
        │       │
        │       └─► Update local state: child.checkedIn = false
        │               └─► UI shows unchecked immediately
        │
        ├─► [API Call]
        │       │
        │       └─► DELETE /api/checkins/{recordId}/ (proposed)
        │               │
        │               ├─► [Success: 204 No Content]
        │               │       └─► Remove undo timer
        │               │               └─► Show "Undo successful" toast
        │               │
        │               └─► [Error: 404 Not Found]
        │                       └─► Record already removed
        │                               └─► Keep optimistic state
        │
        └─► [WebSocket Broadcast]
                │
                └─► Other stations receive child_checked_out message
                        └─► Update their local state
```

### 4. Search Sequence

```
User types in search box
        │
        ├─► [Debounce 300ms]
        │
        ├─► [Client-Side Filter] (if families already loaded)
        │       │
        │       └─► Filter by family name or child name
        │               └─► Re-render filtered list
        │
        └─► [API Search] (if query is complex or fresh load needed)
                │
                └─► familyApi.search(query)
                        └─► Family[] matching query
                                └─► Enrich and render
```

### 5. Add Family Sequence

```
User submits "Add Family" form
        │
        ├─► [Transform Data]
        │       │
        │       └─► Convert UI form to API format
        │               {
        │                 parents: [{ name, phone, email, relationship_type }],
        │                 children: [{ first_name, last_name, birthdate, ... }]
        │               }
        │
        ├─► [API Call]
        │       │
        │       └─► familyApi.create(data)
        │               │
        │               ├─► [Success: 201 Created]
        │               │       └─► Family { id, parents[], children[] }
        │               │               │
        │               │               ├─► Enrich new family
        │               │               ├─► Add to local state
        │               │               ├─► Sort families alphabetically
        │               │               ├─► Auto-expand new family
        │               │               └─► Show success toast
        │               │
        │               └─► [Error: 400 Bad Request]
        │                       └─► Show validation errors
        │                               └─► Keep form open with errors
        │
        └─► [Close Form]
                └─► Hide add family panel
```

### 6. WebSocket Real-Time Updates

```
WebSocket receives message
        │
        ├─► [Parse Message Type]
        │
        ├─► [child_checked_in]
        │       │
        │       └─► Find family in local state
        │               └─► Update child.checkedIn = true
        │                       └─► Re-render (without undo timer - not our action)
        │
        ├─► [child_checked_out]
        │       │
        │       └─► Find family in local state
        │               └─► Update child.checkedIn = false
        │                       └─► Re-render
        │
        ├─► [session_started]
        │       │
        │       └─► Update session indicator
        │               └─► Reload families for new session
        │
        └─► [session_ended]
                │
                └─► Update session indicator
                        └─► Show "Session Ended" notice
```

## State Management Strategy

### Local Component State

```typescript
// In +page.svelte

// Loading states
let isLoading = $state<boolean>(true);
let loadingError = $state<string | null>(null);

// Core data (enriched)
let families = $state<UiFamily[]>([]);
let currentSession = $state<Session | null>(null);

// UI state
let searchQuery = $state<string>('');
let expandedFamilies = $state<Set<string>>(new Set());
let expandedChildId = $state<string | null>(null);
let showAddPanel = $state<boolean>(false);
let successToast = $state<string | null>(null);

// Undo timer state (from store)
let undoActionsData = $derived($undoActionsWithTick);
let undoActions = $derived(undoActionsData.actions);

// Derived state
const visibleFamilies = $derived.by(() => {
  const filtered = getVisibleFamilies(families, undoActions);
  if (!searchQuery) return filtered;
  return filtered.filter(/* search logic */);
});
```

### Undo Timer Store

Keep existing `/lib/checkin/stores/undoTimer.ts` with minor changes:

```typescript
// Change from numeric IDs to UUIDs
interface UndoAction {
  id: string;              // UUID of undo action
  checkInRecordId: string; // UUID of CheckInRecord (for API calls)
  familyId: string;        // UUID of family
  childIds: string[];      // UUIDs of children
  timestamp: number;       // Unix timestamp
  expiresAt: number;       // timestamp + 30000
}

// Add method to create undo action from check-in response
function createUndoActionFromCheckIn(checkInRecord: CheckInRecord) {
  return createUndoAction(
    checkInRecord.id,         // checkInRecordId
    extractFamilyId(/* ... */), // familyId
    [checkInRecord.child]     // childIds
  );
}
```

### WebSocket Store

Reuse existing `/lib/stores/websocket.ts`:

```typescript
// In +page.svelte

onMount(() => {
  // Connect WebSocket
  websocketStore.connect();

  // Subscribe to messages
  const unsubscribe = websocketStore.onMessage((message) => {
    handleWebSocketMessage(message);
  });

  // Cleanup
  return () => {
    unsubscribe();
    websocketStore.disconnect();
  };
});

function handleWebSocketMessage(message: WebSocketMessage) {
  switch (message.type) {
    case 'child_checked_in':
      // Update local state for this child
      updateChildCheckInStatus(message.data.child_id, true);
      break;
    case 'child_checked_out':
      // Update local state for this child
      updateChildCheckInStatus(message.data.child_id, false);
      break;
    case 'session_started':
      // Reload page data
      loadPageData();
      break;
    case 'session_ended':
      // Show notice, reload data
      currentSession = null;
      break;
  }
}
```

## Error Handling Architecture

### Error Types

```typescript
// Extend ApiError with user-friendly messages
interface CheckInError extends ApiError {
  userMessage: string;  // Translated message for display
  recoverable: boolean; // Can user retry?
  action?: () => void;  // Optional recovery action
}

function handleCheckInError(error: ApiError): CheckInError {
  switch (error.status) {
    case 400:
      if (error.details?.child?.includes('already checked in')) {
        return {
          ...error,
          userMessage: $_('checkin.errors.alreadyCheckedIn'),
          recoverable: false,
        };
      }
      return {
        ...error,
        userMessage: $_('checkin.errors.validationError'),
        recoverable: true,
      };
    case 401:
      return {
        ...error,
        userMessage: $_('checkin.errors.unauthorized'),
        recoverable: true,
        action: () => window.location.href = '/login',
      };
    case 0:
      return {
        ...error,
        userMessage: $_('checkin.errors.networkError'),
        recoverable: true,
      };
    default:
      return {
        ...error,
        userMessage: $_('checkin.errors.serverError'),
        recoverable: true,
      };
  }
}
```

### Loading State UI

```svelte
{#if isLoading}
  <div class="flex items-center justify-center min-h-screen">
    <div class="text-center">
      <LoadingSpinner size="lg" />
      <p class="mt-4 text-slate-600">{$_('checkin.loading')}</p>
    </div>
  </div>
{:else if loadingError}
  <div class="flex items-center justify-center min-h-screen">
    <div class="text-center">
      <Icon name="alert-circle" size="lg" class="text-red-500 mx-auto" />
      <p class="mt-4 text-red-600">{loadingError}</p>
      <button
        onclick={loadPageData}
        class="mt-4 px-4 py-2 bg-blue-500 text-white rounded"
      >
        {$_('common.retry')}
      </button>
    </div>
  </div>
{:else}
  <!-- Normal UI -->
{/if}
```

## Performance Optimization Strategy

### 1. Initial Load

```typescript
async function loadPageData() {
  isLoading = true;
  loadingError = null;

  try {
    // Parallel loading for speed
    const [sessionsResult, familiesResult, checkInsResult] = await Promise.all([
      sessionApi.active().catch(err => ({ data: [], error: err })),
      familyApi.list().catch(err => ({ data: [], error: err })),
      checkInApi.active().catch(err => ({ data: [], error: err })),
    ]);

    // Handle partial failures
    if (sessionsResult.error) {
      console.error('Failed to load sessions:', sessionsResult.error);
    }
    currentSession = sessionsResult.data?.[0] || null;

    if (familiesResult.error) {
      throw familiesResult.error;
    }
    const rawFamilies = familiesResult.data;

    if (checkInsResult.error) {
      console.error('Failed to load check-ins:', checkInsResult.error);
    }
    const activeCheckIns = checkInsResult.data || [];

    // Enrich data
    families = rawFamilies.map(family =>
      enrichFamilyWithUiState(family, activeCheckIns, [currentSession])
    );

  } catch (err) {
    loadingError = handleCheckInError(err).userMessage;
  } finally {
    isLoading = false;
  }
}
```

### 2. Search Optimization

```typescript
// Debounced search
let searchTimeout: number | null = null;
const SEARCH_DEBOUNCE_MS = 300;

function handleSearchInput(event: Event) {
  const query = (event.target as HTMLInputElement).value;

  if (searchTimeout) {
    clearTimeout(searchTimeout);
  }

  // Update UI immediately (client-side filter)
  searchQuery = query;

  // Debounce API call
  searchTimeout = setTimeout(async () => {
    if (query.length >= 2) {
      // Optionally fetch from API for server-side search
      // const results = await familyApi.search(query);
      // families = results.map(enrichFamilyWithUiState);
    }
  }, SEARCH_DEBOUNCE_MS);
}
```

### 3. Granular Updates

```typescript
// Instead of replacing entire families array, update specific family
function updateChildCheckInStatus(childId: string, checkedIn: boolean) {
  families = families.map(family => {
    const childIndex = family.children.findIndex(c => c.id === childId);
    if (childIndex === -1) return family;

    const updatedChildren = [...family.children];
    updatedChildren[childIndex] = {
      ...updatedChildren[childIndex],
      checkedIn,
      checkInTime: checkedIn ? formatTime(new Date()) : undefined,
    };

    return {
      ...family,
      children: updatedChildren,
      hasActiveCheckIns: updatedChildren.some(c => c.checkedIn),
    };
  });
}
```

## Testing Strategy

### Unit Tests

```typescript
// Test enrichment function
describe('enrichFamilyWithUiState', () => {
  it('should compute displayName from first parent', () => {
    const family: ApiFamily = {
      id: '123',
      parents: [{ name: 'John Smith', ... }],
      children: [],
    };
    const enriched = enrichFamilyWithUiState(family, [], []);
    expect(enriched.displayName).toBe('Smith');
  });

  it('should join child names', () => {
    const family: ApiFamily = {
      id: '123',
      children: [{ first_name: 'Emma', last_name: 'Smith', ... }],
    };
    const enriched = enrichFamilyWithUiState(family, [], []);
    expect(enriched.children[0].fullName).toBe('Emma Smith');
  });

  it('should mark child as checked in when record exists', () => {
    const family: ApiFamily = { id: '123', children: [{ id: 'c1', ... }] };
    const checkIns: CheckInRecord[] = [{
      id: 'r1',
      child: 'c1',
      check_in_time: '2025-01-01T10:00:00Z',
      ...
    }];
    const enriched = enrichFamilyWithUiState(family, checkIns, []);
    expect(enriched.children[0].checkedIn).toBe(true);
  });
});
```

### Integration Tests

```typescript
describe('Check-In Page', () => {
  it('should load families on mount', async () => {
    // Mock API responses
    vi.mocked(familyApi.list).mockResolvedValue([mockFamily]);
    vi.mocked(checkInApi.active).mockResolvedValue([]);

    render(CheckInPage);

    await waitFor(() => {
      expect(screen.getByText('Garcia')).toBeInTheDocument();
    });
  });

  it('should check in child and show undo timer', async () => {
    vi.mocked(checkInApi.checkIn).mockResolvedValue(mockCheckInRecord);

    render(CheckInPage);
    await userEvent.click(screen.getByTestId('check-in-child-1'));

    expect(checkInApi.checkIn).toHaveBeenCalledWith({
      child: 'child-1',
      session: 'session-1',
    });

    await waitFor(() => {
      expect(screen.getByText(/30/)).toBeInTheDocument(); // Undo timer
    });
  });
});
```

## Summary

This architecture provides:

1. **Type Safety**: Using real API types with TypeScript
2. **Performance**: Parallel loading, debounced search, granular updates
3. **UX**: Optimistic updates, real-time WebSocket sync, 30-second undo
4. **Maintainability**: Clean separation between API layer and UI layer
5. **Testability**: Pure functions for enrichment, mockable API calls
6. **i18n Support**: All user-facing strings translated
7. **Error Handling**: Graceful degradation with user-friendly messages

Next step: Begin Phase 1 implementation (type layer and enrichment).
