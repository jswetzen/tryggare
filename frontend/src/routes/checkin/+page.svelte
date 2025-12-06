<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { Family, Child, TicketType, Session, FamilyApiResponse } from '$lib/checkin/types';
  import Icon from '$lib/components/ui/Icon.svelte';

  // Import checkin components
  import SessionIndicator from '$lib/components/checkin/SessionIndicator.svelte';
  import SuccessToast from '$lib/components/checkin/SuccessToast.svelte';
  import FamilyCard from '$lib/components/checkin/FamilyCard.svelte';
  import AddFamilyPanel from '$lib/components/checkin/AddFamilyPanel.svelte';

  // Import stores and utilities
  import {
    createUndoAction,
    removeUndoAction,
    getRemainingTime,
    getFamilyUndoActions,
    undoActionsWithTick,
    cleanup as cleanupUndoTimer,
  } from '$lib/checkin/stores/undoTimer';
  import { getVisibleFamilies } from '$lib/checkin/utils/familyVisibility';

  // Import API services
  import { checkinApi, ticketApi } from '$lib/api/services';
  import type { ApiError } from '$lib/api/client';
  import { websocketStore } from '$lib/stores/websocket';
  import type { WebSocketMessage } from '$lib/api/types';

  // ============================================================================
  // HELPER FUNCTIONS - Transform API responses to frontend types
  // ============================================================================

  function transformFamilyResponse(apiFamily: FamilyApiResponse): Family {
    return {
      id: apiFamily.id,
      last_name: apiFamily.last_name,
      display_name: apiFamily.display_name,
      name: apiFamily.display_name, // Use display_name for backward compatibility
      children: apiFamily.children.map((child) => ({
        id: child.id,
        first_name: child.first_name,
        last_name: child.last_name,
        name: `${child.first_name} ${child.last_name}`,
        ticket: (child.ticket_type as TicketType) || 'none',
        ticket_type: (child.ticket_type as TicketType) || 'none',
        ticket_details: child.ticket_details,
        checkedIn: child.is_checked_in || false, // Use backend check-in status
        family: child.family,
        birthdate: child.birthdate,
        allergies: child.allergies,
        notes: child.notes,
        qr_token: child.qr_token,
      })),
      parents: apiFamily.parents,
      last_participation_date: apiFamily.last_participation_date,
    };
  }

  // ============================================================================
  // STATE MANAGEMENT
  // ============================================================================

  let families = $state<Family[]>([]);
  let activeSession = $state<Session | null>(null);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let searchQuery = $state('');
  let expandedFamilies = $state<Set<string>>(new Set());
  let expandedChildId = $state<string | null>(null);
  let showAddPanel = $state(false);
  let successToast = $state<string | null>(null);

  // Subscribe to undo timer store for reactivity
  // The $ prefix makes this reactive to store updates
  // undoActionsWithTick returns { actions: UndoAction[], tick: number }
  let undoActionsData = $derived($undoActionsWithTick);
  let undoActions = $derived(undoActionsData.actions);

  // ============================================================================
  // DATA LOADING
  // ============================================================================

  async function loadFamilies() {
    try {
      loading = true;
      error = null;
      const response = await checkinApi.getFamilies();
      families = response.map(transformFamilyResponse);
    } catch (err) {
      const apiError = err as ApiError;
      error = apiError.message || 'Failed to load families';
      console.error('Error loading families:', err);
    } finally {
      loading = false;
    }
  }

  async function loadActiveSession() {
    try {
      const sessions = await checkinApi.getActiveSessions();
      if (sessions.length > 0) {
        activeSession = sessions[0]; // Use the first active session
      } else {
        error = 'No active session found';
      }
    } catch (err) {
      const apiError = err as ApiError;
      console.error('Error loading active session:', err);
      // Don't set error state here, as it's not critical
    }
  }

  // Load data on mount
  onMount(() => {
    // Load initial data
    Promise.all([loadFamilies(), loadActiveSession()]);

    // Connect to WebSocket for real-time updates
    websocketStore.connect();

    // Subscribe to WebSocket messages
    const unsubscribe = websocketStore.onMessage(handleWebSocketMessage);

    // Return cleanup function
    return () => {
      unsubscribe();
    };
  });

  // ============================================================================
  // HELPER FUNCTIONS
  // ============================================================================

  // Helper to get current time formatted
  function getCurrentTime(): string {
    return new Date().toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
    });
  }

  // Handle WebSocket messages for real-time updates
  function handleWebSocketMessage(message: WebSocketMessage) {
    if (message.type === 'child_checked_in') {
      // Another station checked in a child - reload family list to update UI
      // This ensures we show the latest check-in state across all stations
      loadFamilies();
    } else if (message.type === 'child_checked_out') {
      // Child was checked out - reload family list
      loadFamilies();
    }
  }

  // ============================================================================
  // COMPUTED VALUES
  // ============================================================================

  // Filter visible families based on search and visibility rules
  const visibleFamilies = $derived.by(() => {
    const filtered = getVisibleFamilies(families, undoActions);

    if (!searchQuery) return filtered;

    const query = searchQuery.toLowerCase();
    return filtered.filter(
      (family) =>
        family.name.toLowerCase().includes(query) ||
        family.children.some((child) => child.name.toLowerCase().includes(query))
    );
  });

  // ============================================================================
  // EFFECTS
  // ============================================================================

  // Auto-expand families when search matches child name (but not family name)
  // Collapse all families when search is cleared
  $effect(() => {
    if (!searchQuery) {
      // Clear all expanded families when search is cleared
      expandedFamilies = new Set();
      return;
    }

    const query = searchQuery.toLowerCase();
    const newExpanded = new Set<string>();

    // Use families directly instead of visibleFamilies to avoid circular dependency
    families.forEach((family) => {
      const familyNameMatches = family.name.toLowerCase().includes(query);

      if (!familyNameMatches) {
        const childNameMatches = family.children.some((child) =>
          child.name.toLowerCase().includes(query)
        );

        if (childNameMatches) {
          newExpanded.add(family.id);
        }
      }
    });

    // Only update if different to avoid unnecessary re-renders
    if (newExpanded.size !== expandedFamilies.size ||
        ![...newExpanded].every(id => expandedFamilies.has(id))) {
      expandedFamilies = newExpanded;
    }
  });

  // Cleanup on destroy
  onDestroy(() => {
    cleanupUndoTimer();
    websocketStore.disconnect();
  });

  // ============================================================================
  // EVENT HANDLERS
  // ============================================================================

  // Toggle family expansion
  function toggleFamily(familyId: string) {
    if (expandedFamilies.has(familyId)) {
      expandedFamilies.delete(familyId);
    } else {
      expandedFamilies.add(familyId);
    }
    expandedFamilies = new Set(expandedFamilies);
  }

  // Check in individual child
  async function checkInChild(familyId: string, childId: string) {
    if (!activeSession) {
      error = 'No active session';
      return;
    }

    try {
      // Call API to check in the child
      const checkInRecord = await checkinApi.checkIn({
        child: childId,
        session: activeSession.id,
      });

      // Create undo action
      const actionId = createUndoAction(familyId, [childId]);
      const checkInTime = getCurrentTime();

      // Update local state optimistically
      families = families.map((fam) => {
        if (fam.id !== familyId) return fam;
        return {
          ...fam,
          children: fam.children.map((child) => {
            if (child.id !== childId) return child;
            return {
              ...child,
              checkedIn: true,
              checkInTime,
              checkInActionId: actionId,
              checkInRecordId: checkInRecord.id, // Store the backend record ID
            };
          }),
        };
      });

      const family = families.find((f) => f.id === familyId);
      const child = family?.children.find((c) => c.id === childId);
      if (child) {
        successToast = $_('checkin.successCheckedIn', { values: { name: child.name } });
      }

      // Close expansion if open
      expandedChildId = null;
    } catch (err) {
      const apiError = err as ApiError;
      error = apiError.message || 'Failed to check in child';
      console.error('Error checking in child:', err);
    }
  }

  // Check in entire family
  async function checkInFamily(familyId: string) {
    if (!activeSession) {
      error = 'No active session';
      return;
    }

    const family = families.find((f) => f.id === familyId);
    if (!family) return;

    const childIdsToCheckIn = family.children
      .filter((c) => !c.checkedIn && c.ticket !== 'none')
      .map((c) => c.id);

    if (childIdsToCheckIn.length === 0) return;

    try {
      // Check in all children and collect their record IDs
      const checkInRecords = await Promise.all(
        childIdsToCheckIn.map((childId) =>
          checkinApi.checkIn({
            child: childId,
            session: activeSession.id,
          })
        )
      );

      // Map child IDs to record IDs
      const recordIdMap = new Map(
        checkInRecords.map((record) => [record.child, record.id])
      );

      const actionId = createUndoAction(familyId, childIdsToCheckIn);
      const checkInTime = getCurrentTime();

      families = families.map((fam) => {
        if (fam.id !== familyId) return fam;
        return {
          ...fam,
          lastCheckInTime: Date.now(),
          children: fam.children.map((child) => {
            if (!childIdsToCheckIn.includes(child.id)) return child;
            return {
              ...child,
              checkedIn: true,
              checkInTime,
              checkInActionId: actionId,
              checkInRecordId: recordIdMap.get(child.id), // Store the backend record ID
            };
          }),
        };
      });

      const count = childIdsToCheckIn.length;
      const childrenLabel = count === 1 ? $_('checkin.child') : $_('checkin.children');
      successToast = $_('checkin.successFamilyCheckedIn', {
        values: {
          family: family.name,
          count: count,
          childrenLabel: childrenLabel,
        },
      });
    } catch (err) {
      const apiError = err as ApiError;
      error = apiError.message || 'Failed to check in family';
      console.error('Error checking in family:', err);
    }
  }

  // Undo individual child check-in
  async function undoChildCheckIn(familyId: string, childId: string) {
    const family = families.find((f) => f.id === familyId);
    const child = family?.children.find((c) => c.id === childId);

    if (!child?.checkInActionId || !child?.checkInRecordId) {
      return;
    }

    try {
      // Call backend undo endpoint
      await checkInApi.undo(child.checkInRecordId);

      // Remove undo action from timer store
      removeUndoAction(child.checkInActionId);

      // Update local state
      families = families.map((fam) => {
        if (fam.id !== familyId) return fam;
        return {
          ...fam,
          children: fam.children.map((c) => {
            if (c.id !== childId) return c;
            return {
              ...c,
              checkedIn: false,
              checkInTime: undefined,
              checkInActionId: undefined,
              checkInRecordId: undefined,
            };
          }),
        };
      });

      if (child) {
        successToast = `${child.name} check-in undone`;
      }
    } catch (err) {
      const apiError = err as ApiError;
      error = apiError.message || 'Failed to undo check-in';
      console.error('Error undoing check-in:', err);
    }
  }

  // Undo family check-in
  async function undoFamilyCheckIn(familyId: string) {
    const family = families.find((f) => f.id === familyId);
    if (!family) return;

    // Find all undo actions for this family
    const familyActions = getFamilyUndoActions(familyId);
    if (familyActions.length === 0) return;

    // Get the most recent family action (should have multiple children)
    const familyAction = familyActions.find((a) => a.childIds.length > 1);
    if (!familyAction) return;

    try {
      // Find all children affected by this family action
      const affectedChildren = family.children.filter(
        (c) => familyAction.childIds.includes(c.id) && c.checkInActionId === familyAction.id
      );

      // Call backend undo endpoint for each child
      await Promise.all(
        affectedChildren
          .filter((c) => c.checkInRecordId)
          .map((c) => checkInApi.undo(c.checkInRecordId!))
      );

      // Remove undo action from timer store
      removeUndoAction(familyAction.id);

      // Update local state - undo all children affected by this action
      families = families.map((fam) => {
        if (fam.id !== familyId) return fam;
        return {
          ...fam,
          children: fam.children.map((c) => {
            if (
              familyAction.childIds.includes(c.id) &&
              c.checkInActionId === familyAction.id
            ) {
              return {
                ...c,
                checkedIn: false,
                checkInTime: undefined,
                checkInActionId: undefined,
                checkInRecordId: undefined,
              };
            }
            return c;
          }),
        };
      });

      successToast = `${family.name} check-in undone`;
    } catch (err) {
      const apiError = err as ApiError;
      error = apiError.message || 'Failed to undo family check-in';
      console.error('Error undoing family check-in:', err);
    }
  }

  // Assign ticket and check in child
  async function assignTicketAndCheckIn(
    familyId: string,
    childId: string,
    ticketType: TicketType
  ) {
    if (!activeSession) {
      error = 'No active session';
      return;
    }

    try {
      // Assign the ticket via API based on ticket type
      if (ticketType === 'event') {
        await ticketApi.assignEventTicket({
          child: childId,
          event: activeSession.event,
        });
      } else if (ticketType === 'session') {
        await ticketApi.assignSessionTicket({
          child: childId,
          session: activeSession.id,
        });
      }

      // Update local state
      families = families.map((fam) => {
        if (fam.id !== familyId) return fam;
        return {
          ...fam,
          children: fam.children.map((child) => {
            if (child.id !== childId) return child;
            return { ...child, ticket: ticketType, ticket_type: ticketType };
          }),
        };
      });

      // Then check in the child
      await checkInChild(familyId, childId);
    } catch (err) {
      const apiError = err as ApiError;
      error = apiError.message || 'Failed to assign ticket';
      console.error('Error assigning ticket:', err);
    }
  }

  // Add new family
  async function handleAddFamily(data: {
    familyName: string;
    childrenNames: string[];
    ticketType: TicketType;
    parents: Array<{
      name: string;
      phone: string;
      email: string;
      relationship_type: string;
    }>;
  }) {
    try {
      // Create family via API
      const newFamily = await checkinApi.createFamily({
        last_name: data.familyName,
        parents: data.parents,
        children: data.childrenNames.map((name) => ({
          first_name: name,
          last_name: data.familyName,
        })),
      });

      // Transform and add to local state
      const transformedFamily = transformFamilyResponse(newFamily);

      // Assign tickets to children if needed
      if (data.ticketType !== 'none' && activeSession) {
        for (const child of transformedFamily.children) {
          if (data.ticketType === 'event') {
            await ticketApi.assignEventTicket({
              child: child.id,
              event: activeSession.event,
            });
          } else if (data.ticketType === 'session') {
            await ticketApi.assignSessionTicket({
              child: child.id,
              session: activeSession.id,
            });
          }
          // Update ticket type in local state
          child.ticket = data.ticketType;
          child.ticket_type = data.ticketType;
        }
      }

      families = [...families, transformedFamily].sort((a, b) =>
        a.name.localeCompare(b.name)
      );
      showAddPanel = false;

      const count = transformedFamily.children.length;
      const childrenLabel = count === 1 ? $_('checkin.child') : $_('checkin.children');
      successToast = `${data.familyName} family added with ${count} ${childrenLabel}!`;

      // Auto-expand the new family
      expandedFamilies.add(transformedFamily.id);
      expandedFamilies = new Set(expandedFamilies);
    } catch (err) {
      const apiError = err as ApiError;
      error = apiError.message || 'Failed to create family';
      console.error('Error creating family:', err);
    }
  }
</script>

<svelte:head>
  <title>{$_('checkin.pageTitle')}</title>
</svelte:head>

<div class="min-h-screen bg-slate-100">
  <div class="max-w-4xl mx-auto p-5">
    {#if loading}
      <div class="text-center py-12">
        <p class="text-slate-600">{$_('common.loading')}</p>
      </div>
    {:else if error}
      <div class="mb-4 p-4 bg-red-50 border-2 border-red-500 rounded-lg">
        <p class="text-red-700">{error}</p>
        <button
          onclick={() => {
            error = null;
            loadFamilies();
          }}
          class="mt-2 px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
        >
          {$_('common.retry')}
        </button>
      </div>
    {:else}
      <!-- Session Indicator -->
      <SessionIndicator
        eventName={activeSession?.event_name || 'No Event'}
        sessionName={activeSession?.name || 'No Active Session'}
        sessionTime={activeSession
          ? `${new Date(activeSession.start_time).toLocaleTimeString('en-US', {
              hour: 'numeric',
              minute: '2-digit',
            })} - ${activeSession.end_time ? new Date(activeSession.end_time).toLocaleTimeString('en-US', {
              hour: 'numeric',
              minute: '2-digit',
            }) : 'Open'}`
          : ''}
        onChangeSession={() => alert('Change session functionality')}
        onAddFamily={() => (showAddPanel = true)}
      />

    <!-- Add Family Panel -->
    {#if showAddPanel}
      <AddFamilyPanel
        onAdd={handleAddFamily}
        onClose={() => (showAddPanel = false)}
      />
    {/if}

    <!-- Header -->
    <div class="mb-5">
      <h1 class="text-3xl font-bold text-blue-900">{$_('checkin.title')}</h1>
    </div>

    <!-- Search Box -->
    <div class="mb-4">
      <div class="relative">
        <Icon
          name="search"
          size="sm"
          class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
        />
        <input
          type="text"
          bind:value={searchQuery}
          placeholder={$_('checkin.searchPlaceholder')}
          class="w-full pl-10 pr-10 py-3 border-2 border-blue-500 rounded-lg bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
          data-testid="search-input"
        />
        {#if searchQuery}
          <button
            onclick={() => (searchQuery = '')}
            class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
            aria-label={$_('checkin.clearSearch')}
            data-testid="clear-search-button"
          >
            <Icon name="x" size="sm" />
          </button>
        {/if}
      </div>
    </div>

    <!-- Stats Header -->
    <div class="mb-4 flex items-center justify-between text-sm">
      <span class="text-slate-600" data-testid="family-count-text">
        {visibleFamilies.length}{' '}
        {visibleFamilies.length === 1 ? 'family' : 'families'}
        {searchQuery && ' matching search'}
      </span>
    </div>

    <!-- Family Cards -->
    <div class="space-y-3">
      {#if visibleFamilies.length === 0}
        <div class="text-center py-12 bg-white rounded-lg border-2 border-dashed border-slate-300">
          <p class="text-slate-500 mb-2">
            {searchQuery
              ? $_('checkin.noFamiliesFound', { values: { query: searchQuery } })
              : $_('checkin.noFamilies')}
          </p>
          {#if searchQuery}
            <p class="text-sm text-slate-400">{$_('checkin.tryDifferentSearch')}</p>
          {/if}
        </div>
      {:else}
        {#each visibleFamilies as family (family.id)}
          {@const _tick = undoActionsData.tick}
          {@const familyActions = getFamilyUndoActions(family.id)}
          {@const familyAction = familyActions.find((a) => a.childIds.length > 1)}
          {@const familyUndoSeconds = familyAction && _tick >= 0 ? getRemainingTime(familyAction.id) : null}
          <FamilyCard
            {family}
            expanded={expandedFamilies.has(family.id)}
            onToggle={() => toggleFamily(family.id)}
            onCheckInChild={(childId) => checkInChild(family.id, childId)}
            onCheckInFamily={() => checkInFamily(family.id)}
            onUndoChild={(childId) => undoChildCheckIn(family.id, childId)}
            onUndoFamily={() => undoFamilyCheckIn(family.id)}
            onAssignTicket={(childId, ticketType) =>
              assignTicketAndCheckIn(family.id, childId, ticketType)}
            {expandedChildId}
            onToggleChildExpansion={(childId) => {
              expandedChildId = childId;
            }}
            {getRemainingTime}
            {familyUndoSeconds}
          />
        {/each}
      {/if}
    </div>
  {/if}
  </div>
</div>

<!-- Success Toast -->
{#if successToast}
  <SuccessToast
    message={successToast}
    onClose={() => {
      successToast = null;
    }}
  />
{/if}

<!-- Animations -->
<style>
  :global(.animate-slide-in) {
    animation: slide-in 0.3s ease-out;
  }

  :global(.animate-expand) {
    animation: expand 0.2s ease-out;
  }

  @keyframes slide-in {
    from {
      transform: translateX(100%);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }

  @keyframes expand {
    from {
      opacity: 0;
      transform: translateY(-10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
</style>
