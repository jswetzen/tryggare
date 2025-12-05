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
 * Sorts families by check-in status and alphabetically
 *
 * Sorting order:
 * 1. Families with unchecked children (sorted alphabetically by family name)
 * 2. Families with all checked-in but active undo (sorted alphabetically by family name)
 *
 * A family has unchecked children if ANY child has checkedIn === false
 *
 * @param families - Array of families to sort
 * @param _undoActions - Array of undo actions (unused, kept for API consistency)
 */
export function sortFamiliesByStatus(
  families: Family[],
  _undoActions: UndoAction[]
): Family[] {
  return [...families].sort((a, b) => {
    const aHasUnchecked = a.children.some((child) => !child.checkedIn);
    const bHasUnchecked = b.children.some((child) => !child.checkedIn);

    // If one has unchecked and the other doesn't, unchecked comes first
    if (aHasUnchecked && !bHasUnchecked) return -1;
    if (!aHasUnchecked && bHasUnchecked) return 1;

    // Both have same unchecked status, sort alphabetically
    return a.name.localeCompare(b.name);
  });
}

/**
 * Filter families that should be displayed, sorted by status
 */
export function getVisibleFamilies(
  families: Family[],
  undoActions: UndoAction[]
): Family[] {
  const visible = families.filter((family) => shouldShowFamily(family, undoActions));
  return sortFamiliesByStatus(visible, undoActions);
}
