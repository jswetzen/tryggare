/**
 * Tests for CheckinExpandableTable Component
 *
 * Note: This component renders both mobile and desktop layouts simultaneously (hidden with CSS),
 * so we use getAllBy* queries to handle multiple matching elements.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import CheckinExpandableTable from './CheckinExpandableTable.svelte';
import type { Family, Parent } from '$lib/checkin/types';

// Mock the i18n library
vi.mock('svelte-i18n', () => ({
  _: {
    subscribe: (fn: any) => {
      fn((key: string, options?: any) => {
        const translations: Record<string, string> = {
          'checkin.child': 'child',
          'checkin.children': 'children',
          'checkin.adult': 'adult',
          'checkin.adults': 'adults',
          'checkin.allCheckedIn': 'All Checked In',
          'checkin.alreadyCheckedIn': 'Already Checked In',
          'checkin.checkInCount': 'Check In {count}',
          'checkin.checkedInCount': '{count} checked in',
          'checkin.undoSeconds': 'Undo ({seconds}s)',
          'checkin.ticketEvent': 'Event',
          'checkin.ticketSession': 'Session',
          'checkin.ticketNone': 'No Ticket',
          'checkin.ticketNotRequired': 'No ticket needed',
          'checkin.ticketGuardianOnly': 'Guardian, no ticket needed',
          'checkin.adultsNotCheckedInHere': 'Adults are not checked in at this session',
          'checkin.checkedInAt': 'Checked in at {time}',
          'checkin.checkedInElsewhere': 'Checked in to {session}',
          'checkin.expandFamily': 'Expand {familyName} family',
          'checkin.collapseFamily': 'Collapse {familyName} family',
          'checkin.undoFamilyAria': 'Undo family check-in, {seconds} seconds remaining',
          'checkin.checkInFamilyAria': 'Check in {count} children from {familyName} family',
          'checkin.grantTicketPromptChild': 'This session requires a ticket for children. Check in {name} with:',
          'checkin.grantTicketPromptAdult': 'This session requires a ticket for adults. Check in {name} with:',
          'checkin.colFamily': 'Family',
          'checkin.colStatus': 'Status',
          'checkin.colActions': 'Actions',
          'checkin.guardianPresent': 'Guardian Present',
          'checkin.checkIn': 'Check In',
          'checkin.guardian': 'Guardian',
          'checkin.guardians': 'Guardians',
          'checkin.noTicketClickToAssign': 'No ticket - click to assign',
          'checkin.pendingPaymentBanner': 'Unpaid registration — {amount} {currency} owed',
          'checkin.markPaidNow': 'Mark paid now:',
          'checkin.markPaidSwish': 'Swish',
          'checkin.markPaidBankgiro': 'Bankgiro',
          'checkin.markPaidOther': 'Other',
          'checkin.confirmDespiteBalance': 'Let in, settle payment later',
          'checkin.confirmDespiteBalanceConfirm': 'Let this family in without full payment?',
          'checkin.pendingPaymentAwaiting': 'Awaiting payment',
          'checkin.pendingPaymentShort': 'Unpaid',
          'checkin.pendingPaymentBlockedTitle':
            'Registration is unpaid — resolve via the banner above before checking in',
        };

        if (options?.values) {
          let result = translations[key] || key;
          Object.entries(options.values).forEach(([k, v]) => {
            result = result.replace(`{${k}}`, String(v));
          });
          return result;
        }

        return translations[key] || key;
      });
      return () => {};
    }
  }
}));

// Mock the undo timer store
vi.mock('$lib/checkin/stores/undoTimer', () => ({
  undoActionsWithTick: {
    subscribe: (fn: any) => {
      fn({ actions: [], tick: 0 });
      return () => {};
    }
  }
}));

describe('CheckinExpandableTable', () => {
  const mockFamilies: Family[] = [
    {
      id: 'family-1',
      last_name: 'Smith',
      display_name: 'Smith Family',
      name: 'Smith Family',
      children: [
        {
          id: 'child-1',
          first_name: 'John',
          last_name: 'Smith',
          name: 'John Smith',
          ticket: 'event',
          ticket_type: 'event',
          checkedIn: false,
          family: 'family-1'
        },
        {
          id: 'child-2',
          first_name: 'Jane',
          last_name: 'Smith',
          name: 'Jane Smith',
          ticket: 'session',
          ticket_type: 'session',
          checkedIn: false,
          family: 'family-1'
        }
      ],
      parents: [{ id: 'parent-1', first_name: 'Bob', last_name: 'Smith', name: 'Bob Smith', relationship_type: 'father', ticket: 'none', ticket_type: 'none', checkedIn: false }]
    }
  ];

  const defaultProps = {
    families: mockFamilies,
    onCheckInChild: vi.fn(),
    onCheckInFamily: vi.fn(),
    onUndoChild: vi.fn(),
    onUndoFamily: vi.fn(),
    onAssignTicket: vi.fn(),
    getRemainingTime: vi.fn(() => null),
    supervisedState: {},
    expandedChildId: null,
    onToggleChildExpansion: vi.fn()
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    it('should render families with correct information', () => {
      render(CheckinExpandableTable, { props: defaultProps });

      expect(screen.getAllByText('Smith Family').length).toBeGreaterThan(0);
      expect(screen.getAllByText(/2 children/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/0 checked in/i).length).toBeGreaterThan(0);
    });

    it('should show all checked in badge when all children are checked in', () => {
      const allCheckedIn: Family[] = [
        {
          ...mockFamilies[0],
          children: mockFamilies[0].children.map(c => ({ ...c, checkedIn: true }))
        }
      ];

      render(CheckinExpandableTable, {
        props: { ...defaultProps, families: allCheckedIn }
      });

      expect(screen.getAllByText('All Checked In').length).toBeGreaterThan(0);
    });
  });

  describe('Family Expansion', () => {
    it('should toggle family expansion on click', async () => {
      const user = userEvent.setup();
      render(CheckinExpandableTable, { props: defaultProps });

      const toggleButtons = screen.getAllByTestId('family-toggle-button-family-1');

      // Initially collapsed
      expect(screen.queryByText('John Smith')).not.toBeInTheDocument();

      // Expand
      await user.click(toggleButtons[0]);

      // Wait for expansion (children should appear in both mobile and desktop views)
      expect(screen.queryAllByText('John Smith').length).toBeGreaterThanOrEqual(1);

      // Collapse
      await user.click(toggleButtons[0]);
      expect(screen.queryByText('John Smith')).not.toBeInTheDocument();
    });
  });

  describe('Check-In Functionality', () => {
    it('should call onCheckInChild when individual check-in button is clicked', async () => {
      const user = userEvent.setup();
      const onCheckInChild = vi.fn();

      render(CheckinExpandableTable, {
        props: { ...defaultProps, onCheckInChild }
      });

      // Expand family
      const toggleButtons = screen.getAllByTestId('family-toggle-button-family-1');
      await user.click(toggleButtons[0]);

      // Click check-in button (wait for it to appear)
      const checkInButtons = screen.queryAllByTestId('child-check-in-button-child-1');
      if (checkInButtons.length > 0) {
        await user.click(checkInButtons[0]);
        expect(onCheckInChild).toHaveBeenCalledWith('family-1', 'child-1');
      } else {
        // If not found, the test should fail with a clear message
        throw new Error('Check-in button not found after expansion');
      }
    });

    it('should call onCheckInFamily when family check-in button is clicked', async () => {
      const user = userEvent.setup();
      const onCheckInFamily = vi.fn();

      render(CheckinExpandableTable, {
        props: { ...defaultProps, onCheckInFamily }
      });

      const checkInButtons = screen.getAllByTestId('family-check-in-button-family-1');
      await user.click(checkInButtons[0]);

      expect(onCheckInFamily).toHaveBeenCalledWith('family-1');
    });

    it('should show family check-in button with correct count', () => {
      render(CheckinExpandableTable, { props: defaultProps });

      expect(screen.getAllByText('Check In 2').length).toBeGreaterThan(0);
    });
  });

  describe('Undo Functionality', () => {
    it('should show undo button with countdown for individual child', async () => {
      const user = userEvent.setup();
      const getRemainingTime = vi.fn((actionId: string) =>
        actionId === 'action-1' ? 25 : null
      );

      const checkedInFamily: Family[] = [
        {
          ...mockFamilies[0],
          children: [
            {
              ...mockFamilies[0].children[0],
              checkedIn: true,
              checkInActionId: 'action-1',
              checkInTime: '10:30'
            }
          ]
        }
      ];

      render(CheckinExpandableTable, {
        props: { ...defaultProps, families: checkedInFamily, getRemainingTime }
      });

      // Expand family
      const toggleButtons = screen.getAllByTestId('family-toggle-button-family-1');
      await user.click(toggleButtons[0]);

      expect(screen.queryAllByText(/Undo \(25s\)/i).length).toBeGreaterThanOrEqual(1);
    });

    it('should call onUndoChild when undo button is clicked', async () => {
      const user = userEvent.setup();
      const onUndoChild = vi.fn();
      const getRemainingTime = vi.fn(() => 20);

      const checkedInFamily: Family[] = [
        {
          ...mockFamilies[0],
          children: [
            {
              ...mockFamilies[0].children[0],
              checkedIn: true,
              checkInActionId: 'action-1',
              checkInTime: '10:30'
            }
          ]
        }
      ];

      render(CheckinExpandableTable, {
        props: { ...defaultProps, families: checkedInFamily, getRemainingTime, onUndoChild }
      });

      // Expand and click undo
      const toggleButtons = screen.getAllByTestId('family-toggle-button-family-1');
      await user.click(toggleButtons[0]);

      const undoButtons = screen.queryAllByTestId('child-undo-button-child-1');
      if (undoButtons.length > 0) {
        await user.click(undoButtons[0]);
        expect(onUndoChild).toHaveBeenCalledWith('family-1', 'child-1');
      } else {
        throw new Error('Undo button not found after expansion');
      }
    });

    it('should show family undo button when multiple children checked in together', () => {
      const getRemainingTime = vi.fn((actionId: string) =>
        actionId === 'family-action-1' ? 28 : null
      );

      const familyCheckedIn: Family[] = [
        {
          ...mockFamilies[0],
          children: mockFamilies[0].children.map(c => ({
            ...c,
            checkedIn: true,
            checkInActionId: 'family-action-1',
            checkInTime: '10:30'
          }))
        }
      ];

      render(CheckinExpandableTable, {
        props: { ...defaultProps, families: familyCheckedIn, getRemainingTime }
      });

      expect(screen.getAllByText(/Undo \(28s\)/i).length).toBeGreaterThan(0);
    });
  });

  describe('Supervised State', () => {
    it('should show supervised checkbox for eligible children', async () => {
      const user = userEvent.setup();
      render(CheckinExpandableTable, { props: defaultProps });

      // Expand family
      const toggleButtons = screen.getAllByTestId('family-toggle-button-family-1');
      await user.click(toggleButtons[0]);

      expect(screen.queryAllByTestId('supervised-checkbox-child-1').length).toBeGreaterThanOrEqual(1);
    });

    it('should not show supervised checkbox for checked-in children', async () => {
      const user = userEvent.setup();
      const checkedInFamily: Family[] = [
        {
          ...mockFamilies[0],
          children: [
            {
              ...mockFamilies[0].children[0],
              checkedIn: true
            }
          ]
        }
      ];

      render(CheckinExpandableTable, {
        props: { ...defaultProps, families: checkedInFamily }
      });

      // Expand family
      const toggleButtons = screen.getAllByTestId('family-toggle-button-family-1');
      await user.click(toggleButtons[0]);

      expect(screen.queryByTestId('supervised-checkbox-child-1')).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper test IDs for all interactive elements', () => {
      render(CheckinExpandableTable, { props: defaultProps });

      expect(screen.getAllByTestId('family-card-family-1').length).toBeGreaterThan(0);
      expect(screen.getAllByTestId('family-toggle-button-family-1').length).toBeGreaterThan(0);
      expect(screen.getAllByTestId('family-check-in-button-family-1').length).toBeGreaterThan(0);
    });

    it('should support keyboard navigation for expansion', async () => {
      const user = userEvent.setup();
      render(CheckinExpandableTable, { props: defaultProps });

      const toggleButtons = screen.getAllByTestId('family-toggle-button-family-1');
      const toggleButton = toggleButtons[0];

      toggleButton.focus();
      await user.keyboard('{Enter}');

      expect(screen.queryAllByText('John Smith').length).toBeGreaterThanOrEqual(1);

      await user.keyboard(' ');
      expect(screen.queryByText('John Smith')).not.toBeInTheDocument();
    });
  });

  describe('Search Auto-Expand', () => {
    const twoFamilies: Family[] = [
      {
        id: 'family-1',
        last_name: 'Smith',
        display_name: 'Smith Family',
        name: 'Smith Family',
        children: [
          {
            id: 'child-1',
            first_name: 'John',
            last_name: 'Smith',
            name: 'John Smith',
            ticket: 'event',
            ticket_type: 'event',
            checkedIn: false,
            family: 'family-1'
          }
        ],
        parents: []
      },
      {
        id: 'family-2',
        last_name: 'Jones',
        display_name: 'Jones Family',
        name: 'Jones Family',
        children: [
          {
            id: 'child-3',
            first_name: 'Alice',
            last_name: 'Jones',
            name: 'Alice Jones',
            ticket: 'session',
            ticket_type: 'session',
            checkedIn: false,
            family: 'family-2'
          }
        ],
        parents: []
      }
    ];

    it('should auto-expand family when search matches a child name', async () => {
      const { rerender } = render(CheckinExpandableTable, {
        props: { ...defaultProps, families: twoFamilies, searchQuery: '' }
      });

      // Initially collapsed — no child rows visible
      expect(screen.queryByText('John Smith')).not.toBeInTheDocument();

      // Search for child by first name
      await rerender({ ...defaultProps, families: twoFamilies, searchQuery: 'John' });

      // Family with matching child should be expanded
      expect(screen.queryAllByText('John Smith').length).toBeGreaterThanOrEqual(1);

      // Non-matching family's children should not be visible
      expect(screen.queryByText('Alice Jones')).not.toBeInTheDocument();
    });

    it('should collapse auto-expanded family when search is cleared', async () => {
      const { rerender } = render(CheckinExpandableTable, {
        props: { ...defaultProps, families: twoFamilies, searchQuery: 'John' }
      });

      // Should be expanded due to search
      expect(screen.queryAllByText('John Smith').length).toBeGreaterThanOrEqual(1);

      // Clear search
      await rerender({ ...defaultProps, families: twoFamilies, searchQuery: '' });

      // Should collapse back
      expect(screen.queryByText('John Smith')).not.toBeInTheDocument();
    });

    it('should not auto-expand when search matches only the family name', async () => {
      const { rerender } = render(CheckinExpandableTable, {
        props: { ...defaultProps, families: twoFamilies, searchQuery: '' }
      });

      // Search for family name (not child name)
      await rerender({ ...defaultProps, families: twoFamilies, searchQuery: 'Smith' });

      // Smith family matches by name but should NOT be auto-expanded
      expect(screen.queryByText('John Smith')).not.toBeInTheDocument();
    });

    it('should re-auto-expand after manual collapse when the search query changes', async () => {
      const user = userEvent.setup();
      const { rerender } = render(CheckinExpandableTable, {
        props: { ...defaultProps, families: twoFamilies, searchQuery: 'John' }
      });

      // Auto-expanded by initial search for "John"
      expect(screen.queryAllByText('John Smith').length).toBeGreaterThanOrEqual(1);

      // User manually collapses it
      const toggleButtons = screen.getAllByTestId('family-toggle-button-family-1');
      await user.click(toggleButtons[0]);
      expect(screen.queryByText('John Smith')).not.toBeInTheDocument();

      // User keeps typing — the query changes ("John" → "Joh"). Manual-collapse
      // memory belongs to the previous query and must not suppress auto-expand
      // for the new query.
      await rerender({ ...defaultProps, families: twoFamilies, searchQuery: 'Joh' });

      expect(screen.queryAllByText('John Smith').length).toBeGreaterThanOrEqual(1);
    });

    it('should keep the family collapsed while the search query is unchanged after a manual collapse', async () => {
      const user = userEvent.setup();
      render(CheckinExpandableTable, {
        props: { ...defaultProps, families: twoFamilies, searchQuery: 'John' }
      });

      expect(screen.queryAllByText('John Smith').length).toBeGreaterThanOrEqual(1);

      const toggleButtons = screen.getAllByTestId('family-toggle-button-family-1');
      await user.click(toggleButtons[0]);

      // Same query, user just collapsed it — it should stay collapsed.
      expect(screen.queryByText('John Smith')).not.toBeInTheDocument();
    });

    it('should keep manually expanded families expanded when search is cleared', async () => {
      const user = userEvent.setup();
      const { rerender } = render(CheckinExpandableTable, {
        props: { ...defaultProps, families: twoFamilies, searchQuery: '' }
      });

      // Manually expand Smith family
      const toggleButtons = screen.getAllByTestId('family-toggle-button-family-1');
      await user.click(toggleButtons[0]);
      expect(screen.queryAllByText('John Smith').length).toBeGreaterThanOrEqual(1);

      // Search for something unrelated to Smith family's children
      await rerender({ ...defaultProps, families: twoFamilies, searchQuery: 'Alice' });

      // Manually expanded family should still be expanded
      expect(screen.queryAllByText('John Smith').length).toBeGreaterThanOrEqual(1);

      // Clear search
      await rerender({ ...defaultProps, families: twoFamilies, searchQuery: '' });

      // Manually expanded family should still be expanded (not collapsed by search clear)
      expect(screen.queryAllByText('John Smith').length).toBeGreaterThanOrEqual(1);
    });
  });

  describe('Guardians Subsection', () => {
    const ticketedParent: Parent = {
      id: 'parent-ticketed',
      first_name: 'Alice',
      last_name: 'Smith',
      name: 'Alice Smith',
      relationship_type: 'mother',
      ticket: 'event',
      ticket_type: 'event',
      checkedIn: false
    };

    const noTicketParent: Parent = {
      id: 'parent-noticket',
      first_name: 'Bob',
      last_name: 'Smith',
      name: 'Bob Smith',
      relationship_type: 'father',
      ticket: 'none',
      ticket_type: 'none',
      checkedIn: false
    };

    const checkedInParent: Parent = {
      id: 'parent-checkedin',
      first_name: 'Carol',
      last_name: 'Smith',
      name: 'Carol Smith',
      relationship_type: 'mother',
      ticket: 'event',
      ticket_type: 'event',
      checkedIn: true,
      checkInTime: '10:00'
    };

    it('should render check-in button for a ticketed, not-checked-in parent', async () => {
      const user = userEvent.setup();
      const familyWithTicketedParent: Family[] = [
        { ...mockFamilies[0], parents: [ticketedParent] }
      ];

      render(CheckinExpandableTable, {
        props: { ...defaultProps, families: familyWithTicketedParent }
      });

      // Expand family
      const toggleButtons = screen.getAllByTestId('family-toggle-button-family-1');
      await user.click(toggleButtons[0]);

      expect(screen.queryAllByTestId('parent-check-in-button-parent-ticketed').length).toBeGreaterThanOrEqual(1);
    });

    it('should render expand button for a ticket-less parent', async () => {
      const user = userEvent.setup();
      const familyWithNoTicketParent: Family[] = [
        { ...mockFamilies[0], parents: [noTicketParent] }
      ];

      render(CheckinExpandableTable, {
        props: { ...defaultProps, families: familyWithNoTicketParent }
      });

      // Expand family
      const toggleButtons = screen.getAllByTestId('family-toggle-button-family-1');
      await user.click(toggleButtons[0]);

      expect(screen.queryAllByTestId('parent-expand-button-parent-noticket').length).toBeGreaterThanOrEqual(1);
    });

    it('should show ticket assignment buttons when ticket-less parent expansion is open', async () => {
      const user = userEvent.setup();
      const familyWithNoTicketParent: Family[] = [
        { ...mockFamilies[0], parents: [noTicketParent] }
      ];

      render(CheckinExpandableTable, {
        props: {
          ...defaultProps,
          families: familyWithNoTicketParent,
          expandedChildId: 'parent-noticket'
        }
      });

      // Expand family
      const toggleButtons = screen.getAllByTestId('family-toggle-button-family-1');
      await user.click(toggleButtons[0]);

      expect(screen.queryAllByTestId('parent-ticket-assign-session-parent-noticket').length).toBeGreaterThanOrEqual(1);
    });

    it('should not render a supervised checkbox for checked-in parents', async () => {
      const user = userEvent.setup();
      const familyWithCheckedInParent: Family[] = [
        { ...mockFamilies[0], parents: [checkedInParent] }
      ];

      render(CheckinExpandableTable, {
        props: { ...defaultProps, families: familyWithCheckedInParent }
      });

      // Expand family
      const toggleButtons = screen.getAllByTestId('family-toggle-button-family-1');
      await user.click(toggleButtons[0]);

      // There should be no supervised checkbox for the parent
      expect(screen.queryByTestId(`supervised-checkbox-${checkedInParent.id}`)).not.toBeInTheDocument();
    });

    it('should not render guardians section when family has no parents', async () => {
      const user = userEvent.setup();
      const familyNoParents: Family[] = [
        { ...mockFamilies[0], parents: [] }
      ];

      render(CheckinExpandableTable, {
        props: { ...defaultProps, families: familyNoParents }
      });

      // Expand family
      const toggleButtons = screen.getAllByTestId('family-toggle-button-family-1');
      await user.click(toggleButtons[0]);

      expect(screen.queryByText('Guardians')).not.toBeInTheDocument();
    });

    it('shows a guardian-only adult as allowed, with a neutral line instead of a ticket name', async () => {
      const user = userEvent.setup();
      const guardianOnly: Parent = {
        ...(mockFamilies[0].parents[0] as Parent),
        id: 'parent-guardian',
        ticket: 'event',
        ticket_type: 'event',
        ticketExemption: 'guardian_only',
      };

      render(CheckinExpandableTable, {
        props: { ...defaultProps, families: [{ ...mockFamilies[0], parents: [guardianOnly] }] }
      });
      await user.click(screen.getAllByTestId('family-toggle-button-family-1')[0]);

      expect(screen.queryAllByText('Guardian, no ticket needed').length).toBeGreaterThanOrEqual(1);
      expect(screen.queryAllByTestId('parent-check-in-button-parent-guardian').length).toBeGreaterThanOrEqual(1);
      expect(screen.queryAllByTestId('parent-expand-button-parent-guardian')).toHaveLength(0);
    });

    it('lists guardians with a calm note and no check-in button when parentCheckinEnabled is false', async () => {
      const user = userEvent.setup();

      render(CheckinExpandableTable, {
        props: { ...defaultProps, families: mockFamilies, parentCheckinEnabled: false }
      });

      const toggleButtons = screen.getAllByTestId('family-toggle-button-family-1');
      await user.click(toggleButtons[0]);

      // Still listed (they are there, just not checked in at this session) ...
      expect(screen.queryAllByText('Guardians').length).toBeGreaterThanOrEqual(1);
      expect(screen.queryAllByText('Adults are not checked in at this session').length).toBeGreaterThanOrEqual(1);
      // ... but neither an action nor the red no-ticket state is offered.
      expect(screen.queryAllByTestId(/^parent-check-in-button-/)).toHaveLength(0);
      expect(screen.queryAllByTestId(/^parent-expand-button-/)).toHaveLength(0);
    });
  });

  describe('Adults not checked in at this session', () => {
    const adultCheckedInElsewhere: Parent = {
      id: 'parent-in',
      first_name: 'Carol',
      last_name: 'Smith',
      name: 'Carol Smith',
      relationship_type: 'mother',
      // Checked in for another session; in this one adults are not checked in.
      ticket: 'none',
      ticket_type: 'none',
      checkedIn: true,
      checkInTime: '10:00'
    };

    it('shows the note for an adult whatever their checkedIn flag, not "No Ticket"', async () => {
      const user = userEvent.setup();
      render(CheckinExpandableTable, {
        props: {
          ...defaultProps,
          families: [{ ...mockFamilies[0], parents: [adultCheckedInElsewhere, mockFamilies[0].parents[0]] }],
          parentCheckinEnabled: false
        }
      });
      await user.click(screen.getAllByTestId('family-toggle-button-family-1')[0]);

      for (const id of ['parent-in', 'parent-1']) {
        const rows = screen.getAllByTestId(`parent-row-${id}`);
        for (const row of rows) {
          expect(within(row).getByText(/Adults are not checked in at this session/)).toBeInTheDocument();
          expect(within(row).queryByText('No Ticket')).not.toBeInTheDocument();
        }
      }
    });
  });

  describe('Adult checked in to a different session', () => {
    const adult = (over: Partial<Parent>): Parent => ({
      id: 'parent-x',
      first_name: 'Anna',
      last_name: 'Smith',
      name: 'Anna Smith',
      relationship_type: 'mother',
      ticket: 'event',
      ticket_type: 'event',
      checkedIn: false,
      ...over
    });

    async function rowsFor(parent: Parent) {
      const user = userEvent.setup();
      render(CheckinExpandableTable, {
        props: { ...defaultProps, families: [{ ...mockFamilies[0], parents: [parent] }] }
      });
      await user.click(screen.getAllByTestId('family-toggle-button-family-1')[0]);
      return screen.getAllByTestId('parent-row-parent-x');
    }

    it('says where, keeps the Check In button live, and does not read "Already Checked In"', async () => {
      const rows = await rowsFor(adult({ checkedInElsewhere: ['B children'] }));

      for (const row of rows) {
        expect(within(row).getByText(/Checked in to B children/)).toBeInTheDocument();
        expect(within(row).getByTestId('parent-check-in-button-parent-x')).toBeEnabled();
        expect(within(row).queryByText('Already Checked In')).not.toBeInTheDocument();
      }
    });

    it('lists every other session', async () => {
      const rows = await rowsFor(adult({ checkedInElsewhere: ['B children', 'C'] }));

      expect(within(rows[0]).getByText(/Checked in to B children, C/)).toBeInTheDocument();
    });

    it('shows no note for an adult who is not checked in anywhere else', async () => {
      const rows = await rowsFor(adult({ checkedInElsewhere: [] }));

      for (const row of rows) {
        expect(within(row).queryByText(/Checked in to/)).not.toBeInTheDocument();
      }
    });

    it('shows no note once the adult is checked in HERE', async () => {
      const rows = await rowsFor(
        adult({ checkedIn: true, checkInTime: '10:00', checkedInElsewhere: ['B children'] })
      );

      for (const row of rows) {
        expect(within(row).queryByText(/Checked in to B children/)).not.toBeInTheDocument();
        expect(within(row).getByText('Already Checked In')).toBeInTheDocument();
      }
    });
  });

  describe('Family check-in with a ticketless sibling', () => {
    const ticketless = {
      id: 'child-3',
      first_name: 'Kim',
      last_name: 'Smith',
      name: 'Kim Smith',
      ticket: 'none' as const,
      ticket_type: 'none' as const,
      checkedIn: false,
      family: 'family-1'
    };

    it('still offers "Check In (n)" for the eligible children', async () => {
      const user = userEvent.setup();
      const onCheckInFamily = vi.fn();
      render(CheckinExpandableTable, {
        props: {
          ...defaultProps,
          onCheckInFamily,
          families: [{ ...mockFamilies[0], children: [...mockFamilies[0].children, ticketless] }]
        }
      });

      // Two eligible children (the ticketless one is not counted) in both layouts.
      const buttons = screen.getAllByTestId('family-check-in-button-family-1');
      expect(buttons).toHaveLength(2);
      expect(buttons[0]).toHaveTextContent('Check In 2');
      await user.click(buttons[0]);
      expect(onCheckInFamily).toHaveBeenCalledWith('family-1');
    });
  });

  describe('Localised labels', () => {
    it('takes the expand / collapse and family check-in aria-labels from the catalogue', async () => {
      const user = userEvent.setup();
      render(CheckinExpandableTable, { props: defaultProps });

      const toggle = screen.getAllByTestId('family-toggle-button-family-1')[0];
      expect(toggle).toHaveAttribute('aria-label', 'Expand Smith Family family');
      await user.click(toggle);
      expect(toggle).toHaveAttribute('aria-label', 'Collapse Smith Family family');
      expect(screen.getAllByTestId('family-check-in-button-family-1')[0]).toHaveAttribute(
        'aria-label',
        'Check in 2 children from Smith Family family'
      );
    });

    it('takes the desktop column headers from the catalogue', () => {
      render(CheckinExpandableTable, { props: defaultProps });
      const headers = screen.getAllByRole('columnheader', { hidden: true }).map((h) => h.textContent?.trim());
      expect(headers).toEqual(['Family', 'Status', 'Actions']);
    });
  });

  describe('Grant-ticket panel', () => {
    const noTicketChild = {
      id: 'child-9',
      first_name: 'Nils',
      last_name: 'Smith',
      name: 'Nils Smith',
      ticket: 'none' as const,
      ticket_type: 'none' as const,
      checkedIn: false,
      family: 'family-1'
    };
    const noTicketAdult: Parent = {
      id: 'parent-9',
      first_name: 'Ola',
      last_name: 'Smith',
      name: 'Ola Smith',
      relationship_type: 'father',
      ticket: 'none',
      ticket_type: 'none',
      checkedIn: false
    };
    const family: Family = { ...mockFamilies[0], children: [noTicketChild], parents: [noTicketAdult] };

    it('states why, for a child, and offers both tickets in the same blue', async () => {
      const user = userEvent.setup();
      render(CheckinExpandableTable, { props: { ...defaultProps, families: [family], expandedChildId: 'child-9' } });
      await user.click(screen.getAllByTestId('family-toggle-button-family-1')[0]);

      const panel = screen.getAllByTestId('grant-ticket-panel-child-9')[0];
      expect(panel).toHaveTextContent('This session requires a ticket for children. Check in Nils Smith with:');
      const session = within(panel).getByTestId('ticket-assign-session-child-9');
      const event = within(panel).getByTestId('ticket-assign-event-child-9');
      expect(session.className).toContain('bg-primary-600');
      expect(event.className).toContain('bg-primary-600');
      expect(event.className).not.toContain('success');
    });

    it('says adults, not children, for an adult', async () => {
      const user = userEvent.setup();
      render(CheckinExpandableTable, { props: { ...defaultProps, families: [family], expandedChildId: 'parent-9' } });
      await user.click(screen.getAllByTestId('family-toggle-button-family-1')[0]);

      expect(screen.getAllByTestId('grant-ticket-panel-parent-9')[0]).toHaveTextContent(
        'This session requires a ticket for adults. Check in Ola Smith with:'
      );
    });

    it('assigns the chosen ticket in one tap', async () => {
      const user = userEvent.setup();
      const onAssignTicket = vi.fn();
      render(CheckinExpandableTable, {
        props: { ...defaultProps, families: [family], expandedChildId: 'child-9', onAssignTicket }
      });
      await user.click(screen.getAllByTestId('family-toggle-button-family-1')[0]);
      await user.click(screen.getAllByTestId('ticket-assign-event-child-9')[0]);
      expect(onAssignTicket).toHaveBeenCalledWith('family-1', 'child-9', 'event');
    });

    it('says "No Ticket" once on the row (the chip), not again as a subtitle', async () => {
      const user = userEvent.setup();
      render(CheckinExpandableTable, { props: { ...defaultProps, families: [family] } });
      await user.click(screen.getAllByTestId('family-toggle-button-family-1')[0]);

      for (const row of screen.getAllByTestId('child-row-child-9')) {
        expect(within(row).getAllByText('No Ticket')).toHaveLength(1);
      }
      for (const row of screen.getAllByTestId('parent-row-parent-9')) {
        expect(within(row).getAllByText('No Ticket')).toHaveLength(1);
      }
    });

    it('draws the chip chevron as an inline stroke icon, not a text glyph', async () => {
      const user = userEvent.setup();
      render(CheckinExpandableTable, { props: { ...defaultProps, families: [family] } });
      await user.click(screen.getAllByTestId('family-toggle-button-family-1')[0]);

      const chip = screen.getAllByTestId('child-expand-button-child-9')[0];
      expect(chip.textContent).not.toMatch(/[▲▼]/);
      const svg = chip.querySelector('svg');
      expect(svg).not.toBeNull();
      expect(svg).toHaveAttribute('stroke', 'currentColor');
      expect(svg).toHaveAttribute('stroke-width', '2');
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty families array', () => {
      render(CheckinExpandableTable, {
        props: { ...defaultProps, families: [] }
      });

      expect(screen.queryByTestId(/family-card/)).not.toBeInTheDocument();
    });

    it('should show adult count for a child-less family with parents', () => {
      const emptyFamily: Family[] = [
        {
          ...mockFamilies[0],
          children: []
        }
      ];

      render(CheckinExpandableTable, {
        props: { ...defaultProps, families: emptyFamily }
      });

      // mockFamilies[0] has exactly one parent — falls back to the adult
      // count instead of "0 children" now that all-adult households are supported.
      expect(screen.getAllByText(/1 adult/i).length).toBeGreaterThan(0);
      expect(screen.queryByText(/0 children/i)).not.toBeInTheDocument();
    });

    it('should handle a fully empty family (no children, no parents)', () => {
      const emptyFamily: Family[] = [
        {
          ...mockFamilies[0],
          children: [],
          parents: []
        }
      ];

      render(CheckinExpandableTable, {
        props: { ...defaultProps, families: emptyFamily }
      });

      // Neither branch has anything to count — should render without crashing.
      expect(screen.getAllByTestId(/family-card/).length).toBeGreaterThan(0);
    });
  });

  describe('Pending Payment', () => {
    const familyWithPendingPayment: Family[] = [
      {
        ...mockFamilies[0],
        pending_payment: {
          registration_id: 'reg-1',
          reference_code: 'ABC123',
          amount_owed: '1500.00',
          currency: 'SEK'
        }
      }
    ];

    async function expandFamily(user: ReturnType<typeof userEvent.setup>) {
      const toggleButtons = screen.getAllByTestId('family-toggle-button-family-1');
      await user.click(toggleButtons[0]);
    }

    it('does not render the banner when there is no pending payment', () => {
      render(CheckinExpandableTable, { props: defaultProps });

      expect(screen.queryByText(/Unpaid registration/i)).not.toBeInTheDocument();
    });

    it('shows the "awaiting payment" badge on the collapsed family row instead of a check-in button', () => {
      render(CheckinExpandableTable, {
        props: { ...defaultProps, families: familyWithPendingPayment }
      });

      expect(screen.getAllByText('Awaiting payment').length).toBeGreaterThan(0);
      expect(screen.queryByTestId('family-check-in-button-family-1')).not.toBeInTheDocument();
    });

    it('does not render the banner while the family is collapsed', () => {
      render(CheckinExpandableTable, {
        props: { ...defaultProps, families: familyWithPendingPayment }
      });

      expect(screen.queryByText(/Unpaid registration/i)).not.toBeInTheDocument();
      expect(
        screen.queryByTestId('pending-payment-banner-family-1')
      ).not.toBeInTheDocument();
    });

    it('renders the unpaid banner with the amount owed once expanded', async () => {
      const user = userEvent.setup();
      render(CheckinExpandableTable, {
        props: { ...defaultProps, families: familyWithPendingPayment }
      });

      await expandFamily(user);

      expect(
        screen.getAllByText('Unpaid registration — 1500.00 SEK owed').length
      ).toBeGreaterThan(0);
    });

    it('disables individual check-in buttons for a family with a pending payment', async () => {
      const user = userEvent.setup();
      const onCheckInChild = vi.fn();
      render(CheckinExpandableTable, {
        props: { ...defaultProps, families: familyWithPendingPayment, onCheckInChild }
      });

      await expandFamily(user);

      const unpaidButtons = screen.getAllByText('Unpaid');
      expect(unpaidButtons.length).toBeGreaterThan(0);
      for (const button of unpaidButtons) {
        expect(button).toBeDisabled();
      }
      expect(screen.queryByTestId('child-check-in-button-child-1')).not.toBeInTheDocument();

      await user.click(unpaidButtons[0]);
      expect(onCheckInChild).not.toHaveBeenCalled();
    });

    it('calls onMarkPaid with the registration id and method when a payment button is clicked', async () => {
      const user = userEvent.setup();
      const onMarkPaid = vi.fn().mockResolvedValue(undefined);

      render(CheckinExpandableTable, {
        props: { ...defaultProps, families: familyWithPendingPayment, onMarkPaid }
      });

      await expandFamily(user);

      const swishButtons = screen.getAllByText('Swish');
      await user.click(swishButtons[0]);

      expect(onMarkPaid).toHaveBeenCalledWith('reg-1', 'swish');
    });

    it('calls onConfirmDespiteBalance after staff confirms the override dialog', async () => {
      const user = userEvent.setup();
      const onConfirmDespiteBalance = vi.fn().mockResolvedValue(undefined);
      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);

      render(CheckinExpandableTable, {
        props: {
          ...defaultProps,
          families: familyWithPendingPayment,
          onConfirmDespiteBalance
        }
      });

      await expandFamily(user);

      const overrideButtons = screen.getAllByText('Let in, settle payment later');
      await user.click(overrideButtons[0]);

      expect(confirmSpy).toHaveBeenCalled();
      expect(onConfirmDespiteBalance).toHaveBeenCalledWith('reg-1');

      confirmSpy.mockRestore();
    });

    it('does not call onConfirmDespiteBalance when staff cancels the override dialog', async () => {
      const user = userEvent.setup();
      const onConfirmDespiteBalance = vi.fn().mockResolvedValue(undefined);
      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false);

      render(CheckinExpandableTable, {
        props: {
          ...defaultProps,
          families: familyWithPendingPayment,
          onConfirmDespiteBalance
        }
      });

      await expandFamily(user);

      const overrideButtons = screen.getAllByText('Let in, settle payment later');
      await user.click(overrideButtons[0]);

      expect(onConfirmDespiteBalance).not.toHaveBeenCalled();

      confirmSpy.mockRestore();
    });
  });

  describe('Edit family trigger', () => {
    it('does not render an edit button when onEditFamily is not provided', () => {
      render(CheckinExpandableTable, { props: defaultProps });

      expect(screen.queryAllByTestId('family-edit-button-family-1')).toHaveLength(0);
    });

    it('renders an edit button and calls onEditFamily with the family id when clicked', async () => {
      const user = userEvent.setup();
      const onEditFamily = vi.fn();
      render(CheckinExpandableTable, { props: { ...defaultProps, onEditFamily } });

      const editButtons = screen.getAllByTestId('family-edit-button-family-1');
      expect(editButtons.length).toBeGreaterThan(0);
      await user.click(editButtons[0]);

      expect(onEditFamily).toHaveBeenCalledWith('family-1');
    });

    it('clicking the edit button does not also toggle the family row expansion', async () => {
      const user = userEvent.setup();
      const onEditFamily = vi.fn();
      render(CheckinExpandableTable, { props: { ...defaultProps, onEditFamily } });

      const editButtons = screen.getAllByTestId('family-edit-button-family-1');
      await user.click(editButtons[0]);

      // Still collapsed — a click on the nested edit button must not also
      // bubble into toggleFamily's expand/collapse handler.
      expect(screen.queryByText('John Smith')).not.toBeInTheDocument();
    });
  });
});
