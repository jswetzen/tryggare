<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { t } from 'svelte-i18n';
  import { websocketStore } from '$lib/stores/websocket';
  import { familyApi, childApi, sessionApi, checkInApi } from '$lib/api/services';
  import type {
    Family as ApiFamily,
    Child as ApiChild,
    Session,
    WebSocketMessage
  } from '$lib/api/types';
  import type {
    Family as CheckinFamily,
    Child as CheckinChild,
    TicketType
  } from '$lib/checkin/types';

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

  // Import existing UI components
  import PageHeader from '$lib/components/PageHeader.svelte';
  import SearchBox from '$lib/components/SearchBox.svelte';
  import { EmptyState, Alert, Icon } from '$lib/components/ui';

  // State management
  let searchQuery = $state('');
  let apiFamilies = $state<ApiFamily[]>([]);
  let sessions = $state<Session[]>([]);
  let selectedSession = $state<string | null>(null);
  let loading = $state(false);
  let error = $state<string | null>(null);
  let successMessage = $state<string | null>(null);
  let showAddPanel = $state(false);
  let expandedFamilies = $state(new Set<number>());
  let expandedChildId = $state<number | null>(null);

  // Child ID to API ID mapping
  let childIdToApiId = $state(new Map<number, string>());
  let nextCheckInId = $state(1);

  let unsubscribe: (() => void) | null = null;

  // Subscribe to undo timer store for reactivity
  const undoActions = $undoActionsWithTick;

  // Helper to get current time formatted
  function getCurrentTime(): string {
    return new Date().toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
    });
  }

  // Helper to determine ticket type from child data
  function getTicketType(child: ApiChild): TicketType {
    // TODO: This should be based on actual ticket/registration data
    // For now, we'll default to 'event' for all children
    // In a real implementation, check if child has event pass, session ticket, or neither
    return 'event';
  }

  // Transform API family data to checkin family format
  function transformFamily(apiFamily: ApiFamily, familyId: number): CheckinFamily {
    const children: CheckinChild[] = (apiFamily.children || []).map((apiChild, index) => {
      const childId = familyId * 1000 + index; // Generate unique numeric ID
      childIdToApiId.set(childId, apiChild.id);

      return {
        id: childId,
        name: `${apiChild.first_name} ${apiFamily.family_name}`,
        ticket: getTicketType(apiChild),
        checkedIn: false,
      };
    });

    return {
      id: familyId,
      name: apiFamily.family_name || `${apiFamily.primary_contact_name}'s Family`,
      children,
    };
  }

  // Transform API families to checkin families
  const checkinFamilies = $derived(
    apiFamilies.map((apiFamily, index) => transformFamily(apiFamily, index + 1))
  );

  // Get visible families based on search and visibility rules
  const visibleFamilies = $derived.by(() => {
    const filtered = getVisibleFamilies(checkinFamilies, undoActions);

    if (!searchQuery) return filtered;

    const query = searchQuery.toLowerCase();
    return filtered.filter(
      (family) =>
        family.name.toLowerCase().includes(query) ||
        family.children.some((child) => child.name.toLowerCase().includes(query))
    );
  });

  // Auto-expand families when search matches child name (but not family name)
  $effect(() => {
    if (!searchQuery) return;

    const query = searchQuery.toLowerCase();

    visibleFamilies.forEach((family) => {
      const familyNameMatches = family.name.toLowerCase().includes(query);

      if (!familyNameMatches) {
        const childNameMatches = family.children.some((child) =>
          child.name.toLowerCase().includes(query)
        );

        if (childNameMatches) {
          expandedFamilies.add(family.id);
          // Trigger reactivity
          expandedFamilies = new Set(expandedFamilies);
        }
      }
    });
  });

  // Get selected session data
  const selectedSessionData = $derived(
    sessions.find((s) => s.id === selectedSession)
  );

  onMount(() => {
    // Connect to WebSocket for real-time updates
    websocketStore.connect();

    // Subscribe to WebSocket messages
    unsubscribe = websocketStore.onMessage(handleWebSocketMessage);

    // Load active sessions
    loadSessions();
  });

  onDestroy(() => {
    if (unsubscribe) {
      unsubscribe();
    }
    cleanupUndoTimer();
  });

  function handleWebSocketMessage(message: WebSocketMessage) {
    if (message.type === 'child_checked_in') {
      console.log('Child checked in:', message.data);
      // Refresh the search results
      if (apiFamilies.length > 0) {
        searchFamilies();
      }
    }
  }

  async function loadSessions() {
    try {
      sessions = await sessionApi.active();
      // Auto-select first session if only one
      if (sessions.length === 1) {
        selectedSession = sessions[0].id;
      }
    } catch (err) {
      console.error('Failed to load sessions:', err);
      error = $t('checkin.sessionsError');
    }
  }

  async function searchFamilies() {
    if (!searchQuery.trim()) {
      apiFamilies = [];
      return;
    }

    loading = true;
    error = null;

    try {
      const results = await familyApi.search(searchQuery);
      apiFamilies = results;

      // Load children for all families
      for (const family of apiFamilies) {
        const familyChildren = await childApi.list(family.id);
        family.children = familyChildren;
      }
    } catch (err) {
      console.error('Search failed:', err);
      error = $t('checkin.searchError');
      apiFamilies = [];
    } finally {
      loading = false;
    }
  }

  // Toggle family expansion
  function toggleFamily(familyId: number) {
    if (expandedFamilies.has(familyId)) {
      expandedFamilies.delete(familyId);
    } else {
      expandedFamilies.add(familyId);
    }
    expandedFamilies = new Set(expandedFamilies);
  }

  // Check in individual child
  async function checkInChild(familyId: number, childId: number) {
    if (!selectedSession) {
      error = $t('checkin.selectError');
      return;
    }

    const apiChildId = childIdToApiId.get(childId);
    if (!apiChildId) {
      error = 'Child not found';
      return;
    }

    try {
      // Call API to check in
      await checkInApi.checkIn({
        child: apiChildId,
        session: selectedSession,
      });

      // Create undo action
      const actionId = createUndoAction(familyId, [childId]);
      const checkInTime = getCurrentTime();

      // Update local state
      const familyIndex = checkinFamilies.findIndex((f) => f.id === familyId);
      if (familyIndex !== -1) {
        const family = checkinFamilies[familyIndex];
        const childIndex = family.children.findIndex((c) => c.id === childId);
        if (childIndex !== -1) {
          family.children[childIndex] = {
            ...family.children[childIndex],
            checkedIn: true,
            checkInTime,
            checkInActionId: actionId,
          };
          // Trigger reactivity
          apiFamilies = [...apiFamilies];

          // Show success message
          const childName = family.children[childIndex].name;
          successMessage = `${childName} checked in!`;
        }
      }

      // Close expansion if open
      expandedChildId = null;
    } catch (err: any) {
      console.error('Check-in failed:', err);
      error = err.message || $t('checkin.error');
    }
  }

  // Check in entire family
  async function checkInFamily(familyId: number) {
    if (!selectedSession) {
      error = $t('checkin.selectError');
      return;
    }

    const family = checkinFamilies.find((f) => f.id === familyId);
    if (!family) return;

    const childrenToCheckIn = family.children.filter(
      (c) => !c.checkedIn && c.ticket !== 'none'
    );

    if (childrenToCheckIn.length === 0) return;

    try {
      // Check in all children
      for (const child of childrenToCheckIn) {
        const apiChildId = childIdToApiId.get(child.id);
        if (apiChildId) {
          await checkInApi.checkIn({
            child: apiChildId,
            session: selectedSession,
          });
        }
      }

      // Create undo action for all children
      const childIds = childrenToCheckIn.map((c) => c.id);
      const actionId = createUndoAction(familyId, childIds);
      const checkInTime = getCurrentTime();

      // Update local state
      const familyIndex = checkinFamilies.findIndex((f) => f.id === familyId);
      if (familyIndex !== -1) {
        const fam = checkinFamilies[familyIndex];
        fam.children = fam.children.map((child) => {
          if (childIds.includes(child.id)) {
            return {
              ...child,
              checkedIn: true,
              checkInTime,
              checkInActionId: actionId,
            };
          }
          return child;
        });
        fam.lastCheckInTime = Date.now();
        // Trigger reactivity
        apiFamilies = [...apiFamilies];

        successMessage = `${family.name} family checked in (${childrenToCheckIn.length} ${
          childrenToCheckIn.length === 1 ? 'child' : 'children'
        })!`;
      }
    } catch (err: any) {
      console.error('Family check-in failed:', err);
      error = err.message || $t('checkin.error');
    }
  }

  // Undo individual child check-in
  async function undoChildCheckIn(familyId: number, childId: number) {
    const family = checkinFamilies.find((f) => f.id === familyId);
    const child = family?.children.find((c) => c.id === childId);

    if (!child?.checkInActionId) return;

    const apiChildId = childIdToApiId.get(childId);
    if (!apiChildId) return;

    try {
      // TODO: Call API to undo check-in
      // For now, just update local state

      removeUndoAction(child.checkInActionId);

      // Update local state
      const familyIndex = checkinFamilies.findIndex((f) => f.id === familyId);
      if (familyIndex !== -1) {
        const fam = checkinFamilies[familyIndex];
        const childIndex = fam.children.findIndex((c) => c.id === childId);
        if (childIndex !== -1) {
          fam.children[childIndex] = {
            ...fam.children[childIndex],
            checkedIn: false,
            checkInTime: undefined,
            checkInActionId: undefined,
          };
          // Trigger reactivity
          apiFamilies = [...apiFamilies];

          successMessage = `${child.name} check-in undone`;
        }
      }
    } catch (err: any) {
      console.error('Undo failed:', err);
      error = err.message || 'Failed to undo check-in';
    }
  }

  // Undo family check-in
  async function undoFamilyCheckIn(familyId: number) {
    const family = checkinFamilies.find((f) => f.id === familyId);
    if (!family) return;

    // Find all undo actions for this family
    const familyActions = getFamilyUndoActions(familyId);
    if (familyActions.length === 0) return;

    // Get the most recent family action (should have multiple children)
    const familyAction = familyActions.find((a) => a.childIds.length > 1);
    if (!familyAction) return;

    try {
      // TODO: Call API to undo check-ins
      // For now, just update local state

      removeUndoAction(familyAction.id);

      // Update local state
      const familyIndex = checkinFamilies.findIndex((f) => f.id === familyId);
      if (familyIndex !== -1) {
        const fam = checkinFamilies[familyIndex];
        fam.children = fam.children.map((c) => {
          if (
            familyAction.childIds.includes(c.id) &&
            c.checkInActionId === familyAction.id
          ) {
            return {
              ...c,
              checkedIn: false,
              checkInTime: undefined,
              checkInActionId: undefined,
            };
          }
          return c;
        });
        // Trigger reactivity
        apiFamilies = [...apiFamilies];

        successMessage = `${family.name} check-in undone`;
      }
    } catch (err: any) {
      console.error('Undo family failed:', err);
      error = err.message || 'Failed to undo family check-in';
    }
  }

  // Assign ticket and check in child
  async function assignTicketAndCheckIn(
    familyId: number,
    childId: number,
    ticketType: TicketType
  ) {
    // First update the ticket type locally
    const familyIndex = checkinFamilies.findIndex((f) => f.id === familyId);
    if (familyIndex !== -1) {
      const family = checkinFamilies[familyIndex];
      const childIndex = family.children.findIndex((c) => c.id === childId);
      if (childIndex !== -1) {
        family.children[childIndex] = {
          ...family.children[childIndex],
          ticket: ticketType,
        };
        // Trigger reactivity
        apiFamilies = [...apiFamilies];
      }
    }

    // Then check in the child
    setTimeout(() => checkInChild(familyId, childId), 0);
  }

  // Add new family
  async function handleAddFamily(data: {
    familyName: string;
    childrenNames: string[];
    ticketType: TicketType;
  }) {
    try {
      // TODO: Call API to create family and children
      // For now, just add to local state

      const newFamilyId = Math.max(...checkinFamilies.map(f => f.id), 0) + 1;
      const newChildren: CheckinChild[] = data.childrenNames.map((name, index) => {
        const childId = newFamilyId * 1000 + index;
        return {
          id: childId,
          name: `${name} ${data.familyName}`,
          ticket: data.ticketType,
          checkedIn: false,
        };
      });

      // Note: In real implementation, would create via API and get back IDs
      // For now, creating mock API family
      const mockApiFamily: ApiFamily = {
        id: `family-${newFamilyId}`,
        family_name: data.familyName,
        primary_contact_name: data.familyName,
        primary_contact_phone: '',
        primary_contact_email: '',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        children: newChildren.map((child, index) => ({
          id: `child-${newFamilyId}-${index}`,
          family: `family-${newFamilyId}`,
          first_name: data.childrenNames[index],
          last_name: data.familyName,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        })),
      };

      apiFamilies = [...apiFamilies, mockApiFamily].sort((a, b) =>
        (a.family_name || '').localeCompare(b.family_name || '')
      );

      showAddPanel = false;
      successMessage = `${data.familyName} family added with ${newChildren.length} ${
        newChildren.length === 1 ? 'child' : 'children'
      }!`;

      // Auto-expand the new family
      expandedFamilies.add(newFamilyId);
      expandedFamilies = new Set(expandedFamilies);
    } catch (err: any) {
      console.error('Add family failed:', err);
      error = err.message || 'Failed to add family';
    }
  }

  // Get family-level undo remaining time
  function getFamilyUndoSeconds(familyId: number): number | null {
    const familyActions = getFamilyUndoActions(familyId);
    const familyAction = familyActions.find((a) => a.childIds.length > 1);
    return familyAction ? getRemainingTime(familyAction.id) : null;
  }

  // Format session time for display
  function formatSessionTime(session: Session): string {
    const start = new Date(session.start_time);
    const startTime = start.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
    });

    if (session.end_time) {
      const end = new Date(session.end_time);
      const endTime = end.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
      });
      return `${startTime} - ${endTime}`;
    }

    return startTime;
  }
</script>

<svelte:head>
  <title>{$t('checkin.pageTitle')}</title>
</svelte:head>

<div class="min-h-screen bg-slate-100">
  <div class="max-w-4xl mx-auto p-5">
    <!-- Session Indicator -->
    {#if selectedSessionData}
      <SessionIndicator
        eventName={selectedSessionData.name}
        sessionName={selectedSessionData.name}
        sessionTime={formatSessionTime(selectedSessionData)}
        onChangeSession={() => {
          // Allow changing session - show session selector
          selectedSession = null;
        }}
        onAddFamily={() => {
          showAddPanel = true;
        }}
      />
    {/if}

    <!-- Session Selection (only show if no session selected or multiple sessions) -->
    {#if !selectedSession || sessions.length > 1}
      <div class="bg-white border-2 border-primary-500 rounded-lg p-4 mb-4">
        <label for="session-select" class="block font-semibold text-primary-900 mb-2 text-sm">
          {$t('checkin.selectSession')}
        </label>
        <select
          id="session-select"
          data-testid="session-select"
          bind:value={selectedSession}
          class="w-full px-3 py-2 border border-neutral-300 rounded bg-white text-sm"
          disabled={loading}
        >
          <option value={null}>{$t('checkin.selectSessionPlaceholder')}</option>
          {#each sessions as session}
            <option value={session.id}>{session.name}</option>
          {/each}
        </select>
      </div>
    {/if}

    <!-- Add Family Panel -->
    {#if showAddPanel}
      <AddFamilyPanel
        onAdd={handleAddFamily}
        onClose={() => {
          showAddPanel = false;
        }}
      />
    {/if}

    <!-- Alerts -->
    {#if error}
      <Alert type="error" dismissible ondismiss={() => (error = null)} class="mb-4">
        {error}
      </Alert>
    {/if}

    <!-- Header -->
    <div class="mb-5">
      <h1 class="text-3xl font-bold text-blue-900">{$t('checkin.title')}</h1>
    </div>

    <!-- Search Box -->
    <div class="mb-4">
      <div class="relative">
        <Icon name="search" size="sm" class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          bind:value={searchQuery}
          placeholder={$t('checkin.searchPlaceholder')}
          class="w-full pl-10 pr-10 py-3 border-2 border-blue-500 rounded-lg bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
          data-testid="search-input"
          onkeydown={(e) => {
            if (e.key === 'Enter') {
              searchFamilies();
            }
          }}
        />
        {#if searchQuery}
          <button
            onclick={() => {
              searchQuery = '';
              apiFamilies = [];
            }}
            class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
            aria-label="Clear search"
            data-testid="clear-search-button"
          >
            <Icon name="x" size="sm" />
          </button>
        {/if}
      </div>

      <div class="flex justify-end mt-2">
        <button
          data-testid="search-button"
          onclick={searchFamilies}
          class="px-4 py-2 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          disabled={loading || !searchQuery.trim()}
        >
          {loading ? $t('checkin.searching') : $t('checkin.searchButton')}
        </button>
      </div>
    </div>

    <!-- Stats Header -->
    {#if checkinFamilies.length > 0}
      <div class="mb-4 flex items-center justify-between text-sm">
        <span class="text-slate-600" data-testid="family-count-text">
          {visibleFamilies.length}{' '}
          {visibleFamilies.length === 1 ? 'family' : 'families'}
          {searchQuery && ' matching search'}
        </span>
      </div>
    {/if}

    <!-- Loading State -->
    {#if loading && apiFamilies.length === 0}
      <EmptyState type="loading" title={$t('checkin.searching')} />
    {:else if visibleFamilies.length === 0 && searchQuery}
      <!-- No results -->
      <div class="text-center py-12 bg-white rounded-lg border-2 border-dashed border-slate-300">
        <p class="text-slate-500 mb-2">
          {$t('checkin.noFamiliesFound', { values: { query: searchQuery } })}
        </p>
        <p class="text-sm text-slate-400 mb-4">Try a different search term</p>
        <button
          onclick={() => {
            showAddPanel = true;
          }}
          class="px-4 py-2 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors"
        >
          {$t('checkin.addNewFamily')}
        </button>
      </div>
    {:else if visibleFamilies.length === 0 && !searchQuery}
      <!-- Empty state -->
      <EmptyState
        type="empty"
        title={$t('checkin.getStarted')}
        description={$t('checkin.searchForFamily')}
      >
        {#snippet icon()}
          <Icon name="search" size="xl" />
        {/snippet}
      </EmptyState>
    {:else}
      <!-- Family Cards -->
      <div class="space-y-3">
        {#each visibleFamilies as family (family.id)}
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
            familyUndoSeconds={getFamilyUndoSeconds(family.id)}
          />
        {/each}
      </div>
    {/if}
  </div>
</div>

<!-- Success Toast -->
{#if successMessage}
  <SuccessToast
    message={successMessage}
    onClose={() => {
      successMessage = null;
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

  .chevron {
    display: inline-block;
    transition: transform 0.2s ease;
  }

  .chevron.expanded {
    transform: rotate(0deg);
  }
</style>
