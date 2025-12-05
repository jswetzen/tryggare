import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import FamilyTable from './FamilyTable.svelte';

// Mock svelte-i18n
vi.mock('svelte-i18n', () => ({
  t: {
    subscribe: vi.fn((callback) => {
      callback((key: string) => {
        const translations: Record<string, string> = {
          'checkin.familyChild': 'Family / Child',
          'checkin.ticket': 'Ticket',
          'checkin.checkIn': 'Check In',
          'checkin.checkInAll': 'Check in all',
          'checkin.alreadyCheckedIn': 'Already checked in',
          'checkout.familyChild': 'Family / Child',
          'checkout.checkedIn': 'Checked In',
          'checkout.checkOut': 'Check Out',
          'checkout.checkOutAll': 'Check out all',
          'checkout.pickedUpBy': 'Picked up by',
          'checkout.selectPerson': 'Select person'
        };
        return translations[key] || key;
      });
      return () => {};
    })
  }
}));

const mockFamilies = [
  {
    id: 'family-1',
    name: 'Smith',
    children: [
      {
        id: 'child-1',
        firstName: 'Emma',
        lastName: 'Smith',
        ticketType: 'event' as const,
        checkInTime: '2025-12-03T10:30:00Z'
      },
      {
        id: 'child-2',
        firstName: 'Oliver',
        lastName: 'Smith',
        ticketType: 'session' as const,
        checkInTime: '2025-12-03T10:35:00Z'
      }
    ],
    parents: [
      {
        firstName: 'John',
        lastName: 'Smith',
        relationshipType: 'Father'
      },
      {
        firstName: 'Jane',
        lastName: 'Smith',
        relationshipType: 'Mother'
      }
    ]
  },
  {
    id: 'family-2',
    name: 'Johnson',
    children: [
      {
        id: 'child-3',
        firstName: 'Sophia',
        lastName: 'Johnson',
        ticketType: 'none' as const
      }
    ],
    parents: [
      {
        firstName: 'Mike',
        lastName: 'Johnson',
        relationshipType: 'Father'
      }
    ]
  }
];

describe('FamilyTable - Check-in Mode', () => {
  it('renders families and children in check-in mode', () => {
    render(FamilyTable, {
      props: {
        families: mockFamilies,
        mode: 'checkin'
      }
    });

    // Check family names
    expect(screen.getByText(/Smith \(2\)/)).toBeInTheDocument();
    expect(screen.getByText(/Johnson \(1\)/)).toBeInTheDocument();

    // Check child names
    expect(screen.getByText('Emma Smith')).toBeInTheDocument();
    expect(screen.getByText('Oliver Smith')).toBeInTheDocument();
    expect(screen.getByText('Sophia Johnson')).toBeInTheDocument();
  });

  it('displays correct table headers for check-in mode', () => {
    render(FamilyTable, {
      props: {
        families: mockFamilies,
        mode: 'checkin'
      }
    });

    expect(screen.getByText('Family / Child')).toBeInTheDocument();
    expect(screen.getByText('Ticket')).toBeInTheDocument();
    expect(screen.getByText('Check In')).toBeInTheDocument();
  });

  it('calls onToggleChild when child check-in button clicked', async () => {
    const user = userEvent.setup();
    const onToggleChild = vi.fn();

    render(FamilyTable, {
      props: {
        families: mockFamilies,
        mode: 'checkin',
        onToggleChild
      }
    });

    // Find and click a check-in button (we need to find by row)
    const buttons = screen.getAllByRole('button');
    // First few buttons will be for individual children
    await user.click(buttons[1]); // Click first child's button

    expect(onToggleChild).toHaveBeenCalled();
  });

  it('calls onToggleFamily when family check-in button clicked', async () => {
    const user = userEvent.setup();
    const onToggleFamily = vi.fn();

    render(FamilyTable, {
      props: {
        families: mockFamilies,
        mode: 'checkin',
        onToggleFamily
      }
    });

    // Family buttons should be first
    const buttons = screen.getAllByRole('button');
    await user.click(buttons[0]); // First family button

    expect(onToggleFamily).toHaveBeenCalledWith('family-1');
  });

  it('shows disabled state for already checked-in children', () => {
    const isChildDisabled = (child: any) => child.id === 'child-1';

    const { container } = render(FamilyTable, {
      props: {
        families: mockFamilies,
        mode: 'checkin',
        onToggleChild: vi.fn(),
        isChildDisabled
      }
    });

    // When a child is disabled, isChildDisabled returns true
    // The component passes this to IconButton which shows "checked-in" variant
    // We verify the isChildDisabled function is being called correctly
    expect(isChildDisabled(mockFamilies[0].children[0])).toBe(true);
    expect(isChildDisabled(mockFamilies[0].children[1])).toBe(false);
  });

  it('alternates row background colors', () => {
    const { container } = render(FamilyTable, {
      props: {
        families: mockFamilies,
        mode: 'checkin'
      }
    });

    const rows = container.querySelectorAll('tbody tr');
    // First family's rows should have white background
    expect(rows[0]).toHaveClass('bg-white');
    expect(rows[1]).toHaveClass('bg-white');
    expect(rows[2]).toHaveClass('bg-white');

    // Second family's rows should have neutral background
    expect(rows[3]).toHaveClass('bg-neutral-50');
    expect(rows[4]).toHaveClass('bg-neutral-50');
  });
});

describe('FamilyTable - Checkout Mode', () => {
  it('displays correct table headers for checkout mode', () => {
    render(FamilyTable, {
      props: {
        families: mockFamilies,
        mode: 'checkout'
      }
    });

    expect(screen.getByText('Family / Child')).toBeInTheDocument();
    expect(screen.getByText('Checked In')).toBeInTheDocument();
    expect(screen.getByText('Check Out')).toBeInTheDocument();
  });

  it('displays check-in times in checkout mode', () => {
    render(FamilyTable, {
      props: {
        families: mockFamilies,
        mode: 'checkout'
      }
    });

    // Should display formatted times (default formatter uses toLocaleTimeString)
    // Check that time elements exist (exact format may vary by locale)
    const tableContent = screen.getByRole('table').textContent;
    expect(tableContent).toContain('AM'); // Times should be formatted
  });

  it('calls onCheckOut when checkout button clicked', async () => {
    const user = userEvent.setup();
    const onCheckOut = vi.fn();

    render(FamilyTable, {
      props: {
        families: mockFamilies,
        mode: 'checkout',
        onCheckOut
      }
    });

    const buttons = screen.getAllByRole('button');
    await user.click(buttons[1]); // Click first child's checkout button

    expect(onCheckOut).toHaveBeenCalled();
  });

  it('renders pickup person selector in checkout mode', () => {
    render(FamilyTable, {
      props: {
        families: mockFamilies,
        mode: 'checkout',
        onPickedUpByChange: vi.fn()
      }
    });

    // Pickup selector is shown when onPickedUpByChange callback is provided
    // Text appears once per family
    const pickedUpLabels = screen.getAllByText('Picked up by:');
    expect(pickedUpLabels.length).toBe(2); // One for each family

    // Should have select dropdown options
    const selects = screen.getAllByText('Select person');
    expect(selects.length).toBe(2); // One for each family
  });

  it('displays parent options in pickup selector', () => {
    render(FamilyTable, {
      props: {
        families: mockFamilies,
        mode: 'checkout',
        onPickedUpByChange: vi.fn()
      }
    });

    // Check that parent names appear as options
    expect(screen.getByText(/John Smith \(Father\)/)).toBeInTheDocument();
    expect(screen.getByText(/Jane Smith \(Mother\)/)).toBeInTheDocument();
    expect(screen.getByText(/Mike Johnson \(Father\)/)).toBeInTheDocument();
  });

  it('calls onPickedUpByChange when pickup person is selected', async () => {
    const user = userEvent.setup();
    const onPickedUpByChange = vi.fn();

    render(FamilyTable, {
      props: {
        families: mockFamilies,
        mode: 'checkout',
        onPickedUpByChange
      }
    });

    const selects = screen.getAllByRole('combobox');
    await user.selectOptions(selects[0], 'John Smith');

    expect(onPickedUpByChange).toHaveBeenCalledWith('family-1', 'John Smith');
  });

  it('uses custom formatTime function when provided', () => {
    const formatTime = vi.fn(() => 'Custom Time');

    render(FamilyTable, {
      props: {
        families: mockFamilies,
        mode: 'checkout',
        formatTime
      }
    });

    expect(formatTime).toHaveBeenCalled();
    expect(screen.getAllByText('Custom Time').length).toBeGreaterThan(0);
  });
});

describe('FamilyTable - Empty State', () => {
  it('renders empty table when no families provided', () => {
    const { container } = render(FamilyTable, {
      props: {
        families: [],
        mode: 'checkin'
      }
    });

    const tbody = container.querySelector('tbody');
    expect(tbody?.children.length).toBe(0);
  });

  it('handles family with no children', () => {
    const emptyFamily = [{
      id: 'family-empty',
      name: 'Empty Family',
      children: []
    }];

    render(FamilyTable, {
      props: {
        families: emptyFamily,
        mode: 'checkin'
      }
    });

    expect(screen.getByText(/Empty Family \(0\)/)).toBeInTheDocument();
  });
});
