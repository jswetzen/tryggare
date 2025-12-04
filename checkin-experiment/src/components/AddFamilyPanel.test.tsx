import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AddFamilyPanel } from './AddFamilyPanel';

describe('AddFamilyPanel', () => {
  it('should render the panel with initial state', () => {
    const mockOnAdd = vi.fn();
    const mockOnClose = vi.fn();

    render(<AddFamilyPanel onAdd={mockOnAdd} onClose={mockOnClose} />);

    expect(screen.getByText('Add New Family')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/garcia.*smith/i)).toBeInTheDocument();
    expect(screen.getByRole('combobox')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/child.*1.*name/i)).toBeInTheDocument();
  });

  it('should have one child input by default', () => {
    const mockOnAdd = vi.fn();
    const mockOnClose = vi.fn();

    render(<AddFamilyPanel onAdd={mockOnAdd} onClose={mockOnClose} />);

    const childInputs = screen.getAllByPlaceholderText(/child.*name/i);
    expect(childInputs).toHaveLength(1);
  });

  it('should add more child inputs when clicking Add Child', async () => {
    const user = userEvent.setup();
    const mockOnAdd = vi.fn();
    const mockOnClose = vi.fn();

    render(<AddFamilyPanel onAdd={mockOnAdd} onClose={mockOnClose} />);

    const addChildButton = screen.getByRole('button', { name: /add child/i });

    await user.click(addChildButton);

    const childInputs = screen.getAllByPlaceholderText(/child.*name/i);
    expect(childInputs).toHaveLength(2);

    await user.click(addChildButton);

    const updatedInputs = screen.getAllByPlaceholderText(/child.*name/i);
    expect(updatedInputs).toHaveLength(3);
  });

  it('should remove child inputs except the first one', async () => {
    const user = userEvent.setup();
    const mockOnAdd = vi.fn();
    const mockOnClose = vi.fn();

    render(<AddFamilyPanel onAdd={mockOnAdd} onClose={mockOnClose} />);

    // Add two more children
    const addChildButton = screen.getByRole('button', { name: /add child/i });
    await user.click(addChildButton);
    await user.click(addChildButton);

    expect(screen.getAllByPlaceholderText(/child.*name/i)).toHaveLength(3);

    // Remove buttons should be present for children 2 and 3
    const removeButtons = screen.getAllByRole('button', { name: /remove/i });
    expect(removeButtons).toHaveLength(2);

    // Click first remove button
    await user.click(removeButtons[0]);

    expect(screen.getAllByPlaceholderText(/child.*name/i)).toHaveLength(2);
  });

  it('should not show remove button for the first child', () => {
    const mockOnAdd = vi.fn();
    const mockOnClose = vi.fn();

    render(<AddFamilyPanel onAdd={mockOnAdd} onClose={mockOnClose} />);

    const removeButtons = screen.queryAllByRole('button', { name: /remove/i });
    expect(removeButtons).toHaveLength(0);
  });

  it('should call onClose when clicking close button', async () => {
    const user = userEvent.setup();
    const mockOnAdd = vi.fn();
    const mockOnClose = vi.fn();

    render(<AddFamilyPanel onAdd={mockOnAdd} onClose={mockOnClose} />);

    const closeButton = screen.getByRole('button', { name: /close/i });
    await user.click(closeButton);

    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it('should call onClose when clicking Cancel', async () => {
    const user = userEvent.setup();
    const mockOnAdd = vi.fn();
    const mockOnClose = vi.fn();

    render(<AddFamilyPanel onAdd={mockOnAdd} onClose={mockOnClose} />);

    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    await user.click(cancelButton);

    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it('should not submit without family name', async () => {
    const user = userEvent.setup();
    const mockOnAdd = vi.fn();
    const mockOnClose = vi.fn();

    render(<AddFamilyPanel onAdd={mockOnAdd} onClose={mockOnClose} />);

    const addButton = screen.getByRole('button', { name: /add family$/i });
    await user.click(addButton);

    expect(mockOnAdd).not.toHaveBeenCalled();
    expect(screen.getByText(/family name is required/i)).toBeInTheDocument();
  });

  it('should not submit without at least one child name', async () => {
    const user = userEvent.setup();
    const mockOnAdd = vi.fn();
    const mockOnClose = vi.fn();

    render(<AddFamilyPanel onAdd={mockOnAdd} onClose={mockOnClose} />);

    const familyNameInput = screen.getByPlaceholderText(/garcia.*smith/i);
    await user.type(familyNameInput, 'Garcia');

    const addButton = screen.getByRole('button', { name: /add family$/i });
    await user.click(addButton);

    expect(mockOnAdd).not.toHaveBeenCalled();
    expect(
      screen.getByText(/at least one child name is required/i)
    ).toBeInTheDocument();
  });

  it('should submit with valid data', async () => {
    const user = userEvent.setup();
    const mockOnAdd = vi.fn();
    const mockOnClose = vi.fn();

    render(<AddFamilyPanel onAdd={mockOnAdd} onClose={mockOnClose} />);

    // Fill in family name
    const familyNameInput = screen.getByPlaceholderText(/garcia.*smith/i);
    await user.type(familyNameInput, 'Garcia');

    // Fill in child name
    const childInput = screen.getByPlaceholderText(/child.*1.*name/i);
    await user.type(childInput, 'Isabella');

    // Submit
    const addButton = screen.getByRole('button', { name: /add family$/i });
    await user.click(addButton);

    expect(mockOnAdd).toHaveBeenCalledTimes(1);
    expect(mockOnAdd).toHaveBeenCalledWith({
      familyName: 'Garcia',
      childrenNames: ['Isabella'],
      ticketType: 'none',
    });
  });

  it('should submit with multiple children', async () => {
    const user = userEvent.setup();
    const mockOnAdd = vi.fn();
    const mockOnClose = vi.fn();

    render(<AddFamilyPanel onAdd={mockOnAdd} onClose={mockOnClose} />);

    // Fill in family name
    const familyNameInput = screen.getByPlaceholderText(/garcia.*smith/i);
    await user.type(familyNameInput, 'Smith');

    // Add a second child
    const addChildButton = screen.getByRole('button', { name: /add child/i });
    await user.click(addChildButton);

    // Fill in child names
    const childInputs = screen.getAllByPlaceholderText(/child.*\d+.*name/i);
    await user.type(childInputs[0], 'Emma');
    await user.type(childInputs[1], 'Oliver');

    // Submit
    const addButton = screen.getByRole('button', { name: /add family$/i });
    await user.click(addButton);

    expect(mockOnAdd).toHaveBeenCalledWith({
      familyName: 'Smith',
      childrenNames: ['Emma', 'Oliver'],
      ticketType: 'none',
    });
  });

  it('should filter out empty child names', async () => {
    const user = userEvent.setup();
    const mockOnAdd = vi.fn();
    const mockOnClose = vi.fn();

    render(<AddFamilyPanel onAdd={mockOnAdd} onClose={mockOnClose} />);

    // Fill in family name
    const familyNameInput = screen.getByPlaceholderText(/garcia.*smith/i);
    await user.type(familyNameInput, 'Anderson');

    // Add two more children
    const addChildButton = screen.getByRole('button', { name: /add child/i });
    await user.click(addChildButton);
    await user.click(addChildButton);

    // Fill in only first and third child
    const childInputs = screen.getAllByPlaceholderText(/child.*\d+.*name/i);
    await user.type(childInputs[0], 'Liam');
    // Leave childInputs[1] empty
    await user.type(childInputs[2], 'Noah');

    // Submit
    const addButton = screen.getByRole('button', { name: /add family$/i });
    await user.click(addButton);

    expect(mockOnAdd).toHaveBeenCalledWith({
      familyName: 'Anderson',
      childrenNames: ['Liam', 'Noah'],
      ticketType: 'none',
    });
  });

  it('should allow selecting different ticket types', async () => {
    const user = userEvent.setup();
    const mockOnAdd = vi.fn();
    const mockOnClose = vi.fn();

    render(<AddFamilyPanel onAdd={mockOnAdd} onClose={mockOnClose} />);

    // Fill in family name
    const familyNameInput = screen.getByPlaceholderText(/garcia.*smith/i);
    await user.type(familyNameInput, 'Martinez');

    // Fill in child
    const childInput = screen.getByPlaceholderText(/child.*1.*name/i);
    await user.type(childInput, 'Sofia');

    // Select ticket type
    const ticketSelect = screen.getByRole('combobox');
    await user.selectOptions(ticketSelect, 'event');

    // Submit
    const addButton = screen.getByRole('button', { name: /add family$/i });
    await user.click(addButton);

    expect(mockOnAdd).toHaveBeenCalledWith({
      familyName: 'Martinez',
      childrenNames: ['Sofia'],
      ticketType: 'event',
    });
  });

  it('should close on Escape key', async () => {
    const user = userEvent.setup();
    const mockOnAdd = vi.fn();
    const mockOnClose = vi.fn();

    render(<AddFamilyPanel onAdd={mockOnAdd} onClose={mockOnClose} />);

    await user.keyboard('{Escape}');

    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it('should focus family name input on mount', () => {
    const mockOnAdd = vi.fn();
    const mockOnClose = vi.fn();

    render(<AddFamilyPanel onAdd={mockOnAdd} onClose={mockOnClose} />);

    const familyNameInput = screen.getByPlaceholderText(/garcia.*smith/i);
    expect(familyNameInput).toHaveFocus();
  });
});
