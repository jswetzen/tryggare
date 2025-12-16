import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import ExpandableListTable from './ExpandableListTable.svelte';

describe('ExpandableListTable', () => {
  const mockItems = [
    {
      id: '1',
      name: 'Smith Family',
      count: 2,
      children: [
        { id: '1a', name: 'John Smith' },
        { id: '1b', name: 'Jane Smith' }
      ]
    },
    {
      id: '2',
      name: 'Johnson Family',
      count: 1,
      children: [
        { id: '2a', name: 'Bob Johnson' }
      ]
    }
  ];

  const mockColumns = [
    { key: 'name', label: 'Family' },
    { key: 'count', label: 'Count' }
  ];

  describe('Desktop Layout', () => {
    it('renders table on desktop view', () => {
      const { container } = render(ExpandableListTable, {
        props: {
          items: mockItems,
          columns: mockColumns
        }
      });

      // Should have desktop table
      const table = container.querySelector('table');
      expect(table).toBeInTheDocument();
    });

    it('renders column headers', () => {
      render(ExpandableListTable, {
        props: {
          items: mockItems,
          columns: mockColumns
        }
      });

      expect(screen.getByText('Family')).toBeInTheDocument();
      expect(screen.getByText('Count')).toBeInTheDocument();
    });

    it('applies sticky header styling', () => {
      const { container } = render(ExpandableListTable, {
        props: {
          items: mockItems,
          columns: mockColumns
        }
      });

      const thead = container.querySelector('thead');
      expect(thead).toHaveClass('sticky', 'top-0', 'bg-slate-50');
    });

    it('renders all items in collapsed state by default', () => {
      render(ExpandableListTable, {
        props: {
          items: mockItems,
          columns: mockColumns
        }
      });

      // Both mobile and desktop views are rendered, so use getAllByText
      expect(screen.getAllByText('Smith Family').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Johnson Family').length).toBeGreaterThan(0);

      // Children should not be visible initially
      expect(screen.queryByText('John Smith')).not.toBeInTheDocument();
      expect(screen.queryByText('Jane Smith')).not.toBeInTheDocument();
    });

    it('expands item when clicked', async () => {
      const user = userEvent.setup();
      const onToggleMock = vi.fn();
      const { container } = render(ExpandableListTable, {
        props: {
          items: mockItems,
          columns: mockColumns,
          onToggle: onToggleMock
        }
      });

      // Find the first row and click it
      const firstRow = container.querySelector('tbody tr');
      await user.click(firstRow as HTMLElement);

      // Verify expansion callback was called
      expect(onToggleMock).toHaveBeenCalledWith('1', true);

      // Check that the chevron changed to down arrow (expanded state)
      const chevronPath = container.querySelector('tbody tr svg path');
      expect(chevronPath).toHaveAttribute('d', 'M3 6l6 6 6-6'); // Down arrow
    });

    it('collapses expanded item when clicked again', async () => {
      const user = userEvent.setup();
      const onToggleMock = vi.fn();
      const { container } = render(ExpandableListTable, {
        props: {
          items: mockItems,
          columns: mockColumns,
          onToggle: onToggleMock
        }
      });

      const firstRow = container.querySelector('tbody tr');

      // Expand
      await user.click(firstRow as HTMLElement);
      expect(onToggleMock).toHaveBeenCalledWith('1', true);

      // Collapse
      await user.click(firstRow as HTMLElement);
      expect(onToggleMock).toHaveBeenCalledWith('1', false);

      // Check that the chevron changed back to right arrow (collapsed state)
      const chevronPath = container.querySelector('tbody tr svg path');
      expect(chevronPath).toHaveAttribute('d', 'M6 3l6 6-6 6'); // Right arrow
    });

    it('shows chevron icons for expandable state', () => {
      const { container } = render(ExpandableListTable, {
        props: {
          items: mockItems,
          columns: mockColumns
        }
      });

      // Should have chevron icons (SVG elements)
      const chevrons = container.querySelectorAll('svg');
      expect(chevrons.length).toBeGreaterThan(0);
    });

    it('applies hover effect to rows', () => {
      const { container } = render(ExpandableListTable, {
        props: {
          items: mockItems,
          columns: mockColumns
        }
      });

      const firstRow = container.querySelector('tbody tr');
      expect(firstRow).toHaveClass('hover:bg-slate-50');
    });
  });

  describe('Mobile Layout', () => {
    it('renders card layout on mobile', () => {
      const { container } = render(ExpandableListTable, {
        props: {
          items: mockItems,
          columns: mockColumns
        }
      });

      // Should have mobile cards container
      const mobileContainer = container.querySelector('.md\\:hidden');
      expect(mobileContainer).toBeInTheDocument();
    });

    it('renders items as cards', () => {
      const { container } = render(ExpandableListTable, {
        props: {
          items: mockItems,
          columns: mockColumns
        }
      });

      // Should have rounded cards with borders
      const cards = container.querySelectorAll('.rounded-lg.border-2.border-slate-300');
      expect(cards.length).toBeGreaterThanOrEqual(2);
    });
  });

  describe('Custom Rendering', () => {
    it('calls onToggle callback when item is expanded', async () => {
      const user = userEvent.setup();
      const onToggleMock = vi.fn();
      const { container } = render(ExpandableListTable, {
        props: {
          items: mockItems,
          columns: mockColumns,
          onToggle: onToggleMock
        }
      });

      const firstRow = container.querySelector('tbody tr');
      await user.click(firstRow as HTMLElement);

      expect(onToggleMock).toHaveBeenCalledWith('1', true);
    });

    it('calls onToggle with false when collapsing', async () => {
      const user = userEvent.setup();
      const onToggleMock = vi.fn();
      const { container } = render(ExpandableListTable, {
        props: {
          items: mockItems,
          columns: mockColumns,
          onToggle: onToggleMock
        }
      });

      const firstRow = container.querySelector('tbody tr');

      // Expand
      await user.click(firstRow as HTMLElement);
      expect(onToggleMock).toHaveBeenCalledWith('1', true);

      // Collapse
      await user.click(firstRow as HTMLElement);
      expect(onToggleMock).toHaveBeenCalledWith('1', false);
    });
  });

  describe('Keyboard Navigation', () => {
    it('makes rows keyboard accessible with tabindex', () => {
      const { container } = render(ExpandableListTable, {
        props: {
          items: mockItems,
          columns: mockColumns
        }
      });

      // Desktop view uses tr with tabindex
      const firstRow = container.querySelector('tbody tr');
      expect(firstRow).toHaveAttribute('tabindex', '0');
      expect(firstRow).toHaveAttribute('role', 'button');

      // Mobile view uses button element
      const mobileButton = container.querySelector('.md\\:hidden button');
      expect(mobileButton).toBeInTheDocument();
    });

    it('expands on Enter key press', async () => {
      const user = userEvent.setup();
      const onToggleMock = vi.fn();
      const { container } = render(ExpandableListTable, {
        props: {
          items: mockItems,
          columns: mockColumns,
          onToggle: onToggleMock
        }
      });

      const firstRow = container.querySelector('tbody tr') as HTMLElement;
      firstRow.focus();
      await user.keyboard('{Enter}');

      expect(onToggleMock).toHaveBeenCalledWith('1', true);
    });

    it('expands on Space key press', async () => {
      const user = userEvent.setup();
      const onToggleMock = vi.fn();
      const { container } = render(ExpandableListTable, {
        props: {
          items: mockItems,
          columns: mockColumns,
          onToggle: onToggleMock
        }
      });

      const firstRow = container.querySelector('tbody tr') as HTMLElement;
      firstRow.focus();
      await user.keyboard(' ');

      expect(onToggleMock).toHaveBeenCalledWith('1', true);
    });
  });

  describe('Styling and Colors', () => {
    it('uses slate color palette', () => {
      const { container } = render(ExpandableListTable, {
        props: {
          items: mockItems,
          columns: mockColumns
        }
      });

      // Check for slate colors in borders and backgrounds
      const tableContainer = container.querySelector('.border-slate-300');
      expect(tableContainer).toBeInTheDocument();

      const header = container.querySelector('.bg-slate-50');
      expect(header).toBeInTheDocument();
    });

    it('applies rounded corners to container', () => {
      const { container } = render(ExpandableListTable, {
        props: {
          items: mockItems,
          columns: mockColumns
        }
      });

      const tableContainer = container.querySelector('.rounded-lg');
      expect(tableContainer).toBeInTheDocument();
    });
  });

  describe('Empty State', () => {
    it('handles empty items array', () => {
      const { container } = render(ExpandableListTable, {
        props: {
          items: [],
          columns: mockColumns
        }
      });

      // Should still render table structure
      const table = container.querySelector('table');
      expect(table).toBeInTheDocument();
    });
  });
});
