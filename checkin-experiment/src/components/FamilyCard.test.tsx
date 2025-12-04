import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FamilyCard } from './FamilyCard';
import type { Family } from '../types';

describe('FamilyCard', () => {
  const mockFamily: Family = {
    id: 1,
    name: 'Garcia',
    children: [
      {
        id: 1,
        name: 'Isabella Garcia',
        ticket: 'event',
        checkedIn: false,
      },
      {
        id: 2,
        name: 'Lucas Garcia',
        ticket: 'session',
        checkedIn: false,
      },
    ],
  };

  it('should render family name and children count', () => {
    render(
      <FamilyCard
        family={mockFamily}
        expanded={false}
        onToggle={vi.fn()}
        onCheckInChild={vi.fn()}
        onCheckInFamily={vi.fn()}
        onUndoChild={vi.fn()}
        onUndoFamily={vi.fn()}
        onAssignTicket={vi.fn()}
        expandedChildId={null}
        onToggleChildExpansion={vi.fn()}
        getRemainingTime={vi.fn()}
        familyUndoSeconds={null}
      />
    );

    expect(screen.getByText(/garcia family/i)).toBeInTheDocument();
    expect(screen.getByText(/2 children/i)).toBeInTheDocument();
  });

  it('should show Check In Family button when children have tickets and are not checked in', () => {
    render(
      <FamilyCard
        family={mockFamily}
        expanded={false}
        onToggle={vi.fn()}
        onCheckInChild={vi.fn()}
        onCheckInFamily={vi.fn()}
        onUndoChild={vi.fn()}
        onUndoFamily={vi.fn()}
        onAssignTicket={vi.fn()}
        expandedChildId={null}
        onToggleChildExpansion={vi.fn()}
        getRemainingTime={vi.fn()}
        familyUndoSeconds={null}
      />
    );

    const button = screen.getByRole('button', { name: /check in.*children/i });
    expect(button).toBeInTheDocument();
    expect(button.textContent).toMatch(/Check In Family/i);
  });

  it('should not show Check In Family button when any child has no ticket', () => {
    const familyWithNoTicket: Family = {
      ...mockFamily,
      children: [
        ...mockFamily.children,
        { id: 3, name: 'Noah', ticket: 'none', checkedIn: false },
      ],
    };

    render(
      <FamilyCard
        family={familyWithNoTicket}
        expanded={false}
        onToggle={vi.fn()}
        onCheckInChild={vi.fn()}
        onCheckInFamily={vi.fn()}
        onUndoChild={vi.fn()}
        onUndoFamily={vi.fn()}
        onAssignTicket={vi.fn()}
        expandedChildId={null}
        onToggleChildExpansion={vi.fn()}
        getRemainingTime={vi.fn()}
        familyUndoSeconds={null}
      />
    );

    expect(screen.queryByRole('button', { name: /check in family/i })).not.toBeInTheDocument();
  });

  it('should show Undo Family button when family undo is active', () => {
    render(
      <FamilyCard
        family={mockFamily}
        expanded={false}
        onToggle={vi.fn()}
        onCheckInChild={vi.fn()}
        onCheckInFamily={vi.fn()}
        onUndoChild={vi.fn()}
        onUndoFamily={vi.fn()}
        onAssignTicket={vi.fn()}
        expandedChildId={null}
        onToggleChildExpansion={vi.fn()}
        getRemainingTime={vi.fn()}
        familyUndoSeconds={28}
      />
    );

    expect(screen.getByRole('button', { name: /undo family.*28/i })).toBeInTheDocument();
  });

  it('should show All Checked In when all children are checked in and no undo active', () => {
    const allCheckedFamily: Family = {
      ...mockFamily,
      children: mockFamily.children.map((c) => ({ ...c, checkedIn: true })),
    };

    render(
      <FamilyCard
        family={allCheckedFamily}
        expanded={false}
        onToggle={vi.fn()}
        onCheckInChild={vi.fn()}
        onCheckInFamily={vi.fn()}
        onUndoChild={vi.fn()}
        onUndoFamily={vi.fn()}
        onAssignTicket={vi.fn()}
        expandedChildId={null}
        onToggleChildExpansion={vi.fn()}
        getRemainingTime={vi.fn()}
        familyUndoSeconds={null}
      />
    );

    expect(screen.getByText(/all checked in/i)).toBeInTheDocument();
  });

  it('should show children when expanded', () => {
    render(
      <FamilyCard
        family={mockFamily}
        expanded={true}
        onToggle={vi.fn()}
        onCheckInChild={vi.fn()}
        onCheckInFamily={vi.fn()}
        onUndoChild={vi.fn()}
        onUndoFamily={vi.fn()}
        onAssignTicket={vi.fn()}
        expandedChildId={null}
        onToggleChildExpansion={vi.fn()}
        getRemainingTime={vi.fn()}
        familyUndoSeconds={null}
      />
    );

    expect(screen.getByText('Isabella Garcia')).toBeInTheDocument();
    expect(screen.getByText('Lucas Garcia')).toBeInTheDocument();
  });

  it('should not show children when collapsed', () => {
    render(
      <FamilyCard
        family={mockFamily}
        expanded={false}
        onToggle={vi.fn()}
        onCheckInChild={vi.fn()}
        onCheckInFamily={vi.fn()}
        onUndoChild={vi.fn()}
        onUndoFamily={vi.fn()}
        onAssignTicket={vi.fn()}
        expandedChildId={null}
        onToggleChildExpansion={vi.fn()}
        getRemainingTime={vi.fn()}
        familyUndoSeconds={null}
      />
    );

    expect(screen.queryByText('Isabella Garcia')).not.toBeInTheDocument();
    expect(screen.queryByText('Lucas Garcia')).not.toBeInTheDocument();
  });

  it('should call onToggle when collapse/expand button clicked', async () => {
    const user = userEvent.setup();
    const mockOnToggle = vi.fn();

    render(
      <FamilyCard
        family={mockFamily}
        expanded={false}
        onToggle={mockOnToggle}
        onCheckInChild={vi.fn()}
        onCheckInFamily={vi.fn()}
        onUndoChild={vi.fn()}
        onUndoFamily={vi.fn()}
        onAssignTicket={vi.fn()}
        expandedChildId={null}
        onToggleChildExpansion={vi.fn()}
        getRemainingTime={vi.fn()}
        familyUndoSeconds={null}
      />
    );

    const toggleButton = screen.getByRole('button', { name: /toggle/i });
    await user.click(toggleButton);

    expect(mockOnToggle).toHaveBeenCalledTimes(1);
  });

  it('should call onCheckInFamily when Check In Family button clicked', async () => {
    const user = userEvent.setup();
    const mockOnCheckInFamily = vi.fn();

    render(
      <FamilyCard
        family={mockFamily}
        expanded={false}
        onToggle={vi.fn()}
        onCheckInChild={vi.fn()}
        onCheckInFamily={mockOnCheckInFamily}
        onUndoChild={vi.fn()}
        onUndoFamily={vi.fn()}
        onAssignTicket={vi.fn()}
        expandedChildId={null}
        onToggleChildExpansion={vi.fn()}
        getRemainingTime={vi.fn()}
        familyUndoSeconds={null}
      />
    );

    const checkInButton = screen.getByRole('button', { name: /check in.*children/i });
    await user.click(checkInButton);

    expect(mockOnCheckInFamily).toHaveBeenCalledTimes(1);
  });

  it('should call onUndoFamily when Undo Family button clicked', async () => {
    const user = userEvent.setup();
    const mockOnUndoFamily = vi.fn();

    render(
      <FamilyCard
        family={mockFamily}
        expanded={false}
        onToggle={vi.fn()}
        onCheckInChild={vi.fn()}
        onCheckInFamily={vi.fn()}
        onUndoChild={vi.fn()}
        onUndoFamily={mockOnUndoFamily}
        onAssignTicket={vi.fn()}
        expandedChildId={null}
        onToggleChildExpansion={vi.fn()}
        getRemainingTime={vi.fn()}
        familyUndoSeconds={25}
      />
    );

    const undoButton = screen.getByRole('button', { name: /undo family/i });
    await user.click(undoButton);

    expect(mockOnUndoFamily).toHaveBeenCalledTimes(1);
  });

  it('should display ticket types for children', () => {
    render(
      <FamilyCard
        family={mockFamily}
        expanded={true}
        onToggle={vi.fn()}
        onCheckInChild={vi.fn()}
        onCheckInFamily={vi.fn()}
        onUndoChild={vi.fn()}
        onUndoFamily={vi.fn()}
        onAssignTicket={vi.fn()}
        expandedChildId={null}
        onToggleChildExpansion={vi.fn()}
        getRemainingTime={vi.fn()}
        familyUndoSeconds={null}
      />
    );

    expect(screen.getByText(/event pass/i)).toBeInTheDocument();
    expect(screen.getByText(/session ticket/i)).toBeInTheDocument();
  });

  it('should display checked in count', () => {
    const partiallyChecked: Family = {
      ...mockFamily,
      children: [
        { ...mockFamily.children[0], checkedIn: true, checkInTime: '9:15 AM' },
        mockFamily.children[1],
      ],
    };

    render(
      <FamilyCard
        family={partiallyChecked}
        expanded={false}
        onToggle={vi.fn()}
        onCheckInChild={vi.fn()}
        onCheckInFamily={vi.fn()}
        onUndoChild={vi.fn()}
        onUndoFamily={vi.fn()}
        onAssignTicket={vi.fn()}
        expandedChildId={null}
        onToggleChildExpansion={vi.fn()}
        getRemainingTime={vi.fn()}
        familyUndoSeconds={null}
      />
    );

    expect(screen.getByText(/1 checked in/i)).toBeInTheDocument();
  });

  it('should show ticket assignment expansion when child without ticket is expanded', () => {
    const familyWithNoTicket: Family = {
      ...mockFamily,
      children: [
        { id: 3, name: 'Noah Garcia', ticket: 'none', checkedIn: false },
      ],
    };

    render(
      <FamilyCard
        family={familyWithNoTicket}
        expanded={true}
        onToggle={vi.fn()}
        onCheckInChild={vi.fn()}
        onCheckInFamily={vi.fn()}
        onUndoChild={vi.fn()}
        onUndoFamily={vi.fn()}
        onAssignTicket={vi.fn()}
        expandedChildId={3}
        onToggleChildExpansion={vi.fn()}
        getRemainingTime={vi.fn()}
        familyUndoSeconds={null}
      />
    );

    expect(screen.getByText(/check in.*noah garcia.*with:/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /session only/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /full event pass/i })).toBeInTheDocument();
  });

  it('should call onAssignTicket when ticket type selected in expansion', async () => {
    const user = userEvent.setup();
    const mockOnAssignTicket = vi.fn();
    const familyWithNoTicket: Family = {
      ...mockFamily,
      children: [
        { id: 3, name: 'Noah Garcia', ticket: 'none', checkedIn: false },
      ],
    };

    render(
      <FamilyCard
        family={familyWithNoTicket}
        expanded={true}
        onToggle={vi.fn()}
        onCheckInChild={vi.fn()}
        onCheckInFamily={vi.fn()}
        onUndoChild={vi.fn()}
        onUndoFamily={vi.fn()}
        onAssignTicket={mockOnAssignTicket}
        expandedChildId={3}
        onToggleChildExpansion={vi.fn()}
        getRemainingTime={vi.fn()}
        familyUndoSeconds={null}
      />
    );

    const sessionButton = screen.getByRole('button', { name: /session only/i });
    await user.click(sessionButton);

    expect(mockOnAssignTicket).toHaveBeenCalledWith(3, 'session');
  });
});
