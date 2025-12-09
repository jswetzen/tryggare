import React, { useState } from 'react';

// ============================================================================
// REUSABLE COMPONENTS
// ============================================================================

// Session Indicator Component
// Svelte equivalent: export let eventName, sessionName, onChangeSession
const SessionIndicator = ({ eventName, sessionName, sessionTime, onChangeSession }) => (
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

// Page Header Component
const PageHeader = ({ title }) => (
  <h1 className="text-blue-900 text-2xl font-bold mb-5 pb-2 border-b-2 border-slate-200">
    {title}
  </h1>
);

// Search Box Component
// Svelte: export let value, onInput (use bind:value in Svelte)
const SearchBox = ({ value, onChange, placeholder = "Search by last name or first name..." }) => (
  <div className="border-2 border-blue-500 rounded-md p-3 mb-5 bg-blue-50">
    <label className="block font-semibold text-blue-900 mb-2 text-sm">
      Search Families
    </label>
    <input
      type="text"
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      className="w-full px-3 py-2 border border-slate-300 rounded bg-white text-sm"
    />
  </div>
);

// Ticket Badge Component
// Svelte: export let type (where type = 'event' | 'session' | 'none')
const TicketBadge = ({ type }) => {
  const styles = {
    event: 'bg-green-600',
    session: 'bg-blue-600',
    none: 'bg-red-600'
  };
  
  const labels = {
    event: 'Event Pass',
    session: 'Session Ticket',
    none: 'No Ticket'
  };
  
  return (
    <div className="flex items-center gap-2">
      <span className={`w-3 h-3 rounded-full ${styles[type]}`} />
      <span className="text-sm">{labels[type]}</span>
    </div>
  );
};

// Icon Button Component
// Svelte: export let variant, tooltip, onClick, disabled = false
const IconButton = ({ variant, tooltip, onClick, disabled = false }) => {
  const styles = {
    checkin: 'bg-green-600 hover:bg-green-700',
    checkout: 'bg-red-600 hover:bg-red-700',
    'checked-in': 'bg-slate-500',
    'checked-out': 'bg-slate-500',
    'family-checkin': 'bg-blue-600 hover:bg-blue-700',
    'family-checkout': 'bg-orange-600 hover:bg-orange-700'
  };
  
  const icons = {
    checkin: '✓',
    checkout: '→',
    'checked-in': '✓',
    'checked-out': '✓',
    'family-checkin': '✓✓',
    'family-checkout': '→→'
  };
  
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={tooltip}
      className={`
        w-8 h-8 rounded-md text-white font-bold flex items-center justify-center
        ${styles[variant]} ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        relative group
      `}
    >
      <span className={variant.includes('family') ? 'text-xs' : ''}>{icons[variant]}</span>
      <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-1 bg-slate-800 text-white text-xs rounded whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity">
        {tooltip}
      </span>
    </button>
  );
};

// Table Header Component
const TableHeader = ({ title, count }) => (
  <div className="flex justify-between items-center my-5 pb-2 border-b border-slate-200">
    <h2 className="text-lg font-semibold text-slate-700">{title}</h2>
    <span className="text-sm text-slate-500">{count} families</span>
  </div>
);

// ============================================================================
// CHECK-IN PAGE DEMO
// ============================================================================

const CheckInDemo = () => {
  // Svelte: let searchQuery = '';
  const [searchQuery, setSearchQuery] = useState('');
  
  // Sample data
  const families = [
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
    }
  ];
  
  return (
    <div className="max-w-3xl mx-auto bg-white border-2 border-slate-300 rounded-lg p-5 shadow-lg">
      <SessionIndicator
        eventName="Summer Conference 2025"
        sessionName="Morning Care"
        sessionTime="8:00 AM - 12:00 PM"
        onChangeSession={() => alert('Change session clicked')}
      />
      
      <PageHeader title="Check-In Station" />
      
      <SearchBox
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
      />
      
      <TableHeader title="Registered Families" count={families.length} />
      
      <table className="w-full border-collapse mb-5">
        <thead className="bg-slate-100">
          <tr>
            <th className="text-left p-2 font-semibold text-slate-600 text-sm border-b-2 border-slate-300">
              Family / Child
            </th>
            <th className="text-left p-2 font-semibold text-slate-600 text-sm border-b-2 border-slate-300">
              Ticket
            </th>
            <th className="text-center p-2 font-semibold text-slate-600 text-sm border-b-2 border-slate-300 w-20">
              Check In
            </th>
          </tr>
        </thead>
        <tbody>
          {families.map((family, idx) => {
            const bgColor = idx % 2 === 0 ? 'bg-slate-50' : 'bg-slate-100/50';
            const uncheckedCount = family.children.filter(c => !c.checkedIn).length;
            
            return (
              <React.Fragment key={family.id}>
                {/* Family Name Row */}
                <tr className={bgColor}>
                  <td className="p-2 font-bold text-blue-900 border-b border-slate-200">
                    {family.name}
                  </td>
                  <td className="p-2 border-b border-slate-200"></td>
                  <td className="p-2 text-center border-b border-slate-200">
                    {uncheckedCount > 0 && (
                      <IconButton
                        variant="family-checkin"
                        tooltip={`Check in ${family.name} family (${uncheckedCount})`}
                        onClick={() => alert(`Check in ${family.name} family`)}
                      />
                    )}
                  </td>
                </tr>
                
                {/* Children Rows */}
                {family.children.map((child, childIdx) => {
                  const isLastChild = childIdx === family.children.length - 1;
                  return (
                    <tr key={child.id} className={bgColor}>
                      <td className={`p-2 pl-5 font-medium text-slate-700 text-sm ${isLastChild ? 'border-b-2 border-slate-300' : 'border-b border-slate-200'}`}>
                        {child.name}
                      </td>
                      <td className={`p-2 ${isLastChild ? 'border-b-2 border-slate-300' : 'border-b border-slate-200'}`}>
                        <TicketBadge type={child.ticket} />
                      </td>
                      <td className={`p-2 text-center ${isLastChild ? 'border-b-2 border-slate-300' : 'border-b border-slate-200'}`}>
                        <IconButton
                          variant={child.checkedIn ? 'checked-in' : 'checkin'}
                          tooltip={child.checkedIn ? 'Checked In' : 'Check In'}
                          onClick={() => alert(`Check in ${child.name}`)}
                          disabled={child.checkedIn}
                        />
                      </td>
                    </tr>
                  );
                })}
              </React.Fragment>
            );
          })}
        </tbody>
      </table>
      
      <div className="text-center p-8 bg-slate-50 border-2 border-dashed border-slate-300 rounded-md mt-5">
        <p className="text-slate-500 mb-3">Can't find the family you're looking for?</p>
        <button className="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-5 py-2 rounded">
          + Add New Family
        </button>
      </div>
    </div>
  );
};

// ============================================================================
// CHECK-OUT PAGE DEMO
// ============================================================================

const CheckOutDemo = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [pickupBy, setPickupBy] = useState({});
  
  // Only checked-in children
  const families = [
    {
      id: 1,
      name: 'Garcia',
      children: [
        { id: 1, name: 'Isabella Garcia', checkInTime: '9:05 AM', checkedOut: false }
      ]
    },
    {
      id: 3,
      name: 'Smith',
      children: [
        { id: 4, name: 'Emma Smith', checkInTime: '9:15 AM', checkedOut: false },
        { id: 5, name: 'Oliver Smith', checkInTime: '9:16 AM', checkedOut: false }
      ]
    }
  ];
  
  return (
    <div className="max-w-3xl mx-auto bg-white border-2 border-slate-300 rounded-lg p-5 shadow-lg">
      <SessionIndicator
        eventName="Summer Conference 2025"
        sessionName="Morning Care"
        sessionTime="8:00 AM - 12:00 PM"
        onChangeSession={() => alert('Change session clicked')}
      />
      
      <PageHeader title="Check-Out Station" />
      
      <SearchBox
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
      />
      
      <TableHeader title="Checked-In Children" count={families.length} />
      
      <table className="w-full border-collapse mb-5">
        <thead className="bg-slate-100">
          <tr>
            <th className="text-left p-2 font-semibold text-slate-600 text-sm border-b-2 border-slate-300">
              Family / Child
            </th>
            <th className="text-left p-2 font-semibold text-slate-600 text-sm border-b-2 border-slate-300">
              Checked In
            </th>
            <th className="text-center p-2 font-semibold text-slate-600 text-sm border-b-2 border-slate-300 w-20">
              Check Out
            </th>
          </tr>
        </thead>
        <tbody>
          {families.map((family, idx) => {
            const bgColor = idx % 2 === 0 ? 'bg-slate-50' : 'bg-slate-100/50';
            const notCheckedOutCount = family.children.filter(c => !c.checkedOut).length;
            
            return (
              <React.Fragment key={family.id}>
                {/* Family Name Row */}
                <tr className={bgColor}>
                  <td className="p-2 font-bold text-blue-900 border-b border-slate-200">
                    {family.name}
                  </td>
                  <td className="p-2 border-b border-slate-200"></td>
                  <td className="p-2 text-center border-b border-slate-200">
                    {notCheckedOutCount > 0 && (
                      <IconButton
                        variant="family-checkout"
                        tooltip={`Check out ${family.name} family (${notCheckedOutCount})`}
                        onClick={() => alert(`Check out ${family.name} family`)}
                      />
                    )}
                  </td>
                </tr>
                
                {/* Children Rows */}
                {family.children.map((child) => (
                  <tr key={child.id} className={bgColor}>
                    <td className="p-2 pl-5 font-medium text-slate-700 text-sm border-b border-slate-200">
                      {child.name}
                    </td>
                    <td className="p-2 border-b border-slate-200">
                      <span className="text-slate-500 text-sm">{child.checkInTime}</span>
                    </td>
                    <td className="p-2 text-center border-b border-slate-200">
                      <IconButton
                        variant={child.checkedOut ? 'checked-out' : 'checkout'}
                        tooltip={child.checkedOut ? 'Checked Out' : 'Check Out'}
                        onClick={() => alert(`Check out ${child.name}`)}
                        disabled={child.checkedOut}
                      />
                    </td>
                  </tr>
                ))}
                
                {/* Pickup By Row */}
                <tr className={`${bgColor} border-b-2 border-slate-300`}>
                  <td colSpan="3" className="p-2 pb-3">
                    <div className="flex items-center gap-2 pl-5">
                      <span className="text-sm text-slate-500 font-semibold">Picked up by:</span>
                      <select
                        value={pickupBy[family.id] || ''}
                        onChange={(e) => setPickupBy({ ...pickupBy, [family.id]: e.target.value })}
                        className="px-2 py-1 border border-slate-300 rounded text-sm bg-white text-slate-700"
                      >
                        <option value="">Select...</option>
                        <option value="mom">Mom</option>
                        <option value="dad">Dad</option>
                        <option value="grandma">Grandma</option>
                        <option value="other">Other</option>
                      </select>
                    </div>
                  </td>
                </tr>
              </React.Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

// ============================================================================
// MAIN APP - Toggle between Check-In and Check-Out
// ============================================================================

export default function App() {
  const [view, setView] = useState('checkin');
  
  return (
    <div className="min-h-screen bg-slate-100 p-5">
      <div className="max-w-4xl mx-auto mb-5">
        <div className="flex gap-2 justify-center">
          <button
            onClick={() => setView('checkin')}
            className={`px-6 py-2 font-semibold rounded-t-lg transition-colors ${
              view === 'checkin'
                ? 'bg-white text-blue-900 border-b-2 border-blue-600'
                : 'bg-slate-200 text-slate-600 hover:bg-slate-300'
            }`}
          >
            Check-In View
          </button>
          <button
            onClick={() => setView('checkout')}
            className={`px-6 py-2 font-semibold rounded-t-lg transition-colors ${
              view === 'checkout'
                ? 'bg-white text-blue-900 border-b-2 border-blue-600'
                : 'bg-slate-200 text-slate-600 hover:bg-slate-300'
            }`}
          >
            Check-Out View
          </button>
        </div>
      </div>
      
      {view === 'checkin' ? <CheckInDemo /> : <CheckOutDemo />}
    </div>
  );
}
