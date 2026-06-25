<script lang="ts">
  /**
   * ParentCheckInButton Component
   *
   * Displays different button states based on parent's check-in status and ticket type:
   * - Check In (green) - for parents with valid tickets who aren't checked in
   * - Undo (Xs) (orange) - for recently checked-in parents during grace period
   * - Checked In (gray, disabled) - for checked-in parents after grace period
   * - No Ticket (red) - for parents without tickets, expands to show ticket assignment
   */
  import { _ } from 'svelte-i18n';
  import type { Parent } from '$lib/checkin/types';

  let {
    parent,
    onCheckIn = undefined,
    onUndo = undefined,
    onNoTicketClick = undefined,
    remainingSeconds,
    expanded = false
  }: {
    parent: Parent;
    onCheckIn?: (() => void) | undefined;
    onUndo?: (() => void) | undefined;
    onNoTicketClick?: (() => void) | undefined;
    remainingSeconds: number | null;
    expanded?: boolean;
  } = $props();
</script>

{#if parent.checkedIn && remainingSeconds !== null}
  <!-- Checked in with active undo timer -->
  <button
    on:click={() => onUndo?.()}
    class="px-3 py-1.5 bg-amber-600 text-white text-sm font-semibold rounded hover:bg-amber-700 transition-colors min-w-[100px]"
    aria-label={`Undo check-in for ${parent.name}, ${remainingSeconds} seconds remaining`}
    data-testid={`parent-undo-button-${parent.id}`}
  >
    {$_('checkin.undoSeconds', { values: { seconds: remainingSeconds } })}
  </button>
{:else if parent.checkedIn}
  <!-- Checked in, undo expired -->
  <button
    disabled
    title={`Checked in at ${parent.checkInTime}`}
    class="px-3 py-1.5 bg-slate-400 text-white text-sm font-semibold rounded cursor-not-allowed min-w-[100px]"
  >
    {$_('checkin.alreadyCheckedIn')}
  </button>
{:else if parent.ticket === 'none'}
  <!-- No ticket - show button only (expansion handled by parent) -->
  <button
    on:click={() => onNoTicketClick?.()}
    class="px-3 py-1.5 bg-red-100 text-red-700 text-sm font-semibold rounded border border-red-300 hover:bg-red-200 transition-colors min-w-[100px]"
    aria-label={$_('checkin.noTicketClickToAssign')}
    data-testid={`parent-expand-button-${parent.id}`}
  >
    {$_('checkin.ticketNone')} {expanded ? '▲' : '▼'}
  </button>
{:else}
  <!-- Has valid ticket, ready to check in -->
  <button
    on:click={() => onCheckIn?.()}
    class="px-3 py-1.5 bg-green-600 text-white text-sm font-semibold rounded hover:bg-green-700 transition-colors min-w-[100px]"
    aria-label={`Check in ${parent.name}`}
    data-testid={`parent-check-in-button-${parent.id}`}
  >
    {$_('checkin.checkIn')}
  </button>
{/if}
