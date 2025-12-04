import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChildCheckInButton } from './ChildCheckInButton';
import type { Child } from '../types';

describe('ChildCheckInButton', () => {
  const mockChild: Child = {
    id: 1,
    name: 'Lucas Garcia',
    ticket: 'none',
    checkedIn: false,
  };

  it('should render Check In button for child with valid ticket', () => {
    const childWithTicket: Child = { ...mockChild, ticket: 'event' };
    const mockOnCheckIn = vi.fn();

    render(
      <ChildCheckInButton
        child={childWithTicket}
        onCheckIn={mockOnCheckIn}
        remainingSeconds={null}
      />
    );

    const button = screen.getByRole('button', { name: /check in/i });
    expect(button).toBeInTheDocument();
    expect(button).toHaveClass('bg-green-600');
  });

  it('should render Undo button with countdown when undo active', () => {
    const checkedChild: Child = { ...mockChild, checkedIn: true, ticket: 'event' };
    const mockOnUndo = vi.fn();

    render(
      <ChildCheckInButton
        child={checkedChild}
        onUndo={mockOnUndo}
        remainingSeconds={25}
      />
    );

    const button = screen.getByRole('button', { name: /undo.*25/i });
    expect(button).toBeInTheDocument();
    expect(button).toHaveClass('bg-orange-500');
  });

  it('should render Checked In button when undo period expired', () => {
    const checkedChild: Child = { ...mockChild, checkedIn: true, ticket: 'event', checkInTime: '9:15 AM' };

    render(
      <ChildCheckInButton
        child={checkedChild}
        remainingSeconds={null}
      />
    );

    const button = screen.getByRole('button', { name: /checked in/i });
    expect(button).toBeInTheDocument();
    expect(button).toBeDisabled();
    expect(button).toHaveClass('bg-slate-400');
  });

  it('should render No Ticket button for child without ticket', () => {
    const mockOnNoTicketClick = vi.fn();

    render(
      <ChildCheckInButton
        child={mockChild}
        onNoTicketClick={mockOnNoTicketClick}
        remainingSeconds={null}
      />
    );

    const button = screen.getByRole('button', { name: /no ticket/i });
    expect(button).toBeInTheDocument();
    expect(button).toHaveClass('bg-red-100');
  });

  it('should render No Ticket button with down arrow when not expanded', () => {
    const mockOnNoTicketClick = vi.fn();

    render(
      <ChildCheckInButton
        child={mockChild}
        onNoTicketClick={mockOnNoTicketClick}
        expanded={false}
        remainingSeconds={null}
      />
    );

    const button = screen.getByRole('button', { name: /no ticket/i });
    expect(button.textContent).toContain('▼');
  });

  it('should render No Ticket button with up arrow when expanded', () => {
    const mockOnNoTicketClick = vi.fn();

    render(
      <ChildCheckInButton
        child={mockChild}
        onNoTicketClick={mockOnNoTicketClick}
        expanded={true}
        remainingSeconds={null}
      />
    );

    const button = screen.getByRole('button', { name: /no ticket/i });
    expect(button.textContent).toContain('▲');
  });

  it('should call onCheckIn when Check In button clicked', async () => {
    const user = userEvent.setup();
    const childWithTicket: Child = { ...mockChild, ticket: 'event' };
    const mockOnCheckIn = vi.fn();

    render(
      <ChildCheckInButton
        child={childWithTicket}
        onCheckIn={mockOnCheckIn}
        remainingSeconds={null}
      />
    );

    const button = screen.getByRole('button', { name: /check in/i });
    await user.click(button);

    expect(mockOnCheckIn).toHaveBeenCalledTimes(1);
  });

  it('should call onUndo when Undo button clicked', async () => {
    const user = userEvent.setup();
    const checkedChild: Child = { ...mockChild, checkedIn: true, ticket: 'event' };
    const mockOnUndo = vi.fn();

    render(
      <ChildCheckInButton
        child={checkedChild}
        onUndo={mockOnUndo}
        remainingSeconds={25}
      />
    );

    const button = screen.getByRole('button', { name: /undo/i });
    await user.click(button);

    expect(mockOnUndo).toHaveBeenCalledTimes(1);
  });

  it('should call onNoTicketClick when No Ticket button clicked', async () => {
    const user = userEvent.setup();
    const mockOnNoTicketClick = vi.fn();

    render(
      <ChildCheckInButton
        child={mockChild}
        onNoTicketClick={mockOnNoTicketClick}
        expanded={false}
        remainingSeconds={null}
      />
    );

    const button = screen.getByRole('button', { name: /no ticket/i });
    await user.click(button);

    expect(mockOnNoTicketClick).toHaveBeenCalledTimes(1);
  });
});
