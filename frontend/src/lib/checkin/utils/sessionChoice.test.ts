import { describe, it, expect, vi, beforeEach } from 'vitest';
import { pickSession, readSavedSessionId, saveSessionId } from './sessionChoice';

// setupTests.ts replaces localStorage with vi.fn() stubs, so each test scripts its own behaviour.
const storage = localStorage as unknown as {
  getItem: ReturnType<typeof vi.fn>;
  setItem: ReturnType<typeof vi.fn>;
};

const sessions = [{ id: 'a' }, { id: 'b' }, { id: 'c' }];

describe('sessionChoice', () => {
  beforeEach(() => {
    storage.getItem.mockReset();
    storage.setItem.mockReset();
    storage.getItem.mockReturnValue(null);
  });

  it('falls back to the first session when nothing is saved', () => {
    expect(pickSession(sessions)).toBe(sessions[0]);
  });

  it('restores the saved session when it is still active', () => {
    storage.getItem.mockReturnValue('b');
    expect(pickSession(sessions)).toBe(sessions[1]);
  });

  it('falls back to the first session when the saved id is no longer active', () => {
    storage.getItem.mockReturnValue('gone');
    expect(pickSession(sessions)).toBe(sessions[0]);
  });

  it('falls back to the first session when storage cannot be read', () => {
    storage.getItem.mockImplementation(() => {
      throw new DOMException('denied', 'SecurityError');
    });
    expect(readSavedSessionId()).toBeNull();
    expect(pickSession(sessions)).toBe(sessions[0]);
  });

  it('returns null for an empty list', () => {
    expect(pickSession([])).toBeNull();
  });

  it('does not throw when storage cannot be written', () => {
    storage.setItem.mockImplementation(() => {
      throw new DOMException('quota', 'QuotaExceededError');
    });
    expect(() => saveSessionId('b')).not.toThrow();
  });

  it('saves the chosen id', () => {
    saveSessionId('b');
    expect(storage.setItem).toHaveBeenCalledWith('tryggare.selectedSessionId', 'b');
  });
});
