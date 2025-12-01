import React, { useState } from 'react';
import { Camera, X, Search, ChevronDown, ChevronRight } from 'lucide-react';

// ============================================================================
// MOCK DATA
// ============================================================================

const MOCK_FAMILIES = [
  {
    id: 1,
    name: 'Garcia',
    children: [
      { id: 1, name: 'Isabella Garcia', ticket: 'event', checkedIn: true, checkInTime: '9:05 AM' },
      { id: 2, name: 'Lucas Garcia', ticket: 'none', checkedIn: false }
    ]
  },
  {
    id: 2,
    name: 'Johnson',
    children: [
      { id: 3, name: 'Sophia Johnson', ticket: 'session', checkedIn: false }
    ]
  },
  {
    id: 3,
    name: 'Smith',
    children: [
      { id: 4, name: 'Emma Smith', ticket: 'event', checkedIn: false },
      { id: 5, name: 'Oliver Smith', ticket: 'event', checkedIn: true, checkInTime: '9:16 AM' }
    ]
  },
  {
    id: 4,
    name: 'Anderson',
    children: [
      { id: 6, name: 'Liam Anderson', ticket: 'event', checkedIn: false },
      { id: 7, name: 'Mia Anderson', ticket: 'event', checkedIn: false },
      { id: 8, name: 'Noah Anderson', ticket: 'session', checkedIn: false }
    ]
  },
  {
    id: 5,
    name: 'Martinez',
    children: [
      { id: 9, name: 'Sofia Martinez', ticket: 'event', checkedIn: true, checkInTime: '8:45 AM' },
      { id: 10, name: 'Diego Martinez', ticket: 'event', checkedIn: true, checkInTime: '8:45 AM' }
    ]
  }
];

// ============================================================================
// COMPONENTS
// ============================================================================

// Session Indicator
const SessionIndicator = ({ eventName, sessionName, sessionTime, onChangeSession }: {
  eventName: string;
  sessionName: string;
  sessionTime: string;
  onChangeSession: () => void;
}) => (
  <div className="bg-slate-50 border border-slate-300 rounded px-3 py-2 mb-4 flex flex-wrap justify-between items-center gap-2 text-sm">
    <div className="text-slate-600">
      <span className="font-semibold text-blue-900">Event:</span> {eventName} •
      <span className="font-semibold text-blue-900 ml-1">Session:</span> {sessionName} ({sessionTime})
    </div>
    <button
      onClick={onChangeSession}
      className="text-blue-600 font-semibold hover:underline"
    >
      Change Session
    </button>
  </div>
);

// Child Check-In Button Component
const ChildCheckInButton = ({ status, ticket, checkInTime, onCheckIn, onOverride }: {
  status: string;
  ticket: string;
  checkInTime?: string;
  onCheckIn: () => void;
  onOverride: () => void;
}) => {
  if (status === 'checked-in') {
    return (
      <button
        disabled
        title={`Checked in at ${checkInTime}`}
        className="px-3 py-1.5 bg-slate-400 text-white text-sm font-semibold rounded cursor-not-allowed"
      >
        Checked In
      </button>
    );
  }

  if (ticket === 'none') {
    return (
      <button
        onClick={onOverride}
        className="px-3 py-1.5 bg-red-100 text-red-700 text-sm font-semibold rounded border border-red-300 hover:bg-red-200 transition-colors"
      >
        No Ticket
      </button>
    );
  }

  return (
    <button
      onClick={onCheckIn}
      className="px-3 py-1.5 bg-green-600 text-white text-sm font-semibold rounded hover:bg-green-700 transition-colors"
    >
      Check In
    </button>
  );
};

// Family Card Component
const FamilyCard = ({ family, expanded, onToggle, onCheckInChild, onCheckInFamily, onOverride }: {
  family: any;
  expanded: boolean;
  onToggle: () => void;
  onCheckInChild: (familyId: number, childId: number) => void;
  onCheckInFamily: (familyId: number) => void;
  onOverride: (familyId: number, childId: number) => void;
}) => {
  // Calculate stats
  const totalChildren = family.children.length;
  const checkedInCount = family.children.filter((c: any) => c.checkedIn).length;
  const canCheckInCount = family.children.filter((c: any) => !c.checkedIn && c.ticket !== 'none').length;
  const allCheckedIn = checkedInCount === totalChildren;

  return (
    <div className="bg-white border border-slate-300 rounded-lg overflow-hidden mb-3 hover:shadow-md transition-shadow">
      {/* Family Header */}
      <div className="bg-slate-50 p-3 flex items-center justify-between">
        <div className="flex items-center gap-2 flex-1">
          <button
            onClick={onToggle}
            className="text-slate-600 hover:text-slate-900 transition-colors"
          >
            {expanded ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
          </button>
          <div className="flex-1">
            <h3 className="font-bold text-blue-900 text-lg">{family.name} Family</h3>
            <p className="text-sm text-slate-600">
              {totalChildren} {totalChildren === 1 ? 'child' : 'children'} • {checkedInCount} checked in
            </p>
          </div>
        </div>

        {/* Family Check-In Button */}
        {!allCheckedIn && canCheckInCount > 0 && (
          <button
            onClick={() => onCheckInFamily(family.id)}
            className="px-4 py-2 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors text-sm"
          >
            Check In Family ({canCheckInCount})
          </button>
        )}

        {allCheckedIn && (
          <span className="px-4 py-2 bg-slate-200 text-slate-600 font-semibold rounded-lg text-sm">
            All Checked In
          </span>
        )}
      </div>

      {/* Children List (when expanded) */}
      {expanded && (
        <div className="p-3 space-y-2">
          {family.children.map((child: any) => (
            <div
              key={child.id}
              className="flex items-center justify-between p-2 bg-slate-50 rounded border border-slate-200"
            >
              <div className="flex-1">
                <div className="font-medium text-slate-700">{child.name}</div>
                <div className="text-xs text-slate-500 mt-0.5">
                  {child.ticket === 'event' && '🟢 Event Pass'}
                  {child.ticket === 'session' && '🔵 Session Ticket'}
                  {child.ticket === 'none' && '🔴 No Ticket'}
                  {child.checkedIn && ` • Checked in at ${child.checkInTime}`}
                </div>
              </div>

              <ChildCheckInButton
                status={child.checkedIn ? 'checked-in' : 'ready'}
                ticket={child.ticket}
                checkInTime={child.checkInTime}
                onCheckIn={() => onCheckInChild(family.id, child.id)}
                onOverride={() => onOverride(family.id, child.id)}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// QR Scanner View
const QRScannerView = ({ onClose, onFamilyScanned }: {
  onClose: () => void;
  onFamilyScanned: (familyId: number) => void;
}) => {
  const [scannedFamily, setScannedFamily] = useState<any>(null);

  const simulateScan = () => {
    // Simulate scanning a random family
    const randomFamily = MOCK_FAMILIES[Math.floor(Math.random() * MOCK_FAMILIES.length)];
    setScannedFamily(randomFamily);
  };

  const handleCheckInFamily = (familyId: number) => {
    onFamilyScanned(familyId);
    // Go back to camera for next scan
    setScannedFamily(null);
  };

  return (
    <div className="fixed inset-0 bg-slate-900 z-50 flex flex-col">
      {/* Header */}
      <div className="bg-slate-800 p-4 flex items-center justify-between">
        <button
          onClick={() => scannedFamily ? setScannedFamily(null) : onClose()}
          className="text-white hover:text-slate-300 transition-colors"
        >
          {scannedFamily ? '← Back to Camera' : <X size={24} />}
        </button>
        <h2 className="text-white font-semibold">QR Code Scanner</h2>
        <div className="w-6"></div>
      </div>

      {/* Camera View or Family Panel */}
      {!scannedFamily ? (
        <div className="flex-1 flex items-center justify-center bg-slate-800">
          {/* Simulated Camera View */}
          <div className="text-center">
            <Camera size={80} className="text-white mx-auto mb-4" />
            <p className="text-white text-lg mb-6">Position QR code in frame</p>
            <button
              onClick={simulateScan}
              className="px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700"
            >
              Simulate Scan
            </button>
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-auto p-4 bg-slate-100">
          <div className="max-w-md mx-auto">
            <FamilyCard
              family={scannedFamily}
              expanded={true}
              onToggle={() => {}}
              onCheckInChild={(famId, childId) => {
                alert(`Checked in child ${childId}`);
                // In real app, update state and continue scanning
              }}
              onCheckInFamily={handleCheckInFamily}
              onOverride={(famId, childId) => {
                if (confirm('This child does not have a valid ticket. Check in anyway?')) {
                  alert(`Override check-in for child ${childId}`);
                }
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
};

// Override Confirmation Modal
const OverrideModal = ({ childName, onConfirm, onCancel }: {
  childName: string;
  onConfirm: () => void;
  onCancel: () => void;
}) => (
  <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
    <div className="bg-white rounded-lg p-6 max-w-md w-full">
      <h3 className="text-lg font-bold text-slate-900 mb-2">No Valid Ticket</h3>
      <p className="text-slate-600 mb-4">
        <strong>{childName}</strong> does not have a valid ticket for this session.
        Do you want to check them in anyway?
      </p>
      <div className="flex gap-3">
        <button
          onClick={onCancel}
          className="flex-1 px-4 py-2 bg-slate-200 text-slate-700 font-semibold rounded-lg hover:bg-slate-300"
        >
          Cancel
        </button>
        <button
          onClick={onConfirm}
          className="flex-1 px-4 py-2 bg-orange-600 text-white font-semibold rounded-lg hover:bg-orange-700"
        >
          Check In Anyway
        </button>
      </div>
    </div>
  </div>
);

// Success Toast
const SuccessToast = ({ message, onClose }: {
  message: string;
  onClose: () => void;
}) => {
  React.useEffect(() => {
    const timer = setTimeout(onClose, 3000);
    return () => clearTimeout(timer);
  }, [onClose]);

  return (
    <div className="fixed top-4 right-4 bg-green-600 text-white px-4 py-3 rounded-lg shadow-lg flex items-center gap-2 z-50 animate-slide-in">
      <span className="text-xl">✓</span>
      <span className="font-semibold">{message}</span>
    </div>
  );
};

// ============================================================================
// MAIN CHECK-IN VIEW
// ============================================================================

export default function ImprovedCheckIn() {
  const [families, setFamilies] = useState(MOCK_FAMILIES);
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedFamilies, setExpandedFamilies] = useState(new Set<number>());
  const [showScanner, setShowScanner] = useState(false);
  const [overrideModal, setOverrideModal] = useState<any>(null);
  const [successToast, setSuccessToast] = useState<string | null>(null);
  const [showAllFamilies, setShowAllFamilies] = useState(true);

  // Filter families based on search
  const filteredFamilies = families.filter(family => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return family.name.toLowerCase().includes(query) ||
           family.children.some(child => child.name.toLowerCase().includes(query));
  });

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
    setFamilies(families.map(fam => {
      if (fam.id !== familyId) return fam;
      return {
        ...fam,
        children: fam.children.map(child => {
          if (child.id !== childId) return child;
          return { ...child, checkedIn: true, checkInTime: new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }) };
        })
      };
    }));

    const family = families.find(f => f.id === familyId);
    const child = family?.children.find(c => c.id === childId);
    if (child) {
      setSuccessToast(`${child.name} checked in!`);
    }
  };

  // Check in entire family
  const checkInFamily = (familyId: number) => {
    setFamilies(families.map(fam => {
      if (fam.id !== familyId) return fam;
      return {
        ...fam,
        children: fam.children.map(child => {
          if (child.checkedIn || child.ticket === 'none') return child;
          return { ...child, checkedIn: true, checkInTime: new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }) };
        })
      };
    }));

    const family = families.find(f => f.id === familyId);
    if (family) {
      const count = family.children.filter(c => !c.checkedIn && c.ticket !== 'none').length;
      setSuccessToast(`${family.name} family checked in (${count} ${count === 1 ? 'child' : 'children'})!`);
    }
  };

  // Handle override
  const handleOverride = (familyId: number, childId: number) => {
    const family = families.find(f => f.id === familyId);
    const child = family?.children.find(c => c.id === childId);
    if (child) {
      setOverrideModal({ familyId, childId, childName: child.name });
    }
  };

  const confirmOverride = () => {
    if (overrideModal) {
      checkInChild(overrideModal.familyId, overrideModal.childId);
      setOverrideModal(null);
    }
  };

  return (
    <div className="min-h-screen bg-slate-100">
      <div className="max-w-4xl mx-auto p-5">
        {/* Session Indicator */}
        <SessionIndicator
          eventName="Summer Conference 2025"
          sessionName="Morning Care"
          sessionTime="8:00 AM - 12:00 PM"
          onChangeSession={() => alert('Change session')}
        />

        {/* Header with QR Button */}
        <div className="flex items-center justify-between mb-5">
          <h1 className="text-3xl font-bold text-blue-900">Check-In Station</h1>
          <button
            onClick={() => setShowScanner(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Camera size={20} />
            Scan QR
          </button>
        </div>

        {/* Search Box */}
        <div className="mb-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={20} />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by family or child name..."
              className="w-full pl-10 pr-10 py-3 border-2 border-blue-500 rounded-lg bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                <X size={20} />
              </button>
            )}
          </div>
        </div>

        {/* Filter Toggle */}
        <div className="mb-4 flex items-center gap-2">
          <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
            <input
              type="checkbox"
              checked={showAllFamilies}
              onChange={(e) => setShowAllFamilies(e.target.checked)}
              className="w-4 h-4"
            />
            Show all families (including fully checked in)
          </label>
        </div>

        {/* Stats Header */}
        <div className="mb-4 flex items-center justify-between text-sm">
          <span className="text-slate-600">
            {filteredFamilies.length} {filteredFamilies.length === 1 ? 'family' : 'families'}
            {searchQuery && ' matching search'}
          </span>
        </div>

        {/* Family Cards */}
        <div className="space-y-3">
          {filteredFamilies.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-lg border-2 border-dashed border-slate-300">
              <p className="text-slate-500 mb-2">No families found matching "{searchQuery}"</p>
              <p className="text-sm text-slate-400">Try a different search term</p>
            </div>
          ) : (
            filteredFamilies.map(family => (
              <FamilyCard
                key={family.id}
                family={family}
                expanded={expandedFamilies.has(family.id)}
                onToggle={() => toggleFamily(family.id)}
                onCheckInChild={checkInChild}
                onCheckInFamily={checkInFamily}
                onOverride={handleOverride}
              />
            ))
          )}
        </div>

        {/* Add Family Button */}
        <div className="mt-6 text-center py-8 bg-white rounded-lg border-2 border-dashed border-slate-300">
          <p className="text-slate-500 mb-3">Can't find the family you're looking for?</p>
          <button className="px-6 py-2 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700">
            + Add New Family
          </button>
        </div>
      </div>

      {/* QR Scanner Modal */}
      {showScanner && (
        <QRScannerView
          onClose={() => setShowScanner(false)}
          onFamilyScanned={(familyId) => {
            checkInFamily(familyId);
            setShowScanner(false);
          }}
        />
      )}

      {/* Override Confirmation Modal */}
      {overrideModal && (
        <OverrideModal
          childName={overrideModal.childName}
          onConfirm={confirmOverride}
          onCancel={() => setOverrideModal(null)}
        />
      )}

      {/* Success Toast */}
      {successToast && (
        <SuccessToast
          message={successToast}
          onClose={() => setSuccessToast(null)}
        />
      )}

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
      `}</style>
    </div>
  );
}
