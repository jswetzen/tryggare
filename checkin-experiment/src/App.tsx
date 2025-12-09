import { useState, useMemo, useEffect } from 'react';
import { Search, X } from 'lucide-react';
import type { Family, Child, TicketType } from './types';
import { useUndoTimer } from './hooks/useUndoTimer';
import { getVisibleFamilies } from './utils/familyVisibility';
import { FamilyCard } from './components/FamilyCard';
import { AddFamilyPanel } from './components/AddFamilyPanel';

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
// SESSION INDICATOR COMPONENT
// ============================================================================

interface SessionIndicatorProps {
  eventName: string;
  sessionName: string;
  sessionTime: string;
  onChangeSession: () => void;
  onAddFamily: () => void;
}

function SessionIndicator({
  eventName,
  sessionName,
  sessionTime,
  onChangeSession,
  onAddFamily,
}: SessionIndicatorProps) {
  return (
    <div
      className="bg-slate-50 border border-slate-300 rounded px-3 py-2 mb-4 flex flex-wrap justify-between items-center gap-2 text-sm"
      data-testid="session-indicator"
    >
      <div className="text-slate-600">
        <span className="font-semibold text-blue-900">Event:</span> {eventName} •
        <span className="font-semibold text-blue-900 ml-1">Session:</span> {sessionName} ({sessionTime})
      </div>
      <div className="flex gap-2">
        <button
          onClick={onChangeSession}
          className="px-3 py-1.5 text-blue-600 font-semibold hover:underline"
          data-testid="change-session-button"
        >
          Change Session
        </button>
        <button
          onClick={onAddFamily}
          className="px-3 py-1.5 bg-blue-600 text-white font-semibold rounded hover:bg-blue-700 transition-colors"
          data-testid="add-family-button"
        >
          + Add Family
        </button>
      </div>
    </div>
  );
}

// ============================================================================
// SUCCESS TOAST COMPONENT
// ============================================================================

interface SuccessToastProps {
  message: string;
  onClose: () => void;
}

function SuccessToast({ message, onClose }: SuccessToastProps) {
  useEffect(() => {
    const timer = setTimeout(onClose, 3000);
    return () => clearTimeout(timer);
  }, [onClose]);

  return (
    <div
      className="fixed top-4 right-4 bg-green-600 text-white px-4 py-3 rounded-lg shadow-lg flex items-center gap-2 z-50 animate-slide-in"
      role="alert"
      aria-live="polite"
      data-testid="success-toast"
    >
      <span className="text-xl">✓</span>
      <span className="font-semibold">{message}</span>
    </div>
  );
}

// ============================================================================
// MAIN APP COMPONENT
// ============================================================================

export default function App() {
  const [families, setFamilies] = useState<Family[]>(MOCK_FAMILIES);
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedFamilies, setExpandedFamilies] = useState(new Set<number>());
  const [expandedChildId, setExpandedChildId] = useState<number | null>(null);
  const [showAddPanel, setShowAddPanel] = useState(false);
  const [successToast, setSuccessToast] = useState<string | null>(null);
  const [nextFamilyId, setNextFamilyId] = useState(5);
  const [nextChildId, setNextChildId] = useState(10);

  // Use undo timer hook
  const {
    undoActions,
    createUndoAction,
    removeUndoAction,
    getRemainingTime,
    getFamilyUndoActions,
  } = useUndoTimer();

  // Helper to get current time formatted
  const getCurrentTime = () => {
    return new Date().toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
    });
  };

  // Filter visible families based on search and visibility rules
  const visibleFamilies = useMemo(() => {
    const filtered = getVisibleFamilies(families, undoActions);

    if (!searchQuery) return filtered;

    const query = searchQuery.toLowerCase();
    return filtered.filter(
      (family) =>
        family.name.toLowerCase().includes(query) ||
        family.children.some((child) => child.name.toLowerCase().includes(query))
    );
  }, [families, undoActions, searchQuery]);

  // Auto-expand families when search matches child name (but not family name)
  useEffect(() => {
    if (!searchQuery) {
      // Don't collapse families when clearing search (less disruptive)
      return;
    }

    const query = searchQuery.toLowerCase();

    // Find families where search matches child name but NOT family name
    visibleFamilies.forEach((family) => {
      const familyNameMatches = family.name.toLowerCase().includes(query);

      if (!familyNameMatches) {
        // Check if any child name matches
        const childNameMatches = family.children.some((child) =>
          child.name.toLowerCase().includes(query)
        );

        if (childNameMatches) {
          // Auto-expand this family
          setExpandedFamilies((prev) => {
            const newSet = new Set(prev);
            newSet.add(family.id);
            return newSet;
          });
        }
      }
    });
  }, [searchQuery, visibleFamilies]);

  // Toggle family expansion
  const toggleFamily = (familyId: number) => {
    const newExpanded = new Set(expandedFamilies);
    if (newExpanded.has(familyId)) {
      newExpanded.delete(familyId);
    } else {
      newExpanded.add(familyId);
    }
    setExpandedFamilies(newExpanded);
  };

  // Check in individual child
  const checkInChild = (familyId: number, childId: number) => {
    const actionId = createUndoAction(familyId, [childId]);
    const checkInTime = getCurrentTime();

    setFamilies((prev) =>
      prev.map((fam) => {
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
      })
    );

    const family = families.find((f) => f.id === familyId);
    const child = family?.children.find((c) => c.id === childId);
    if (child) {
      setSuccessToast(`${child.name} checked in!`);
    }

    // Close expansion if open
    setExpandedChildId(null);
  };

  // Check in entire family
  const checkInFamily = (familyId: number) => {
    const family = families.find((f) => f.id === familyId);
    if (!family) return;

    const childIdsToCheckIn = family.children
      .filter((c) => !c.checkedIn && c.ticket !== 'none')
      .map((c) => c.id);

    if (childIdsToCheckIn.length === 0) return;

    const actionId = createUndoAction(familyId, childIdsToCheckIn);
    const checkInTime = getCurrentTime();

    setFamilies((prev) =>
      prev.map((fam) => {
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
      })
    );

    setSuccessToast(
      `${family.name} family checked in (${childIdsToCheckIn.length} ${
        childIdsToCheckIn.length === 1 ? 'child' : 'children'
      })!`
    );
  };

  // Undo individual child check-in
  const undoChildCheckIn = (familyId: number, childId: number) => {
    const family = families.find((f) => f.id === familyId);
    const child = family?.children.find((c) => c.id === childId);

    if (child?.checkInActionId) {
      removeUndoAction(child.checkInActionId);

      setFamilies((prev) =>
        prev.map((fam) => {
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
        })
      );

      if (child) {
        setSuccessToast(`${child.name} check-in undone`);
      }
    }
  };

  // Undo family check-in
  const undoFamilyCheckIn = (familyId: number) => {
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
    setFamilies((prev) =>
      prev.map((fam) => {
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
      })
    );

    setSuccessToast(`${family.name} check-in undone`);
  };

  // Assign ticket and check in child
  const assignTicketAndCheckIn = (
    familyId: number,
    childId: number,
    ticketType: TicketType
  ) => {
    // First update the ticket type
    setFamilies((prev) =>
      prev.map((fam) => {
        if (fam.id !== familyId) return fam;
        return {
          ...fam,
          children: fam.children.map((child) => {
            if (child.id !== childId) return child;
            return { ...child, ticket: ticketType };
          }),
        };
      })
    );

    // Then check in the child
    setTimeout(() => checkInChild(familyId, childId), 0);
  };

  // Add new family
  const handleAddFamily = (data: {
    familyName: string;
    childrenNames: string[];
    ticketType: TicketType;
  }) => {
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

    setFamilies((prev) => [...prev, newFamily].sort((a, b) => a.name.localeCompare(b.name)));
    setNextFamilyId(newFamilyId + 1);
    setNextChildId(currentChildId);
    setShowAddPanel(false);
    setSuccessToast(
      `${data.familyName} family added with ${newChildren.length} ${
        newChildren.length === 1 ? 'child' : 'children'
      }!`
    );

    // Auto-expand the new family
    setExpandedFamilies((prev) => new Set(prev).add(newFamilyId));
  };

  // Get family-level undo remaining time
  const getFamilyUndoSeconds = (familyId: number): number | null => {
    const familyActions = getFamilyUndoActions(familyId);
    const familyAction = familyActions.find((a) => a.childIds.length > 1);
    return familyAction ? getRemainingTime(familyAction.id) : null;
  };

  return (
    <div className="min-h-screen bg-slate-100">
      <div className="max-w-4xl mx-auto p-5">
        {/* Session Indicator */}
        <SessionIndicator
          eventName="Summer Conference 2025"
          sessionName="Morning Care"
          sessionTime="8:00 AM - 12:00 PM"
          onChangeSession={() => alert('Change session functionality')}
          onAddFamily={() => setShowAddPanel(true)}
        />

        {/* Add Family Panel */}
        {showAddPanel && (
          <AddFamilyPanel
            onAdd={handleAddFamily}
            onClose={() => setShowAddPanel(false)}
          />
        )}

        {/* Header */}
        <div className="mb-5">
          <h1 className="text-3xl font-bold text-blue-900">Check-In Station</h1>
        </div>

        {/* Search Box */}
        <div className="mb-4">
          <div className="relative">
            <Search
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
              size={20}
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by family or child name..."
              className="w-full pl-10 pr-10 py-3 border-2 border-blue-500 rounded-lg bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
              data-testid="search-input"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                aria-label="Clear search"
                data-testid="clear-search-button"
              >
                <X size={20} />
              </button>
            )}
          </div>
        </div>

        {/* Stats Header */}
        <div className="mb-4 flex items-center justify-between text-sm">
          <span className="text-slate-600" data-testid="family-count-text">
            {visibleFamilies.length}{' '}
            {visibleFamilies.length === 1 ? 'family' : 'families'}
            {searchQuery && ' matching search'}
          </span>
        </div>

        {/* Family Cards */}
        <div className="space-y-3">
          {visibleFamilies.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-lg border-2 border-dashed border-slate-300">
              <p className="text-slate-500 mb-2">
                {searchQuery
                  ? `No families found matching "${searchQuery}"`
                  : 'No families to check in'}
              </p>
              {searchQuery && (
                <p className="text-sm text-slate-400">Try a different search term</p>
              )}
            </div>
          ) : (
            visibleFamilies.map((family) => (
              <FamilyCard
                key={family.id}
                family={family}
                expanded={expandedFamilies.has(family.id)}
                onToggle={() => toggleFamily(family.id)}
                onCheckInChild={(childId) => checkInChild(family.id, childId)}
                onCheckInFamily={() => checkInFamily(family.id)}
                onUndoChild={(childId) => undoChildCheckIn(family.id, childId)}
                onUndoFamily={() => undoFamilyCheckIn(family.id)}
                onAssignTicket={(childId, ticketType) =>
                  assignTicketAndCheckIn(family.id, childId, ticketType)
                }
                expandedChildId={expandedChildId}
                onToggleChildExpansion={setExpandedChildId}
                getRemainingTime={getRemainingTime}
                familyUndoSeconds={getFamilyUndoSeconds(family.id)}
              />
            ))
          )}
        </div>
      </div>

      {/* Success Toast */}
      {successToast && (
        <SuccessToast
          message={successToast}
          onClose={() => setSuccessToast(null)}
        />
      )}

      {/* Animations */}
      <style>{`
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
        .animate-slide-in {
          animation: slide-in 0.3s ease-out;
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
        .animate-expand {
          animation: expand 0.2s ease-out;
        }
      `}</style>
    </div>
  );
}
