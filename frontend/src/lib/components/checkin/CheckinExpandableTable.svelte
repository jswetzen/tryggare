<script lang="ts">
  /**
   * CheckinExpandableTable Component
   *
   * Expandable table/card layout for checkin page aligned with checkout page design.
   * Preserves ALL FamilyCard functionality:
   * - Individual child check-in with undo timers
   * - Family-level check-in with undo timers
   * - Ticket assignment for children with no tickets
   * - Supervised state toggle
   * - Check-in time display
   * - Ticket type badges
   *
   * Visual design matches checkout page:
   * - Mobile: Card layout with rounded borders
   * - Desktop: Table layout with sticky headers
   * - Slate-* color palette throughout
   * - Blue-600 action buttons
   */
  import { _ } from 'svelte-i18n';
  import type { Family, TicketType } from '$lib/checkin/types';
  import ChildCheckInButton from './ChildCheckInButton.svelte';
  import { undoActionsWithTick } from '$lib/checkin/stores/undoTimer';

  interface Props {
    families: Family[];
    onCheckInChild: (familyId: string, childId: string) => Promise<void>;
    onCheckInFamily: (familyId: string) => Promise<void>;
    onUndoChild: (familyId: string, childId: string) => Promise<void>;
    onUndoFamily: (familyId: string) => Promise<void>;
    onAssignTicket: (familyId: string, childId: string, ticketType: TicketType) => Promise<void>;
    getRemainingTime: (actionId: string) => number | null;
    supervisedState: Record<string, boolean>;
    expandedChildId: string | null;
    onToggleChildExpansion: (childId: string | null) => void;
    searchQuery?: string;
  }

  let {
    families,
    onCheckInChild,
    onCheckInFamily,
    onUndoChild,
    onUndoFamily,
    onAssignTicket,
    getRemainingTime,
    supervisedState = $bindable(),
    expandedChildId,
    onToggleChildExpansion,
    searchQuery = ''
  }: Props = $props();

  // Track which families are manually toggled by the user
  let manuallyExpanded = $state<Set<string>>(new Set());
  // Track families explicitly collapsed by the user (to override search auto-expand)
  let manuallyCollapsed = $state<Set<string>>(new Set());

  // Families that should be auto-expanded because a child's name matches the search query
  // (only when the family name itself does NOT match — if the family name matches, it's already shown without needing expansion)
  const searchAutoExpanded = $derived.by(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return new Set<string>();
    const result = new Set<string>();
    for (const family of families) {
      const familyNameMatches = family.name.toLowerCase().includes(query);
      const childMatches = family.children.some((child) =>
        child.name.toLowerCase().includes(query)
      );
      if (childMatches && !familyNameMatches) {
        result.add(family.id);
      }
    }
    return result;
  });

  // Combined expansion state: (manually expanded OR search-auto-expanded) AND NOT manually collapsed
  const expandedFamilies = $derived.by(() => {
    const result = new Set([...manuallyExpanded, ...searchAutoExpanded]);
    for (const id of manuallyCollapsed) {
      result.delete(id);
    }
    return result;
  });

  // Subscribe to undo timer store for reactivity
  let undoActionsData = $derived($undoActionsWithTick);

  function toggleFamily(familyId: string, event: MouseEvent | KeyboardEvent) {
    // Prevent expansion if clicking on a button or interactive element
    const target = event.target as HTMLElement;
    if (target.closest('button') || target.closest('select') || target.closest('input')) {
      return;
    }

    if (expandedFamilies.has(familyId)) {
      // Currently expanded — collapse it
      const newManual = new Set(manuallyExpanded);
      newManual.delete(familyId);
      manuallyExpanded = newManual;
      const newCollapsed = new Set(manuallyCollapsed);
      newCollapsed.add(familyId);
      manuallyCollapsed = newCollapsed;
    } else {
      // Currently collapsed — expand it
      const newManual = new Set(manuallyExpanded);
      newManual.add(familyId);
      manuallyExpanded = newManual;
      const newCollapsed = new Set(manuallyCollapsed);
      newCollapsed.delete(familyId);
      manuallyCollapsed = newCollapsed;
    }
  }

  function isExpanded(familyId: string): boolean {
    return expandedFamilies.has(familyId);
  }

  // Helper to get family-level undo actions
  function getFamilyUndoSeconds(family: Family): number | null {
    const _tick = undoActionsData.tick; // Force reactivity

    // Look through family's checked-in children for a multi-child action
    for (const child of family.children) {
      if (child.checkInActionId) {
        const remainingTime = getRemainingTime(child.checkInActionId);
        if (remainingTime !== null) {
          // Check if this is a family action (multiple children with same actionId)
          const childrenWithSameAction = family.children.filter(
            c => c.checkInActionId === child.checkInActionId
          );
          if (childrenWithSameAction.length > 1) {
            return remainingTime;
          }
        }
      }
    }
    return null;
  }

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

  // Family statistics
  function getTotalChildren(family: Family): number {
    return family.children.length;
  }

  function getCheckedInCount(family: Family): number {
    return family.children.filter(c => c.checkedIn).length;
  }

  function getCanCheckInCount(family: Family): number {
    return family.children.filter(c => !c.checkedIn && c.ticket !== 'none').length;
  }

  function isAllCheckedIn(family: Family): boolean {
    return getCheckedInCount(family) === getTotalChildren(family);
  }

  function hasNoTicketChildren(family: Family): boolean {
    return family.children.some(c => c.ticket === 'none');
  }
</script>

<!-- Mobile Layout (<768px) -->
<div class="md:hidden space-y-3">
  {#each families as family (family.id)}
    {@const expanded = isExpanded(family.id)}
    {@const totalChildren = getTotalChildren(family)}
    {@const checkedInCount = getCheckedInCount(family)}
    {@const canCheckInCount = getCanCheckInCount(family)}
    {@const allCheckedIn = isAllCheckedIn(family)}
    {@const noTicketChildren = hasNoTicketChildren(family)}
    {@const familyUndoSeconds = getFamilyUndoSeconds(family)}

    <div
      class="bg-white border-2 border-slate-300 rounded-lg overflow-hidden"
      class:opacity-60={allCheckedIn}
      class:bg-slate-50={allCheckedIn}
      data-testid={`family-card-${family.id}`}
    >
      <!-- Family Header - ENTIRE DIV CLICKABLE -->
      <div
        class="bg-slate-50 p-2.5 sm:p-3 cursor-pointer active:bg-slate-100"
        onclick={(e) => toggleFamily(family.id, e)}
        role="button"
        tabindex="0"
        onkeydown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            toggleFamily(family.id, e);
          }
        }}
        aria-label={`${expanded ? 'Collapse' : 'Expand'} ${family.name} family`}
        data-testid={`family-toggle-button-${family.id}`}
      >
        <div class="flex items-start justify-between gap-2">
          <!-- Left side: Chevron and family info -->
          <div class="flex items-start gap-2 flex-1 min-w-0">
            <!-- Chevron icon -->
            <div class="flex-shrink-0 pt-0.5">
              {#if expanded}
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M4 7l6 6 6-6"/>
                </svg>
              {:else}
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M7 4l6 6-6 6"/>
                </svg>
              {/if}
            </div>

            <!-- Family info -->
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <h3 class="font-bold text-blue-900 text-base sm:text-lg truncate">
                  {family.name}
                </h3>
                {#if allCheckedIn}
                  <span class="px-1.5 py-0.5 text-xs font-semibold bg-green-100 text-green-800 rounded whitespace-nowrap">
                    {$_('checkin.allCheckedIn')}
                  </span>
                {/if}
              </div>
              <p class="text-xs sm:text-sm text-slate-600 mt-0.5">
                {totalChildren} {totalChildren === 1 ? $_('checkin.child') : $_('checkin.children')} •
                {checkedInCount} checked in
              </p>
            </div>
          </div>

          <!-- Right side: Action button -->
          <div class="flex-shrink-0">
            {#if familyUndoSeconds !== null}
              <!-- Undo Family button during grace period -->
              <button
                type="button"
                onclick={() => onUndoFamily(family.id)}
                class="px-3 py-1.5 sm:px-4 sm:py-2 bg-amber-600 text-white font-semibold rounded-lg hover:bg-amber-700 transition-colors text-xs sm:text-sm whitespace-nowrap"
                aria-label={`Undo family check-in, ${familyUndoSeconds} seconds remaining`}
                data-testid={`family-undo-button-${family.id}`}
              >
                {$_('checkin.undoSeconds', { values: { seconds: familyUndoSeconds } })}
              </button>
            {:else if !allCheckedIn && canCheckInCount > 0 && !noTicketChildren}
              <!-- Check In Family button -->
              <button
                type="button"
                onclick={() => onCheckInFamily(family.id)}
                class="px-3 py-1.5 sm:px-4 sm:py-2 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors text-xs sm:text-sm whitespace-nowrap"
                aria-label={`Check in ${canCheckInCount} children from ${family.name} family`}
                data-testid={`family-check-in-button-${family.id}`}
              >
                {$_('checkin.checkInCount', { values: { count: canCheckInCount } })}
              </button>
            {:else if allCheckedIn}
              <!-- All checked in -->
              <span class="px-3 py-1.5 sm:px-4 sm:py-2 bg-slate-200 text-slate-600 font-semibold rounded-lg text-xs sm:text-sm whitespace-nowrap inline-block">
                {$_('checkin.alreadyCheckedIn')}
              </span>
            {/if}
          </div>
        </div>
      </div>

      <!-- Expanded children list -->
      {#if expanded}
        <div class="p-2 sm:p-3 space-y-2">
          {#each family.children as child (child.id)}
            {@const isChildExpanded = expandedChildId === child.id}
            {@const _tick = undoActionsData.tick}
            {@const childRemainingSeconds = child.checkInActionId && _tick >= 0 ? getRemainingTime(child.checkInActionId) : null}

            <div
              class="flex flex-col gap-2 p-2 bg-slate-50 rounded border border-slate-200"
              data-testid={`child-row-${child.id}`}
            >
              <div class="flex flex-col sm:flex-row sm:items-center gap-2">
                <!-- Child info -->
                <div class="flex-1 min-w-0">
                  <div class="font-medium text-slate-700 text-sm sm:text-base">{child.name}</div>
                  <div class="text-xs text-slate-500 mt-0.5">
                    {getTicketDisplay(child.ticket)}
                    {#if child.checkedIn && child.checkInTime}
                      • {$_('checkin.checkedInAt', { values: { time: child.checkInTime } })}
                    {/if}
                  </div>
                </div>

                <!-- Actions -->
                <div class="flex items-center gap-2 flex-wrap">
                  {#if !child.checkedIn && child.ticket !== 'none'}
                    <label class="flex items-center gap-1.5 text-xs cursor-pointer whitespace-nowrap">
                      <input
                        type="checkbox"
                        id="supervised-{child.id}"
                        bind:checked={supervisedState[child.id]}
                        class="w-4 h-4 text-blue-600 bg-white border-slate-300 rounded focus:ring-blue-500 focus:ring-2"
                        data-testid={`supervised-checkbox-${child.id}`}
                      />
                      <span class="text-slate-600">{$_('checkin.guardianPresent')}</span>
                    </label>
                  {/if}

                  <ChildCheckInButton
                    {child}
                    onCheckIn={() => onCheckInChild(family.id, child.id)}
                    onUndo={() => onUndoChild(family.id, child.id)}
                    onNoTicketClick={() => onToggleChildExpansion(isChildExpanded ? null : child.id)}
                    remainingSeconds={childRemainingSeconds}
                    expanded={isChildExpanded}
                  />
                </div>
              </div>

              <!-- Ticket assignment expansion (for "No Ticket" children) -->
              {#if isChildExpanded && child.ticket === 'none'}
                <div class="w-full bg-yellow-50 border border-yellow-200 rounded p-3 animate-expand">
                  <p class="text-sm text-slate-700 mb-2 font-medium">
                    {$_('checkin.checkIn')} {child.name} with:
                  </p>
                  <div class="flex gap-2">
                    <button
                      onclick={() => onAssignTicket(family.id, child.id, 'session')}
                      class="flex-1 px-3 py-2 bg-blue-500 text-white text-sm font-semibold rounded hover:bg-blue-600 transition-colors"
                      data-testid={`ticket-assign-session-${child.id}`}
                    >
                      {$_('checkin.ticketSession')}
                    </button>
                    <button
                      onclick={() => onAssignTicket(family.id, child.id, 'event')}
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
  {/each}
</div>

<!-- Desktop Layout (≥768px) -->
<div class="hidden md:block bg-white rounded-lg border-2 border-slate-300 overflow-hidden">
  <table class="w-full">
    <!-- Sticky header -->
    <thead class="bg-slate-50 border-b-2 border-slate-300 sticky top-0 z-[5]">
      <tr>
        <th class="px-4 py-3 text-left text-sm font-medium text-slate-700">
          Family
        </th>
        <th class="px-4 py-3 text-left text-sm font-medium text-slate-700">
          Status
        </th>
        <th class="px-4 py-3 text-right text-sm font-medium text-slate-700">
          Actions
        </th>
      </tr>
    </thead>

    <tbody>
      {#each families as family (family.id)}
        {@const expanded = isExpanded(family.id)}
        {@const totalChildren = getTotalChildren(family)}
        {@const checkedInCount = getCheckedInCount(family)}
        {@const canCheckInCount = getCanCheckInCount(family)}
        {@const allCheckedIn = isAllCheckedIn(family)}
        {@const noTicketChildren = hasNoTicketChildren(family)}
        {@const familyUndoSeconds = getFamilyUndoSeconds(family)}

        <!-- Family header row -->
        <tr
          class="border-b border-slate-200 hover:bg-slate-50 cursor-pointer"
          class:opacity-60={allCheckedIn}
          class:bg-slate-50={allCheckedIn}
          onclick={(e) => toggleFamily(family.id, e)}
          role="button"
          tabindex="0"
          onkeydown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              toggleFamily(family.id, e);
            }
          }}
          data-testid={`family-card-${family.id}`}
        >
          <td class="px-4 py-3">
            <div class="flex items-center gap-2">
              <!-- Chevron -->
              <div class="flex-shrink-0">
                {#if expanded}
                  <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M3 6l6 6 6-6"/>
                  </svg>
                {:else}
                  <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M6 3l6 6-6 6"/>
                  </svg>
                {/if}
              </div>
              <span class="font-bold text-blue-900">{family.name}</span>
              {#if allCheckedIn}
                <span class="px-1.5 py-0.5 text-xs font-semibold bg-green-100 text-green-800 rounded">
                  {$_('checkin.allCheckedIn')}
                </span>
              {/if}
            </div>
          </td>
          <td class="px-4 py-3 text-sm text-slate-600">
            {totalChildren} {totalChildren === 1 ? $_('checkin.child') : $_('checkin.children')} •
            {checkedInCount} checked in
          </td>
          <td class="px-4 py-3 text-right">
            <!-- svelte-ignore a11y-click-events-have-key-events -->
            <!-- svelte-ignore a11y-no-static-element-interactions -->
            <div onclick={(e) => e.stopPropagation()}>
              {#if familyUndoSeconds !== null}
                <button
                  onclick={() => onUndoFamily(family.id)}
                  class="px-4 py-1.5 bg-amber-600 text-white text-sm font-medium rounded hover:bg-amber-700 transition-colors"
                  data-testid={`family-undo-button-${family.id}`}
                >
                  {$_('checkin.undoSeconds', { values: { seconds: familyUndoSeconds } })}
                </button>
              {:else if !allCheckedIn && canCheckInCount > 0 && !noTicketChildren}
                <button
                  type="button"
                  onclick={() => onCheckInFamily(family.id)}
                  class="px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded hover:bg-blue-700 transition-colors"
                  data-testid={`family-check-in-button-${family.id}`}
                >
                  {$_('checkin.checkInCount', { values: { count: canCheckInCount } })}
                </button>
              {:else if allCheckedIn}
                <span class="px-4 py-1.5 bg-slate-200 text-slate-600 text-sm font-medium rounded inline-block">
                  {$_('checkin.alreadyCheckedIn')}
                </span>
              {/if}
            </div>
          </td>
        </tr>

        <!-- Children rows (when expanded) -->
        {#if expanded}
          {#each family.children as child (child.id)}
            {@const isChildExpanded = expandedChildId === child.id}
            {@const _tick = undoActionsData.tick}
            {@const childRemainingSeconds = child.checkInActionId && _tick >= 0 ? getRemainingTime(child.checkInActionId) : null}

            <tr class="border-b border-slate-200 bg-slate-50" data-testid={`child-row-${child.id}`}>
              <td class="px-4 py-3 pl-12" colspan="2">
                <div class="flex items-center gap-3">
                  <div class="flex-1">
                    <div class="font-medium text-slate-700">{child.name}</div>
                    <div class="text-xs text-slate-500 mt-0.5">
                      {getTicketDisplay(child.ticket)}
                      {#if child.checkedIn && child.checkInTime}
                        • {$_('checkin.checkedInAt', { values: { time: child.checkInTime } })}
                      {/if}
                    </div>
                  </div>

                  {#if !child.checkedIn && child.ticket !== 'none'}
                    <label class="flex items-center gap-1.5 text-xs cursor-pointer">
                      <input
                        type="checkbox"
                        id="supervised-{child.id}"
                        bind:checked={supervisedState[child.id]}
                        class="w-4 h-4 text-blue-600 bg-white border-slate-300 rounded focus:ring-blue-500 focus:ring-2"
                        data-testid={`supervised-checkbox-${child.id}`}
                      />
                      <span class="text-slate-600">{$_('checkin.guardianPresent')}</span>
                    </label>
                  {/if}
                </div>

                <!-- Ticket assignment expansion (inline for desktop) -->
                {#if isChildExpanded && child.ticket === 'none'}
                  <div class="mt-2 bg-yellow-50 border border-yellow-200 rounded p-3 animate-expand">
                    <p class="text-sm text-slate-700 mb-2 font-medium">
                      {$_('checkin.checkIn')} {child.name} with:
                    </p>
                    <div class="flex gap-2">
                      <button
                        onclick={() => onAssignTicket(family.id, child.id, 'session')}
                        class="flex-1 px-3 py-2 bg-blue-500 text-white text-sm font-semibold rounded hover:bg-blue-600 transition-colors"
                        data-testid={`ticket-assign-session-${child.id}`}
                      >
                        {$_('checkin.ticketSession')}
                      </button>
                      <button
                        onclick={() => onAssignTicket(family.id, child.id, 'event')}
                        class="flex-1 px-3 py-2 bg-green-600 text-white text-sm font-semibold rounded hover:bg-green-700 transition-colors"
                        data-testid={`ticket-assign-event-${child.id}`}
                      >
                        {$_('checkin.ticketEvent')}
                      </button>
                    </div>
                  </div>
                {/if}
              </td>
              <td class="px-4 py-3">
                <div class="flex justify-end">
                  <ChildCheckInButton
                    {child}
                    onCheckIn={() => onCheckInChild(family.id, child.id)}
                    onUndo={() => onUndoChild(family.id, child.id)}
                    onNoTicketClick={() => onToggleChildExpansion(isChildExpanded ? null : child.id)}
                    remainingSeconds={childRemainingSeconds}
                    expanded={isChildExpanded}
                  />
                </div>
              </td>
            </tr>
          {/each}
        {/if}
      {/each}
    </tbody>
  </table>
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
</style>
