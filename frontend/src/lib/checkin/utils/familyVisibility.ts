import type { Family, UndoAction } from '../types';

/**
 * Determines if a family should be visible in the check-in list
 *
 * A family is visible if:
 * - It has at least one unchecked child, OR
 * - It has no children at all AND has at least one unchecked parent, OR
 * - It has at least one active undo action
 *
 * This keeps families visible during the grace period even if all
 * children are checked in, allowing users to undo recent check-ins.
 *
 * Parent check-in state only drives visibility for all-adult households (no
 * children at all) — without that, `.some()` on an empty children array is
 * always false and such a family would never appear. It's deliberately NOT
 * considered for families that do have children: parents are rarely (if
 * ever) checked in in practice, so factoring them in unconditionally would
 * keep almost every family with children permanently visible even once all
 * of its children are checked in, defeating the "hide when done" purpose of
 * this filter entirely.
 */
export function shouldShowFamily(
  family: Family,
  undoActions: UndoAction[]
): boolean {
  const hasUncheckedChildren = family.children.some((child) => !child.checkedIn);
  if (hasUncheckedChildren) {
    return true;
  }

  if (family.children.length === 0) {
    const hasUncheckedParents = family.parents.some((parent) => !parent.checkedIn);
    if (hasUncheckedParents) {
      return true;
    }
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
 * 1. Families with an unchecked child, or (if childless) an unchecked parent
 *    (sorted alphabetically by family name)
 * 2. Families with all checked-in but active undo (sorted alphabetically by family name)
 *
 * Mirrors shouldShowFamily's rule: parent check-in state only affects
 * ordering for all-adult (childless) households, for the same reason —
 * otherwise almost every family with children would stay pinned to the
 * "unchecked" group by its rarely-checked-in parents.
 *
 * @param families - Array of families to sort
 * @param _undoActions - Array of undo actions (unused, kept for API consistency)
 */
export function sortFamiliesByStatus(
  families: Family[],
  _undoActions: UndoAction[]
): Family[] {
  const hasUnchecked = (f: Family) =>
    f.children.some((child) => !child.checkedIn) ||
    (f.children.length === 0 && f.parents.some((parent) => !parent.checkedIn));

  return [...families].sort((a, b) => {
    const aHasUnchecked = hasUnchecked(a);
    const bHasUnchecked = hasUnchecked(b);

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
