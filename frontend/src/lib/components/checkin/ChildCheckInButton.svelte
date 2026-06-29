<script lang="ts">
  /**
   * ChildCheckInButton Component
   *
   * Displays different button states based on child's check-in status and ticket type:
   * - Check In (green) - for children with valid tickets who aren't checked in
   * - Undo (Xs) (orange) - for recently checked-in children during grace period
   * - Checked In (gray, disabled) - for checked-in children after grace period
   * - No Ticket (red) - for children without tickets, expands to show ticket assignment
   */
  import { _ } from 'svelte-i18n';
  import type { Child, TicketType } from '$lib/checkin/types';

  let {
    child,
    onCheckIn = undefined,
    onUndo = undefined,
    onNoTicketClick = undefined,
    remainingSeconds,
    expanded = false
  }: {
    child: Child;
    onCheckIn?: (() => void) | undefined;
    onUndo?: (() => void) | undefined;
    onNoTicketClick?: (() => void) | undefined;
    remainingSeconds: number | null;
    expanded?: boolean;
  } = $props();
</script>

{#if child.checkedIn && remainingSeconds !== null}
  <!-- Checked in with active undo timer -->
  <button
    on:click={() => onUndo?.()}
    class="px-3 py-1.5 bg-warning-600 text-white text-sm font-semibold rounded-button hover:bg-warning-700 transition-colors min-w-[100px]"
    aria-label={`Undo check-in for ${child.name}, ${remainingSeconds} seconds remaining`}
    data-testid={`child-undo-button-${child.id}`}
  >
    {$_('checkin.undoSeconds', { values: { seconds: remainingSeconds } })}
  </button>
{:else if child.checkedIn}
  <!-- Checked in, undo expired -->
  <button
    disabled
    title={`Checked in at ${child.checkInTime}`}
    class="px-3 py-1.5 bg-neutral-400 text-white text-sm font-semibold rounded-button cursor-not-allowed min-w-[100px]"
  >
    {$_('checkin.alreadyCheckedIn')}
  </button>
{:else if child.ticket === 'none'}
  <!-- No ticket - show button only (expansion handled by parent) -->
  <button
    on:click={() => onNoTicketClick?.()}
    class="px-3 py-1.5 bg-danger-100 text-danger-700 text-sm font-semibold rounded-button border border-danger-300 hover:bg-danger-200 transition-colors min-w-[100px]"
    aria-label={$_('checkin.noTicketClickToAssign')}
    data-testid={`child-expand-button-${child.id}`}
  >
    {$_('checkin.ticketNone')} {expanded ? '▲' : '▼'}
  </button>
{:else}
  <!-- Has valid ticket, ready to check in -->
  <button
    on:click={() => onCheckIn?.()}
    class="px-3 py-1.5 bg-success-600 text-white text-sm font-semibold rounded-button hover:bg-success-700 transition-colors min-w-[100px]"
    aria-label={`Check in ${child.name}`}
    data-testid={`child-check-in-button-${child.id}`}
  >
    {$_('checkin.checkIn')}
  </button>
{/if}
