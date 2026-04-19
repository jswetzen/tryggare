/**
 * Tests for CheckinExpandableTable Component
 *
 * Note: This component renders both mobile and desktop layouts simultaneously (hidden with CSS),
 * so we use getAllBy* queries to handle multiple matching elements.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import CheckinExpandableTable from './CheckinExpandableTable.svelte';
import type { Family } from '$lib/checkin/types';

// Mock the i18n library
vi.mock('svelte-i18n', () => ({
  _: {
    subscribe: (fn: any) => {
      fn((key: string, options?: any) => {
        const translations: Record<string, string> = {
          'checkin.child': 'child',
          'checkin.children': 'children',
          'checkin.allCheckedIn': 'All Checked In',
          'checkin.alreadyCheckedIn': 'Already Checked In',
          'checkin.checkInCount': 'Check In {count}',
          'checkin.checkedInCount': '{count} checked in',
          'checkin.undoSeconds': 'Undo ({seconds}s)',
          'checkin.ticketEvent': 'Event',
          'checkin.ticketSession': 'Session',
          'checkin.ticketNone': 'No Ticket',
          'checkin.checkedInAt': 'Checked in at {time}',
          'checkin.guardianPresent': 'Guardian Present',
          'checkin.checkIn': 'Check In',
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
      parents: [{ id: 'parent-1', name: 'Bob Smith', relationship_type: 'father' }]
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

  describe('Edge Cases', () => {
    it('should handle empty families array', () => {
      render(CheckinExpandableTable, {
        props: { ...defaultProps, families: [] }
      });

      expect(screen.queryByTestId(/family-card/)).not.toBeInTheDocument();
    });

    it('should handle family with no children', () => {
      const emptyFamily: Family[] = [
        {
          ...mockFamilies[0],
          children: []
        }
      ];

      render(CheckinExpandableTable, {
        props: { ...defaultProps, families: emptyFamily }
      });

      expect(screen.getAllByText(/0 children/i).length).toBeGreaterThan(0);
    });
  });
});
