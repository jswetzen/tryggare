import { useState, useEffect, useCallback, useRef } from 'react';
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

/**
 * Custom hook for managing undo actions with automatic expiration
 *
 * This hook handles:
 * - Creating undo actions with 30-second grace period
 * - Auto-removing expired actions
 * - Manual removal of actions (when user clicks undo)
 * - Calculating remaining time for countdown display
 * - Finding actions by child or family ID
 */
export function useUndoTimer() {
  const [undoActions, setUndoActions] = useState<UndoAction[]>([]);
  const [, setTick] = useState(0); // Force re-renders for countdown updates
  const timeoutsRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  // Update countdown every second
  useEffect(() => {
    if (undoActions.length === 0) return;

    const interval = setInterval(() => {
      setTick((t) => t + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [undoActions.length]);

  /**
   * Create a new undo action
   * @param familyId - The family ID this action belongs to
   * @param childIds - Array of child IDs affected by this action
   * @returns The ID of the created undo action
   */
  const createUndoAction = useCallback(
    (familyId: number, childIds: number[]): string => {
      const now = Date.now();
      const action: UndoAction = {
        id: generateUUID(),
        familyId,
        childIds,
        timestamp: now,
        expiresAt: now + GRACE_PERIOD_MS,
      };

      setUndoActions((prev) => [...prev, action]);

      // Set timeout to auto-remove after grace period
      const timeout = setTimeout(() => {
        setUndoActions((prev) => prev.filter((a) => a.id !== action.id));
        timeoutsRef.current.delete(action.id);
      }, GRACE_PERIOD_MS);

      timeoutsRef.current.set(action.id, timeout);

      return action.id;
    },
    []
  );

  /**
   * Manually remove an undo action (when user clicks undo)
   * @param actionId - The ID of the action to remove
   */
  const removeUndoAction = useCallback((actionId: string) => {
    setUndoActions((prev) => prev.filter((a) => a.id !== actionId));

    // Cancel the auto-removal timeout
    const timeout = timeoutsRef.current.get(actionId);
    if (timeout) {
      clearTimeout(timeout);
      timeoutsRef.current.delete(actionId);
    }
  }, []);

  /**
   * Get remaining seconds for an undo action
   * @param actionId - The ID of the action
   * @returns Remaining seconds, or null if action doesn't exist
   */
  const getRemainingTime = useCallback(
    (actionId: string): number | null => {
      const action = undoActions.find((a) => a.id === actionId);
      if (!action) return null;

      const remaining = Math.max(
        0,
        Math.ceil((action.expiresAt - Date.now()) / 1000)
      );
      return remaining;
    },
    [undoActions]
  );

  /**
   * Check if a family has any active undo actions
   * @param familyId - The family ID to check
   * @returns True if family has active undo actions
   */
  const hasActiveUndo = useCallback(
    (familyId: number): boolean => {
      return undoActions.some((a) => a.familyId === familyId);
    },
    [undoActions]
  );

  /**
   * Find undo action by child ID
   * @param childId - The child ID to search for
   * @returns The undo action containing this child, or undefined
   */
  const findUndoActionByChildId = useCallback(
    (childId: number): UndoAction | undefined => {
      return undoActions.find((a) => a.childIds.includes(childId));
    },
    [undoActions]
  );

  /**
   * Get all undo actions for a family
   * @param familyId - The family ID
   * @returns Array of undo actions for this family
   */
  const getFamilyUndoActions = useCallback(
    (familyId: number): UndoAction[] => {
      return undoActions.filter((a) => a.familyId === familyId);
    },
    [undoActions]
  );

  // Clean up timeouts on unmount
  useEffect(() => {
    return () => {
      timeoutsRef.current.forEach((timeout) => clearTimeout(timeout));
      timeoutsRef.current.clear();
    };
  }, []);

  return {
    undoActions,
    createUndoAction,
    removeUndoAction,
    getRemainingTime,
    hasActiveUndo,
    findUndoActionByChildId,
    getFamilyUndoActions,
  };
}
