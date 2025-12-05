import type { Child, TicketType } from '../types';

interface ChildCheckInButtonProps {
  child: Child;
  onCheckIn?: () => void;
  onUndo?: () => void;
  onNoTicketClick?: () => void;
  onAssignTicket?: (ticketType: TicketType) => void;
  remainingSeconds: number | null;
  expanded?: boolean;
}

/**
 * ChildCheckInButton component
 *
 * Displays different button states based on child's check-in status and ticket type:
 * - Check In (green) - for children with valid tickets who aren't checked in
 * - Undo (Xs) (orange) - for recently checked-in children during grace period
 * - Checked In (gray, disabled) - for checked-in children after grace period
 * - No Ticket (red) - for children without tickets, expands to show ticket assignment
 */
export function ChildCheckInButton({
  child,
  onCheckIn,
  onUndo,
  onNoTicketClick,
  remainingSeconds,
  expanded = false,
}: ChildCheckInButtonProps) {
  // Checked in with active undo timer
  if (child.checkedIn && remainingSeconds !== null) {
    return (
      <button
        onClick={() => onUndo?.()}
        className="px-3 py-1.5 bg-orange-500 text-white text-sm font-semibold rounded hover:bg-orange-600 transition-colors min-w-[100px]"
        aria-label={`Undo check-in for ${child.name}, ${remainingSeconds} seconds remaining`}
        data-testid={`child-undo-button-${child.id}`}
      >
        Undo ({remainingSeconds}s)
      </button>
    );
  }

  // Checked in, undo expired
  if (child.checkedIn) {
    return (
      <button
        disabled
        title={`Checked in at ${child.checkInTime}`}
        className="px-3 py-1.5 bg-slate-400 text-white text-sm font-semibold rounded cursor-not-allowed min-w-[100px]"
      >
        Checked In
      </button>
    );
  }

  // No ticket - show button only (expansion handled by parent)
  if (child.ticket === 'none') {
    return (
      <button
        onClick={() => onNoTicketClick?.()}
        className="px-3 py-1.5 bg-red-100 text-red-700 text-sm font-semibold rounded border border-red-300 hover:bg-red-200 transition-colors min-w-[100px]"
        aria-label="No ticket - click to assign"
        data-testid={`child-expand-button-${child.id}`}
      >
        No Ticket {expanded ? '▲' : '▼'}
      </button>
    );
  }

  // Has valid ticket, ready to check in
  return (
    <button
      onClick={() => onCheckIn?.()}
      className="px-3 py-1.5 bg-green-600 text-white text-sm font-semibold rounded hover:bg-green-700 transition-colors min-w-[100px]"
      aria-label={`Check in ${child.name}`}
      data-testid={`child-check-in-button-${child.id}`}
    >
      Check In
    </button>
  );
}
