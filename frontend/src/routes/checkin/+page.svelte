<script lang="ts">
  import { onDestroy } from 'svelte';
  import type { Family, Child, TicketType } from '$lib/checkin/types';
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

  // ============================================================================
  // MOCK DATA
  // ============================================================================

  const MOCK_FAMILIES: Family[] = [
    {
      id: 1,
      name: 'Garcia',
      children: [
        { id: 1, name: 'Isabella Garcia', ticket: 'event', checkedIn: false },
        { id: 2, name: 'Lucas Garcia', ticket: 'none', checkedIn: false },
      ],
    },
    {
      id: 2,
      name: 'Johnson',
      children: [
        { id: 3, name: 'Sophia Johnson', ticket: 'session', checkedIn: false },
      ],
    },
    {
      id: 3,
      name: 'Smith',
      children: [
        { id: 4, name: 'Emma Smith', ticket: 'event', checkedIn: false },
        { id: 5, name: 'Oliver Smith', ticket: 'event', checkedIn: false },
      ],
    },
    {
      id: 4,
      name: 'Anderson',
      children: [
        { id: 6, name: 'Liam Anderson', ticket: 'event', checkedIn: false },
        { id: 7, name: 'Mia Anderson', ticket: 'event', checkedIn: false },
        { id: 8, name: 'Noah Anderson', ticket: 'session', checkedIn: false },
      ],
    },
  ];

  // ============================================================================
  // STATE MANAGEMENT
  // ============================================================================

  let families = $state<Family[]>(MOCK_FAMILIES);
  let searchQuery = $state('');
  let expandedFamilies = $state(new Set<number>());
  let expandedChildId = $state<number | null>(null);
  let showAddPanel = $state(false);
  let successToast = $state<string | null>(null);
  let nextFamilyId = $state(5);
  let nextChildId = $state(10);

  // Subscribe to undo timer store for reactivity
  // The $ prefix makes this reactive to store updates
  // undoActionsWithTick returns { actions: UndoAction[], tick: number }
  let undoActionsData = $derived($undoActionsWithTick);
  let undoActions = $derived(undoActionsData.actions);

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
    const newExpanded = new Set<number>();

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
  });

  // ============================================================================
  // EVENT HANDLERS
  // ============================================================================

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
  function checkInChild(familyId: number, childId: number) {
    const actionId = createUndoAction(familyId, [childId]);
    const checkInTime = getCurrentTime();

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
          };
        }),
      };
    });

    const family = families.find((f) => f.id === familyId);
    const child = family?.children.find((c) => c.id === childId);
    if (child) {
      successToast = `${child.name} checked in!`;
    }

    // Close expansion if open
    expandedChildId = null;
  }

  // Check in entire family
  function checkInFamily(familyId: number) {
    const family = families.find((f) => f.id === familyId);
    if (!family) return;

    const childIdsToCheckIn = family.children
      .filter((c) => !c.checkedIn && c.ticket !== 'none')
      .map((c) => c.id);

    if (childIdsToCheckIn.length === 0) return;

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
          };
        }),
      };
    });

    successToast = `${family.name} family checked in (${childIdsToCheckIn.length} ${
      childIdsToCheckIn.length === 1 ? 'child' : 'children'
    })!`;
  }

  // Undo individual child check-in
  function undoChildCheckIn(familyId: number, childId: number) {
    const family = families.find((f) => f.id === familyId);
    const child = family?.children.find((c) => c.id === childId);

    if (child?.checkInActionId) {
      removeUndoAction(child.checkInActionId);

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
            };
          }),
        };
      });

      if (child) {
        successToast = `${child.name} check-in undone`;
      }
    }
  }

  // Undo family check-in
  function undoFamilyCheckIn(familyId: number) {
    const family = families.find((f) => f.id === familyId);
    if (!family) return;

    // Find all undo actions for this family
    const familyActions = getFamilyUndoActions(familyId);
    if (familyActions.length === 0) return;

    // Get the most recent family action (should have multiple children)
    const familyAction = familyActions.find((a) => a.childIds.length > 1);
    if (!familyAction) return;

    removeUndoAction(familyAction.id);

    // Undo all children affected by this action
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
            };
          }
          return c;
        }),
      };
    });

    successToast = `${family.name} check-in undone`;
  }

  // Assign ticket and check in child
  function assignTicketAndCheckIn(
    familyId: number,
    childId: number,
    ticketType: TicketType
  ) {
    // First update the ticket type
    families = families.map((fam) => {
      if (fam.id !== familyId) return fam;
      return {
        ...fam,
        children: fam.children.map((child) => {
          if (child.id !== childId) return child;
          return { ...child, ticket: ticketType };
        }),
      };
    });

    // Then check in the child
    setTimeout(() => checkInChild(familyId, childId), 0);
  }

  // Add new family
  function handleAddFamily(data: {
    familyName: string;
    childrenNames: string[];
    ticketType: TicketType;
  }) {
    const newFamilyId = nextFamilyId;
    let currentChildId = nextChildId;

    const newChildren: Child[] = data.childrenNames.map((name) => ({
      id: currentChildId++,
      name: `${name} ${data.familyName}`,
      ticket: data.ticketType,
      checkedIn: false,
    }));

    const newFamily: Family = {
      id: newFamilyId,
      name: data.familyName,
      children: newChildren,
    };

    families = [...families, newFamily].sort((a, b) => a.name.localeCompare(b.name));
    nextFamilyId = newFamilyId + 1;
    nextChildId = currentChildId;
    showAddPanel = false;
    successToast = `${data.familyName} family added with ${newChildren.length} ${
      newChildren.length === 1 ? 'child' : 'children'
    }!`;

    // Auto-expand the new family
    expandedFamilies.add(newFamilyId);
    expandedFamilies = new Set(expandedFamilies);
  }
</script>

<svelte:head>
  <title>Check-In Station</title>
</svelte:head>

<div class="min-h-screen bg-slate-100">
  <div class="max-w-4xl mx-auto p-5">
    <!-- Session Indicator -->
    <SessionIndicator
      eventName="Summer Conference 2025"
      sessionName="Morning Care"
      sessionTime="8:00 AM - 12:00 PM"
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
      <h1 class="text-3xl font-bold text-blue-900">Check-In Station</h1>
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
          placeholder="Search by family or child name..."
          class="w-full pl-10 pr-10 py-3 border-2 border-blue-500 rounded-lg bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
          data-testid="search-input"
        />
        {#if searchQuery}
          <button
            onclick={() => (searchQuery = '')}
            class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
            aria-label="Clear search"
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
              ? `No families found matching "${searchQuery}"`
              : 'No families to check in'}
          </p>
          {#if searchQuery}
            <p class="text-sm text-slate-400">Try a different search term</p>
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
