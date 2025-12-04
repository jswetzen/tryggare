import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useUndoTimer } from './useUndoTimer';

describe('useUndoTimer', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should initialize with empty undo actions', () => {
    const { result } = renderHook(() => useUndoTimer());

    expect(result.current.undoActions).toEqual([]);
    expect(result.current.getRemainingTime('any-id')).toBeNull();
  });

  it('should create an undo action with correct expiration', () => {
    const { result } = renderHook(() => useUndoTimer());
    const now = Date.now();
    vi.setSystemTime(now);

    act(() => {
      result.current.createUndoAction(1, [2, 3]);
    });

    expect(result.current.undoActions).toHaveLength(1);
    expect(result.current.undoActions[0]).toMatchObject({
      familyId: 1,
      childIds: [2, 3],
      timestamp: now,
      expiresAt: now + 30000,
    });
    expect(result.current.undoActions[0].id).toBeTruthy();
  });

  it('should calculate remaining time correctly', () => {
    const { result } = renderHook(() => useUndoTimer());
    const now = Date.now();
    vi.setSystemTime(now);

    let actionId: string;

    act(() => {
      actionId = result.current.createUndoAction(1, [2]);
    });

    // Just created, should have ~30 seconds
    expect(result.current.getRemainingTime(actionId!)).toBe(30);

    // Advance 5 seconds
    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(result.current.getRemainingTime(actionId!)).toBe(25);

    // Advance 20 more seconds
    act(() => {
      vi.advanceTimersByTime(20000);
    });

    expect(result.current.getRemainingTime(actionId!)).toBe(5);
  });

  it('should auto-remove expired undo actions', () => {
    const { result } = renderHook(() => useUndoTimer());

    let actionId: string;

    act(() => {
      actionId = result.current.createUndoAction(1, [2]);
    });

    expect(result.current.undoActions).toHaveLength(1);

    // Fast-forward past the grace period
    act(() => {
      vi.advanceTimersByTime(31000);
    });

    expect(result.current.undoActions).toHaveLength(0);
    expect(result.current.getRemainingTime(actionId!)).toBeNull();
  });

  it('should manually remove undo action', () => {
    const { result } = renderHook(() => useUndoTimer());

    let actionId: string;

    act(() => {
      actionId = result.current.createUndoAction(1, [2]);
    });

    expect(result.current.undoActions).toHaveLength(1);

    act(() => {
      result.current.removeUndoAction(actionId!);
    });

    expect(result.current.undoActions).toHaveLength(0);
  });

  it('should handle multiple undo actions independently', () => {
    const { result } = renderHook(() => useUndoTimer());
    const now = Date.now();
    vi.setSystemTime(now);

    let action1Id: string;
    let action2Id: string;

    act(() => {
      action1Id = result.current.createUndoAction(1, [2]);
    });

    // Create second action 5 seconds later
    act(() => {
      vi.advanceTimersByTime(5000);
      action2Id = result.current.createUndoAction(1, [3]);
    });

    expect(result.current.undoActions).toHaveLength(2);

    // First action has 25 seconds remaining, second has 30
    expect(result.current.getRemainingTime(action1Id!)).toBe(25);
    expect(result.current.getRemainingTime(action2Id!)).toBe(30);

    // Advance 26 seconds - first should expire, second should remain
    act(() => {
      vi.advanceTimersByTime(26000);
    });

    expect(result.current.undoActions).toHaveLength(1);
    expect(result.current.undoActions[0].id).toBe(action2Id!);
  });

  it('should check if family has active undo', () => {
    const { result } = renderHook(() => useUndoTimer());

    act(() => {
      result.current.createUndoAction(1, [2]);
      result.current.createUndoAction(3, [4]);
    });

    expect(result.current.hasActiveUndo(1)).toBe(true);
    expect(result.current.hasActiveUndo(3)).toBe(true);
    expect(result.current.hasActiveUndo(99)).toBe(false);
  });

  it('should find undo action by child ID', () => {
    const { result } = renderHook(() => useUndoTimer());

    let actionId: string;

    act(() => {
      actionId = result.current.createUndoAction(1, [2, 3, 4]);
    });

    expect(result.current.findUndoActionByChildId(2)?.id).toBe(actionId!);
    expect(result.current.findUndoActionByChildId(3)?.id).toBe(actionId!);
    expect(result.current.findUndoActionByChildId(4)?.id).toBe(actionId!);
    expect(result.current.findUndoActionByChildId(99)).toBeUndefined();
  });

  it('should trigger timer updates every second', () => {
    const { result } = renderHook(() => useUndoTimer());

    act(() => {
      result.current.createUndoAction(1, [2]);
    });

    const initialTime = result.current.getRemainingTime(
      result.current.undoActions[0].id
    );

    // Advance by 1 second
    act(() => {
      vi.advanceTimersByTime(1000);
    });

    const afterOneSecond = result.current.getRemainingTime(
      result.current.undoActions[0].id
    );

    expect(afterOneSecond).toBe(initialTime! - 1);
  });
});
