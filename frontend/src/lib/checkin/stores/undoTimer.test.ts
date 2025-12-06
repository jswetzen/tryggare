import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { get } from 'svelte/store';
import {
  undoActions,
  undoActionsWithTick,
  createUndoAction,
  removeUndoAction,
  getRemainingTime,
  hasActiveUndo,
  findUndoActionByChildId,
  getFamilyUndoActions,
  cleanup,
  reset,
} from './undoTimer';

describe('undoTimer store', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    reset(); // Reset store state before each test
  });

  afterEach(() => {
    reset(); // Clean up after each test
    vi.restoreAllMocks();
  });

  it('should initialize with empty undo actions', () => {
    const actions = get(undoActions);
    expect(actions).toEqual([]);
    expect(getRemainingTime('any-id')).toBeNull();
  });

  it('should create an undo action with correct expiration', () => {
    const now = Date.now();
    vi.setSystemTime(now);

    const actionId = createUndoAction('1', ['2', '3']);

    const actions = get(undoActions);
    expect(actions).toHaveLength(1);
    expect(actions[0]).toMatchObject({
      familyId: '1',
      childIds: ['2', '3'],
      timestamp: now,
      expiresAt: now + 30000,
    });
    expect(actions[0].id).toBe(actionId);
    expect(actionId).toBeTruthy();
  });

  it('should calculate remaining time correctly', () => {
    const now = Date.now();
    vi.setSystemTime(now);

    const actionId = createUndoAction('1', ['2']);

    // Just created, should have ~30 seconds
    expect(getRemainingTime(actionId)).toBe(30);

    // Advance 5 seconds
    vi.advanceTimersByTime(5000);
    expect(getRemainingTime(actionId)).toBe(25);

    // Advance 20 more seconds
    vi.advanceTimersByTime(20000);
    expect(getRemainingTime(actionId)).toBe(5);
  });

  it('should auto-remove expired undo actions', () => {
    const actionId = createUndoAction('1', ['2']);

    let actions = get(undoActions);
    expect(actions).toHaveLength(1);

    // Fast-forward past the grace period
    vi.advanceTimersByTime(31000);

    actions = get(undoActions);
    expect(actions).toHaveLength(0);
    expect(getRemainingTime(actionId)).toBeNull();
  });

  it('should manually remove undo action', () => {
    const actionId = createUndoAction('1', ['2']);

    let actions = get(undoActions);
    expect(actions).toHaveLength(1);

    removeUndoAction(actionId);

    actions = get(undoActions);
    expect(actions).toHaveLength(0);
  });

  it('should handle multiple undo actions independently', () => {
    const now = Date.now();
    vi.setSystemTime(now);

    const action1Id = createUndoAction('1', ['2']);

    // Create second action 5 seconds later
    vi.advanceTimersByTime(5000);
    const action2Id = createUndoAction('1', ['3']);

    let actions = get(undoActions);
    expect(actions).toHaveLength(2);

    // First action has 25 seconds remaining, second has 30
    expect(getRemainingTime(action1Id)).toBe(25);
    expect(getRemainingTime(action2Id)).toBe(30);

    // Advance 26 seconds - first should expire, second should remain
    vi.advanceTimersByTime(26000);

    actions = get(undoActions);
    expect(actions).toHaveLength(1);
    expect(actions[0].id).toBe(action2Id);
  });

  it('should check if family has active undo', () => {
    createUndoAction('1', ['2']);
    createUndoAction('3', ['4']);

    expect(hasActiveUndo('1')).toBe(true);
    expect(hasActiveUndo('3')).toBe(true);
    expect(hasActiveUndo('99')).toBe(false);
  });

  it('should find undo action by child ID', () => {
    const actionId = createUndoAction('1', ['2', '3', '4']);

    expect(findUndoActionByChildId('2')?.id).toBe(actionId);
    expect(findUndoActionByChildId('3')?.id).toBe(actionId);
    expect(findUndoActionByChildId('4')?.id).toBe(actionId);
    expect(findUndoActionByChildId('99')).toBeUndefined();
  });

  it('should get all undo actions for a family', () => {
    const action1Id = createUndoAction('1', ['2']);
    const action2Id = createUndoAction('1', ['3']);
    createUndoAction('2', ['4']); // Different family

    const familyActions = getFamilyUndoActions('1');
    expect(familyActions).toHaveLength(2);
    expect(familyActions[0].id).toBe(action1Id);
    expect(familyActions[1].id).toBe(action2Id);

    const family2Actions = getFamilyUndoActions('2');
    expect(family2Actions).toHaveLength(1);
  });

  it('should update reactive store when actions change', () => {
    const values: number[] = [];
    const unsubscribe = undoActions.subscribe((actions) => {
      values.push(actions.length);
    });

    // Initial value
    expect(values).toEqual([0]);

    createUndoAction('1', ['2']);
    expect(values).toEqual([0, 1]);

    createUndoAction('1', ['3']);
    expect(values).toEqual([0, 1, 2]);

    unsubscribe();
  });

  it('should return remaining time of 0 when action is about to expire', () => {
    const now = Date.now();
    vi.setSystemTime(now);

    const actionId = createUndoAction('1', ['2']);

    // Advance to 29.5 seconds (just before expiration)
    vi.advanceTimersByTime(29500);

    // Should return 0 or 1, not negative
    const remaining = getRemainingTime(actionId);
    expect(remaining).not.toBeNull();
    if (remaining !== null) {
      expect(remaining).toBeGreaterThanOrEqual(0);
    }
  });

  it('should handle removing non-existent action gracefully', () => {
    createUndoAction('1', ['2']);

    let actions = get(undoActions);
    expect(actions).toHaveLength(1);

    // Try to remove an action that doesn't exist
    removeUndoAction('non-existent-id');

    // Should not affect existing actions
    actions = get(undoActions);
    expect(actions).toHaveLength(1);
  });

  it('should cleanup all timers on cleanup call', () => {
    createUndoAction('1', ['2']);
    createUndoAction('1', ['3']);

    let actions = get(undoActions);
    expect(actions).toHaveLength(2);

    cleanup();

    // Advancing time should not auto-remove actions since timers are cleared
    vi.advanceTimersByTime(31000);

    // Actions should still be there (cleanup doesn't remove them, just clears timers)
    // Note: In real usage, cleanup is called on component unmount
    actions = get(undoActions);
    expect(actions).toHaveLength(2);
  });

  it('should update tick value every second when actions exist', () => {
    const tickValues: number[] = [];
    const unsubscribe = undoActionsWithTick.subscribe((data) => {
      tickValues.push(data.tick);
    });

    // Initial tick value
    expect(tickValues).toHaveLength(1);
    const initialTick = tickValues[0];

    // Create an action - this should start the tick interval
    createUndoAction('1', ['2']);

    // Advance 1 second - tick should increment
    vi.advanceTimersByTime(1000);
    expect(tickValues).toHaveLength(3); // Initial + action created + 1 second tick
    expect(tickValues[2]).toBe(initialTick + 1);

    // Advance 2 more seconds
    vi.advanceTimersByTime(2000);
    expect(tickValues).toHaveLength(5); // + 2 more ticks
    expect(tickValues[4]).toBe(initialTick + 3);

    unsubscribe();
  });

  it('should emit new object reference on each tick for Svelte reactivity', () => {
    const dataObjects: any[] = [];
    const unsubscribe = undoActionsWithTick.subscribe((data) => {
      dataObjects.push(data);
    });

    // Create an action
    createUndoAction('1', ['2']);

    // Advance 1 second
    vi.advanceTimersByTime(1000);

    // Each emission should be a new object reference
    expect(dataObjects.length).toBeGreaterThanOrEqual(2);
    // Verify they're different object references (for Svelte reactivity)
    expect(dataObjects[dataObjects.length - 1]).not.toBe(dataObjects[dataObjects.length - 2]);

    unsubscribe();
  });

  it('should stop tick interval when all actions are removed', () => {
    const tickValues: number[] = [];
    const unsubscribe = undoActionsWithTick.subscribe((data) => {
      tickValues.push(data.tick);
    });

    const initialLength = tickValues.length;

    // Create an action - starts tick interval
    const actionId = createUndoAction('1', ['2']);

    // Advance 2 seconds
    vi.advanceTimersByTime(2000);
    const lengthWithTick = tickValues.length;
    expect(lengthWithTick).toBeGreaterThan(initialLength);

    // Remove the action - should stop tick interval
    removeUndoAction(actionId);

    const lengthAfterRemoval = tickValues.length;

    // Advance 2 more seconds - tick should NOT continue
    vi.advanceTimersByTime(2000);

    // Should not have new ticks after action removal
    expect(tickValues.length).toBe(lengthAfterRemoval);

    unsubscribe();
  });
});
