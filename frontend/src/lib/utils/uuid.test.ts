import { describe, it, expect, vi, afterEach } from 'vitest';
import { uuid } from './uuid';

const V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

describe('uuid', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('uses randomUUID when present', () => {
    vi.stubGlobal('crypto', { randomUUID: () => 'native' });
    expect(uuid()).toBe('native');
  });

  it('falls back to getRandomValues when randomUUID is undefined (http context)', () => {
    vi.stubGlobal('crypto', { getRandomValues: (a: Uint8Array) => a.fill(255) });
    expect(uuid()).toMatch(V4);
  });

  it('still returns a v4 without any crypto', () => {
    vi.stubGlobal('crypto', undefined);
    expect(uuid()).toMatch(V4);
  });

  it('is unique across calls', () => {
    vi.stubGlobal('crypto', { getRandomValues: (a: Uint8Array) => crypto_fill(a) });
    expect(uuid()).not.toBe(uuid());
  });
});

function crypto_fill(a: Uint8Array) {
  for (let i = 0; i < a.length; i++) a[i] = Math.floor(Math.random() * 256);
  return a;
}
