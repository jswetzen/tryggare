import type { Family, UndoAction } from '../types';

/**
 * Determines if a family should be visible in the check-in list
 *
 * A family is visible if:
 * - It has at least one unchecked child, OR
 * - It has at least one active undo action
 *
 * This keeps families visible during the grace period even if all
 * children are checked in, allowing users to undo recent check-ins.
 */
export function shouldShowFamily(
  family: Family,
  undoActions: UndoAction[]
): boolean {
  // Check if family has any unchecked children
  const hasUncheckedChildren = family.children.some((child) => !child.checkedIn);

  if (hasUncheckedChildren) {
    return true;
  }

  // Check if family has any active undo actions
  const hasActiveUndo = undoActions.some(
    (action) => action.familyId === family.id
  );

  return hasActiveUndo;
}

/**
 * Filter families that should be displayed
 */
export function getVisibleFamilies(
  families: Family[],
  undoActions: UndoAction[]
): Family[] {
  return families.filter((family) => shouldShowFamily(family, undoActions));
}
