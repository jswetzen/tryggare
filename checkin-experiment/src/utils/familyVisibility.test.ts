import { describe, it, expect } from 'vitest';
import { shouldShowFamily } from './familyVisibility';
import type { Family, UndoAction } from '../types';

describe('shouldShowFamily', () => {
  const mockFamily: Family = {
    id: 1,
    name: 'Garcia',
    children: [
      { id: 1, name: 'Isabella', ticket: 'event', checkedIn: false },
      { id: 2, name: 'Lucas', ticket: 'session', checkedIn: false },
    ],
  };

  it('should show family with unchecked children', () => {
    expect(shouldShowFamily(mockFamily, [])).toBe(true);
  });

  it('should hide family when all children are checked in and no undo active', () => {
    const allCheckedFamily: Family = {
      ...mockFamily,
      children: mockFamily.children.map((c) => ({ ...c, checkedIn: true })),
    };

    expect(shouldShowFamily(allCheckedFamily, [])).toBe(false);
  });

  it('should show family when all children checked in but undo active', () => {
    const allCheckedFamily: Family = {
      ...mockFamily,
      children: mockFamily.children.map((c) => ({ ...c, checkedIn: true })),
    };

    const activeUndoAction: UndoAction = {
      id: 'undo-1',
      familyId: 1,
      childIds: [1, 2],
      timestamp: Date.now(),
      expiresAt: Date.now() + 30000,
    };

    expect(shouldShowFamily(allCheckedFamily, [activeUndoAction])).toBe(true);
  });

  it('should show family with mix of checked and unchecked children', () => {
    const mixedFamily: Family = {
      ...mockFamily,
      children: [
        { ...mockFamily.children[0], checkedIn: true },
        mockFamily.children[1],
      ],
    };

    expect(shouldShowFamily(mixedFamily, [])).toBe(true);
  });

  it('should not show family when undo is for different family', () => {
    const allCheckedFamily: Family = {
      ...mockFamily,
      children: mockFamily.children.map((c) => ({ ...c, checkedIn: true })),
    };

    const undoForOtherFamily: UndoAction = {
      id: 'undo-1',
      familyId: 999, // Different family
      childIds: [1, 2],
      timestamp: Date.now(),
      expiresAt: Date.now() + 30000,
    };

    expect(shouldShowFamily(allCheckedFamily, [undoForOtherFamily])).toBe(false);
  });

  it('should show family when it has multiple undo actions', () => {
    const allCheckedFamily: Family = {
      ...mockFamily,
      children: mockFamily.children.map((c) => ({ ...c, checkedIn: true })),
    };

    const undoActions: UndoAction[] = [
      {
        id: 'undo-1',
        familyId: 1,
        childIds: [1],
        timestamp: Date.now(),
        expiresAt: Date.now() + 30000,
      },
      {
        id: 'undo-2',
        familyId: 1,
        childIds: [2],
        timestamp: Date.now(),
        expiresAt: Date.now() + 25000,
      },
    ];

    expect(shouldShowFamily(allCheckedFamily, undoActions)).toBe(true);
  });

  it('should handle empty children array', () => {
    const emptyFamily: Family = {
      id: 1,
      name: 'Empty',
      children: [],
    };

    expect(shouldShowFamily(emptyFamily, [])).toBe(false);
  });
});
