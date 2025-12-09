import { describe, it, expect } from 'vitest';
import { shouldShowFamily, sortFamiliesByStatus } from './familyVisibility';
import type { Family, UndoAction } from '../types';

describe('shouldShowFamily', () => {
  const mockFamily: Family = {
    id: '1',
    name: 'Garcia',
    last_name: 'Garcia',
    display_name: 'Garcia Family',
    parents: [],
    children: [
      { id: '1', name: 'Isabella', first_name: 'Isabella', last_name: 'Garcia', ticket: 'event', ticket_type: 'event', checkedIn: false, family: '1' },
      { id: '2', name: 'Lucas', first_name: 'Lucas', last_name: 'Garcia', ticket: 'session', ticket_type: 'session', checkedIn: false, family: '1' },
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
      familyId: '1',
      childIds: ['1', '2'],
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
      familyId: '999', // Different family
      childIds: ['1', '2'],
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
        familyId: '1',
        childIds: ['1'],
        timestamp: Date.now(),
        expiresAt: Date.now() + 30000,
      },
      {
        id: 'undo-2',
        familyId: '1',
        childIds: ['2'],
        timestamp: Date.now(),
        expiresAt: Date.now() + 25000,
      },
    ];

    expect(shouldShowFamily(allCheckedFamily, undoActions)).toBe(true);
  });

  it('should handle empty children array', () => {
    const emptyFamily: Family = {
      id: '1',
      name: 'Empty',
      last_name: 'Empty',
      display_name: 'Empty Family',
      parents: [],
      children: [],
    };

    expect(shouldShowFamily(emptyFamily, [])).toBe(false);
  });
});

describe('sortFamiliesByStatus', () => {
  const garciaFamily: Family = {
    id: '1',
    name: 'Garcia',
    last_name: 'Garcia',
    display_name: 'Garcia Family',
    parents: [],
    children: [
      { id: '1', name: 'Isabella', first_name: 'Isabella', last_name: 'Garcia', ticket: 'event', ticket_type: 'event', checkedIn: false, family: '1' },
      { id: '2', name: 'Lucas', first_name: 'Lucas', last_name: 'Garcia', ticket: 'session', ticket_type: 'session', checkedIn: false, family: '1' },
    ],
  };

  const smithFamily: Family = {
    id: '2',
    name: 'Smith',
    last_name: 'Smith',
    display_name: 'Smith Family',
    parents: [],
    children: [
      { id: '3', name: 'Emma', first_name: 'Emma', last_name: 'Smith', ticket: 'event', ticket_type: 'event', checkedIn: false, family: '2' },
    ],
  };

  const andersonFamily: Family = {
    id: '3',
    name: 'Anderson',
    last_name: 'Anderson',
    display_name: 'Anderson Family',
    parents: [],
    children: [
      { id: '4', name: 'Liam', first_name: 'Liam', last_name: 'Anderson', ticket: 'event', ticket_type: 'event', checkedIn: false, family: '3' },
    ],
  };

  const martinezFamily: Family = {
    id: '4',
    name: 'Martinez',
    last_name: 'Martinez',
    display_name: 'Martinez Family',
    parents: [],
    children: [
      { id: '5', name: 'Sofia', first_name: 'Sofia', last_name: 'Martinez', ticket: 'event', ticket_type: 'event', checkedIn: true, family: '4' },
      { id: '6', name: 'Diego', first_name: 'Diego', last_name: 'Martinez', ticket: 'event', ticket_type: 'event', checkedIn: true, family: '4' },
    ],
  };

  const williamsFamily: Family = {
    id: '5',
    name: 'Williams',
    last_name: 'Williams',
    display_name: 'Williams Family',
    parents: [],
    children: [
      { id: '7', name: 'Olivia', first_name: 'Olivia', last_name: 'Williams', ticket: 'event', ticket_type: 'event', checkedIn: true, family: '5' },
    ],
  };

  it('should sort families with unchecked children first, alphabetically', () => {
    const families = [smithFamily, garciaFamily, andersonFamily];
    const sorted = sortFamiliesByStatus(families, []);

    expect(sorted).toEqual([andersonFamily, garciaFamily, smithFamily]);
  });

  it('should place families with all checked-in and active undo below unchecked families', () => {
    const allCheckedMartinez: Family = {
      ...martinezFamily,
      children: martinezFamily.children.map((c) => ({ ...c, checkedIn: true })),
    };

    const undoAction: UndoAction = {
      id: 'undo-1',
      familyId: '4',
      childIds: ['5', '6'],
      timestamp: Date.now(),
      expiresAt: Date.now() + 30000,
    };

    const families = [allCheckedMartinez, smithFamily, garciaFamily];
    const sorted = sortFamiliesByStatus(families, [undoAction]);

    // Unchecked families first (Garcia, Smith), then checked with undo (Martinez)
    expect(sorted).toEqual([garciaFamily, smithFamily, allCheckedMartinez]);
  });

  it('should sort families with active undo alphabetically within their group', () => {
    const allCheckedMartinez: Family = {
      ...martinezFamily,
      children: martinezFamily.children.map((c) => ({ ...c, checkedIn: true })),
    };

    const allCheckedWilliams: Family = {
      ...williamsFamily,
      children: williamsFamily.children.map((c) => ({ ...c, checkedIn: true })),
    };

    const undoAction1: UndoAction = {
      id: 'undo-1',
      familyId: '4',
      childIds: ['5', '6'],
      timestamp: Date.now(),
      expiresAt: Date.now() + 30000,
    };

    const undoAction2: UndoAction = {
      id: 'undo-2',
      familyId: '5',
      childIds: ['7'],
      timestamp: Date.now(),
      expiresAt: Date.now() + 25000,
    };

    const families = [allCheckedWilliams, andersonFamily, allCheckedMartinez];
    const sorted = sortFamiliesByStatus(families, [undoAction1, undoAction2]);

    // Anderson (unchecked) first, then Martinez and Williams (both checked with undo, alphabetically)
    expect(sorted).toEqual([andersonFamily, allCheckedMartinez, allCheckedWilliams]);
  });

  it('should treat families with any unchecked child as unchecked', () => {
    const mixedGarcia: Family = {
      ...garciaFamily,
      children: [
        { ...garciaFamily.children[0], checkedIn: true },
        garciaFamily.children[1], // Still unchecked
      ],
    };

    const allCheckedMartinez: Family = {
      ...martinezFamily,
      children: martinezFamily.children.map((c) => ({ ...c, checkedIn: true })),
    };

    const undoAction: UndoAction = {
      id: 'undo-1',
      familyId: '4',
      childIds: ['5', '6'],
      timestamp: Date.now(),
      expiresAt: Date.now() + 30000,
    };

    const families = [allCheckedMartinez, mixedGarcia];
    const sorted = sortFamiliesByStatus(families, [undoAction]);

    // Mixed Garcia (has unchecked) comes before all-checked Martinez (even with undo)
    expect(sorted).toEqual([mixedGarcia, allCheckedMartinez]);
  });

  it('should handle empty families array', () => {
    const sorted = sortFamiliesByStatus([], []);
    expect(sorted).toEqual([]);
  });

  it('should handle families with no undo actions', () => {
    const families = [smithFamily, andersonFamily, garciaFamily];
    const sorted = sortFamiliesByStatus(families, []);

    // All unchecked, sorted alphabetically
    expect(sorted).toEqual([andersonFamily, garciaFamily, smithFamily]);
  });

  it('should maintain original order for families in same priority group with same name', () => {
    const garcia1: Family = {
      id: '1',
      name: 'Garcia',
      last_name: 'Garcia',
      display_name: 'Garcia Family',
      parents: [],
      children: [{ id: '1', name: 'Isabella', first_name: 'Isabella', last_name: 'Garcia', ticket: 'event', ticket_type: 'event', checkedIn: false, family: '1' }],
    };

    const garcia2: Family = {
      id: '2',
      name: 'Garcia',
      last_name: 'Garcia',
      display_name: 'Garcia Family',
      parents: [],
      children: [{ id: '2', name: 'Lucas', first_name: 'Lucas', last_name: 'Garcia', ticket: 'event', ticket_type: 'event', checkedIn: false, family: '2' }],
    };

    const families = [garcia1, garcia2];
    const sorted = sortFamiliesByStatus(families, []);

    // Both have same name and status, should maintain original order
    expect(sorted).toEqual([garcia1, garcia2]);
  });
});
