import { ChevronDown, ChevronRight } from 'lucide-react';
import type { Family, TicketType } from '../types';
import { ChildCheckInButton } from './ChildCheckInButton';

interface FamilyCardProps {
  family: Family;
  expanded: boolean;
  onToggle: () => void;
  onCheckInChild: (childId: number) => void;
  onCheckInFamily: () => void;
  onUndoChild: (childId: number) => void;
  onUndoFamily: () => void;
  onAssignTicket: (childId: number, ticketType: TicketType) => void;
  expandedChildId: number | null;
  onToggleChildExpansion: (childId: number | null) => void;
  getRemainingTime: (actionId: string) => number | null;
  familyUndoSeconds: number | null;
}

/**
 * FamilyCard component
 *
 * Displays a family with expandable child list and check-in functionality.
 * Supports:
 * - Individual child check-in with undo
 * - Family-level check-in with undo
 * - Ticket assignment for children without tickets
 * - Countdown timers for undo actions
 */
export function FamilyCard({
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
  getRemainingTime,
  familyUndoSeconds,
}: FamilyCardProps) {
  const totalChildren = family.children.length;
  const checkedInCount = family.children.filter((c) => c.checkedIn).length;
  const canCheckInCount = family.children.filter(
    (c) => !c.checkedIn && c.ticket !== 'none'
  ).length;
  const allCheckedIn = checkedInCount === totalChildren;
  const hasNoTicketChildren = family.children.some((c) => c.ticket === 'none');

  // Helper to get ticket type display
  const getTicketDisplay = (ticketType: string) => {
    switch (ticketType) {
      case 'event':
        return '🟢 Event Pass';
      case 'session':
        return '🔵 Session Ticket';
      case 'none':
        return '🔴 No Ticket';
      default:
        return '';
    }
  };

  return (
    <div className="bg-white border border-slate-300 rounded-lg overflow-hidden mb-3 hover:shadow-md transition-shadow">
      {/* Family Header */}
      <div className="bg-slate-50 p-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <button
            onClick={onToggle}
            className="text-slate-600 hover:text-slate-900 transition-colors flex-shrink-0"
            aria-label={`Toggle ${family.name} family`}
          >
            {expanded ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
          </button>
          <div className="flex-1 min-w-0">
            <h3 className="font-bold text-blue-900 text-lg truncate">
              {family.name} Family
            </h3>
            <p className="text-sm text-slate-600">
              {totalChildren} {totalChildren === 1 ? 'child' : 'children'} •{' '}
              {checkedInCount} checked in
            </p>
          </div>
        </div>

        {/* Family Action Button */}
        <div className="flex-shrink-0">
          {familyUndoSeconds !== null ? (
            // Undo Family button during grace period
            <button
              onClick={onUndoFamily}
              className="px-4 py-2 bg-orange-500 text-white font-semibold rounded-lg hover:bg-orange-600 transition-colors text-sm whitespace-nowrap"
              aria-label={`Undo family check-in, ${familyUndoSeconds} seconds remaining`}
            >
              Undo Family ({familyUndoSeconds}s)
            </button>
          ) : !allCheckedIn && canCheckInCount > 0 && !hasNoTicketChildren ? (
            // Check In Family button
            <button
              type="button"
              onClick={(e) => {
                console.log('=== CHECK IN FAMILY BUTTON CLICKED ===');
                console.log('Family:', family.name);
                console.log('Event:', e);
                console.log('onCheckInFamily type:', typeof onCheckInFamily);
                console.log('Calling onCheckInFamily...');
                try {
                  onCheckInFamily();
                  console.log('onCheckInFamily called successfully');
                } catch (error) {
                  console.error('Error calling onCheckInFamily:', error);
                  alert('Error: ' + error);
                }
              }}
              className="px-4 py-2 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors text-sm whitespace-nowrap"
              aria-label={`Check in ${canCheckInCount} children from ${family.name} family`}
            >
              Check In Family ({canCheckInCount})
            </button>
          ) : allCheckedIn ? (
            // All checked in
            <span className="px-4 py-2 bg-slate-200 text-slate-600 font-semibold rounded-lg text-sm whitespace-nowrap">
              All Checked In
            </span>
          ) : null}
        </div>
      </div>

      {/* Children List (when expanded) */}
      {expanded && (
        <div className="p-3 space-y-2">
          {family.children.map((child) => {
            const childUndoAction = child.checkInActionId
              ? getRemainingTime(child.checkInActionId)
              : null;

            const isExpanded = expandedChildId === child.id;

            return (
              <div
                key={child.id}
                className="flex flex-col gap-2 p-2 bg-slate-50 rounded border border-slate-200"
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-slate-700">{child.name}</div>
                    <div className="text-xs text-slate-500 mt-0.5">
                      {getTicketDisplay(child.ticket)}
                      {child.checkedIn && child.checkInTime && (
                        <> • Checked in at {child.checkInTime}</>
                      )}
                    </div>
                  </div>

                  <ChildCheckInButton
                    child={child}
                    onCheckIn={() => onCheckInChild(child.id)}
                    onUndo={() => onUndoChild(child.id)}
                    onNoTicketClick={() =>
                      onToggleChildExpansion(
                        isExpanded ? null : child.id
                      )
                    }
                    onAssignTicket={(ticketType) =>
                      onAssignTicket(child.id, ticketType)
                    }
                    remainingSeconds={childUndoAction}
                    expanded={isExpanded}
                  />
                </div>

                {/* Ticket assignment expansion (for "No Ticket" children) */}
                {isExpanded && child.ticket === 'none' && (
                  <div className="w-full bg-yellow-50 border border-yellow-200 rounded p-3 animate-expand">
                    <p className="text-sm text-slate-700 mb-2 font-medium">
                      Check in {child.name} with:
                    </p>
                    <div className="flex gap-2">
                      <button
                        onClick={() => onAssignTicket(child.id, 'session')}
                        className="flex-1 px-3 py-2 bg-blue-500 text-white text-sm font-semibold rounded hover:bg-blue-600 transition-colors"
                      >
                        Session Only
                      </button>
                      <button
                        onClick={() => onAssignTicket(child.id, 'event')}
                        className="flex-1 px-3 py-2 bg-green-600 text-white text-sm font-semibold rounded hover:bg-green-700 transition-colors"
                      >
                        Full Event Pass
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
