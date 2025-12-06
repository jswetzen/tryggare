import { writable, derived, get } from 'svelte/store';
import type { UndoAction } from '../types';
import { GRACE_PERIOD_MS } from '../types';

/**
 * Generate a UUID with fallback for older browsers
 */
function generateUUID(): string {
  // Try native crypto.randomUUID first
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }

  // Fallback: generate a simple UUID
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

// Internal state
const undoActionsStore = writable<UndoAction[]>([]);
const tickStore = writable(0); // Force updates for countdown
const timeoutsMap = new Map<string, ReturnType<typeof setTimeout>>();

// Update tick every second to trigger countdown updates
let tickInterval: ReturnType<typeof setInterval> | null = null;

// Subscribe to undo actions to manage tick interval
undoActionsStore.subscribe((actions) => {
  if (actions.length > 0 && !tickInterval) {
    // Start tick interval when we have actions
    tickInterval = setInterval(() => {
      tickStore.update((t) => t + 1);
    }, 1000);
  } else if (actions.length === 0 && tickInterval) {
    // Stop tick interval when no actions
    clearInterval(tickInterval);
    tickInterval = null;
  }
});

/**
 * Create a new undo action
 * @param familyId - The family ID this action belongs to
 * @param childIds - Array of child IDs affected by this action
 * @returns The ID of the created undo action
 */
export function createUndoAction(familyId: number, childIds: number[]): string {
  const now = Date.now();
  const action: UndoAction = {
    id: generateUUID(),
    familyId,
    childIds,
    timestamp: now,
    expiresAt: now + GRACE_PERIOD_MS,
  };

  undoActionsStore.update((prev) => [...prev, action]);

  // Set timeout to auto-remove after grace period
  const timeout = setTimeout(() => {
    undoActionsStore.update((prev) => prev.filter((a) => a.id !== action.id));
    timeoutsMap.delete(action.id);
  }, GRACE_PERIOD_MS);

  timeoutsMap.set(action.id, timeout);

  return action.id;
}

/**
 * Manually remove an undo action (when user clicks undo)
 * @param actionId - The ID of the action to remove
 */
export function removeUndoAction(actionId: string): void {
  undoActionsStore.update((prev) => prev.filter((a) => a.id !== actionId));

  // Cancel the auto-removal timeout
  const timeout = timeoutsMap.get(actionId);
  if (timeout) {
    clearTimeout(timeout);
    timeoutsMap.delete(actionId);
  }
}

/**
 * Get remaining seconds for an undo action
 * @param actionId - The ID of the action
 * @returns Remaining seconds, or null if action doesn't exist
 * NOTE: This function uses Date.now() which isn't reactive.
 * Use in templates with the undoActionsWithTick store subscription for reactivity.
 */
export function getRemainingTime(actionId: string): number | null {
  const actions = get(undoActionsStore);
  const action = actions.find((a) => a.id === actionId);
  if (!action) return null;

  const remaining = Math.max(
    0,
    Math.ceil((action.expiresAt - Date.now()) / 1000)
  );
  return remaining;
}

/**
 * Check if a family has any active undo actions
 * @param familyId - The family ID to check
 * @returns True if family has active undo actions
 */
export function hasActiveUndo(familyId: number): boolean {
  const actions = get(undoActionsStore);
  return actions.some((a) => a.familyId === familyId);
}

/**
 * Find undo action by child ID
 * @param childId - The child ID to search for
 * @returns The undo action containing this child, or undefined
 */
export function findUndoActionByChildId(childId: number): UndoAction | undefined {
  const actions = get(undoActionsStore);
  return actions.find((a) => a.childIds.includes(childId));
}

/**
 * Get all undo actions for a family
 * @param familyId - The family ID
 * @returns Array of undo actions for this family
 */
export function getFamilyUndoActions(familyId: number): UndoAction[] {
  const actions = get(undoActionsStore);
  return actions.filter((a) => a.familyId === familyId);
}

/**
 * Clean up all timers (call this when component is destroyed)
 */
export function cleanup(): void {
  timeoutsMap.forEach((timeout) => clearTimeout(timeout));
  timeoutsMap.clear();
  if (tickInterval) {
    clearInterval(tickInterval);
    tickInterval = null;
  }
}

/**
 * Reset store to initial state (used for testing)
 */
export function reset(): void {
  cleanup();
  undoActionsStore.set([]);
  tickStore.set(0);
}

// Export the store for reactive subscriptions
export const undoActions = { subscribe: undoActionsStore.subscribe };

// Export a derived store that combines undoActions with tick for reactive countdown updates
// Returns a new object each tick to ensure Svelte detects changes
export const undoActionsWithTick = derived(
  [undoActionsStore, tickStore],
  ([$actions, $tick]) => ({
    actions: $actions,
    tick: $tick,
  })
);
