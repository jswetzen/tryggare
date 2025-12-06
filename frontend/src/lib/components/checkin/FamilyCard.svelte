<script lang="ts">
  /**
   * FamilyCard Component
   *
   * Displays a family with expandable child list and check-in functionality.
   * Supports:
   * - Individual child check-in with undo
   * - Family-level check-in with undo
   * - Ticket assignment for children without tickets
   * - Countdown timers for undo actions
   */
  import type { Family, TicketType } from '$lib/checkin/types';
  import ChildCheckInButton from './ChildCheckInButton.svelte';
  import { _ } from 'svelte-i18n';

  import { undoActionsWithTick } from '$lib/checkin/stores/undoTimer';

  let {
    family,
    expanded,
    onToggle,
    onCheckInChild,
    onCheckInFamily,
    onUndoChild,
    onUndoFamily,
    onAssignTicket,
    expandedChildId,
    onToggleChildExpansion,
    childRemainingTimes,
    familyUndoSeconds
  }: {
    family: Family;
    expanded: boolean;
    onToggle: () => void;
    onCheckInChild: (childId: string) => void;
    onCheckInFamily: () => void;
    onUndoChild: (childId: string) => void;
    onUndoFamily: () => void;
    onAssignTicket: (childId: string, ticketType: TicketType) => void;
    expandedChildId: string | null;
    onToggleChildExpansion: (childId: string | null) => void;
    childRemainingTimes: Map<string, number | null>;
    familyUndoSeconds: number | null;
  } = $props();

  // Subscribe to tick store for reactive countdown
  // Subscribe to undo timer store for reactivity
  // undoActionsWithTick returns { actions: UndoAction[], tick: number }
  let undoActionsData = $derived($undoActionsWithTick);
  let undoActions = $derived(undoActionsData.actions);

  const totalChildren = $derived(family.children.length);
  const checkedInCount = $derived(family.children.filter((c) => c.checkedIn).length);
  const canCheckInCount = $derived(family.children.filter((c) => !c.checkedIn && c.ticket !== 'none').length);
  const allCheckedIn = $derived(checkedInCount === totalChildren);
  const hasNoTicketChildren = $derived(family.children.some((c) => c.ticket === 'none'));

  // Helper to get ticket type display
  function getTicketDisplay(ticketType: string): string {
    switch (ticketType) {
      case 'event':
        return `🟢 ${$_('checkin.ticketEvent')}`;
      case 'session':
        return `🔵 ${$_('checkin.ticketSession')}`;
      case 'none':
        return `🔴 ${$_('checkin.ticketNone')}`;
      default:
        return '';
    }
  }
</script>

<div
  class="bg-white border border-slate-300 rounded-lg overflow-hidden mb-3 hover:shadow-md transition-shadow"
  data-testid={`family-card-${family.id}`}
>
  <!-- Family Header -->
  <div class="bg-slate-50 p-3 flex items-center justify-between gap-3">
    <button
      on:click={onToggle}
      class="flex items-center gap-2 flex-1 min-w-0 text-left hover:bg-slate-100 rounded px-2 py-1 -mx-2 -my-1 transition-colors"
      aria-label={`${expanded ? 'Collapse' : 'Expand'} ${family.name} family`}
      data-testid={`family-toggle-button-${family.id}`}
    >
      <div class="text-slate-600 flex-shrink-0">
        <span class="chevron" class:expanded>
          {expanded ? '▼' : '▶'}
        </span>
      </div>
      <div class="flex-1 min-w-0">
        <h3 class="font-bold text-blue-900 text-lg truncate">
          {family.name} Family
        </h3>
        <p class="text-sm text-slate-600">
          {totalChildren} {totalChildren === 1 ? $_('checkin.child') : $_('checkin.children')} •
          {checkedInCount} checked in
        </p>
      </div>
    </button>

    <!-- Family Action Button -->
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div class="flex-shrink-0" on:click|stopPropagation={() => {}}>
      {#if familyUndoSeconds !== null}
        <!-- Undo Family button during grace period -->
        <button
          on:click={onUndoFamily}
          class="px-4 py-2 bg-amber-600 text-white font-semibold rounded-lg hover:bg-amber-700 transition-colors text-sm whitespace-nowrap"
          aria-label={`Undo family check-in, ${familyUndoSeconds} seconds remaining`}
          data-testid={`family-undo-button-${family.id}`}
        >
          {$_('checkin.undoSeconds', { values: { seconds: familyUndoSeconds } })}
        </button>
      {:else if !allCheckedIn && canCheckInCount > 0 && !hasNoTicketChildren}
        <!-- Check In Family button -->
        <button
          type="button"
          on:click={onCheckInFamily}
          class="px-4 py-2 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors text-sm whitespace-nowrap"
          aria-label={`Check in ${canCheckInCount} children from ${family.name} family`}
          data-testid={`family-check-in-button-${family.id}`}
        >
          {$_('checkin.checkInCount', { values: { count: canCheckInCount } })}
        </button>
      {:else if allCheckedIn}
        <!-- All checked in -->
        <span class="px-4 py-2 bg-slate-200 text-slate-600 font-semibold rounded-lg text-sm whitespace-nowrap">
          {$_('checkin.alreadyCheckedIn')}
        </span>
      {/if}
    </div>
  </div>

  <!-- Children List (when expanded) -->
  {#if expanded}
    <div class="p-3 space-y-2">
      {#each family.children as child (child.id)}
        {@const isExpanded = expandedChildId === child.id}
        {@const childRemainingSeconds = childRemainingTimes.get(child.id) ?? null}

        <div
          class="flex flex-col gap-2 p-2 bg-slate-50 rounded border border-slate-200"
          data-testid={`child-row-${child.id}`}
        >
          <div class="flex items-center justify-between gap-3">
            <div class="flex-1 min-w-0">
              <div class="font-medium text-slate-700">{child.name}</div>
              <div class="text-xs text-slate-500 mt-0.5">
                {getTicketDisplay(child.ticket)}
                {#if child.checkedIn && child.checkInTime}
                  • {$_('checkin.checkedInAt', { values: { time: child.checkInTime } })}
                {/if}
              </div>
            </div>

            <ChildCheckInButton
              {child}
              onCheckIn={() => onCheckInChild(child.id)}
              onUndo={() => onUndoChild(child.id)}
              onNoTicketClick={() => onToggleChildExpansion(isExpanded ? null : child.id)}
              remainingSeconds={childRemainingSeconds}
              expanded={isExpanded}
            />
          </div>

          <!-- Ticket assignment expansion (for "No Ticket" children) -->
          {#if isExpanded && child.ticket === 'none'}
            <div class="w-full bg-yellow-50 border border-yellow-200 rounded p-3 animate-expand">
              <p class="text-sm text-slate-700 mb-2 font-medium">
                {$_('checkin.checkIn')} {child.name} with:
              </p>
              <div class="flex gap-2">
                <button
                  on:click={() => onAssignTicket(child.id, 'session')}
                  class="flex-1 px-3 py-2 bg-blue-500 text-white text-sm font-semibold rounded hover:bg-blue-600 transition-colors"
                  data-testid={`ticket-assign-session-${child.id}`}
                >
                  {$_('checkin.ticketSession')}
                </button>
                <button
                  on:click={() => onAssignTicket(child.id, 'event')}
                  class="flex-1 px-3 py-2 bg-green-600 text-white text-sm font-semibold rounded hover:bg-green-700 transition-colors"
                  data-testid={`ticket-assign-event-${child.id}`}
                >
                  {$_('checkin.ticketEvent')}
                </button>
              </div>
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
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

  .animate-expand {
    animation: expand 0.2s ease-out;
  }

  .chevron {
    display: inline-block;
    transition: transform 0.2s ease;
  }
</style>
