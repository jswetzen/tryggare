import { describe, it, expect } from 'vitest';
import en from './locales/en.json';
import sv from './locales/sv.json';

function keys(obj: unknown, prefix = ''): string[] {
  if (obj === null || typeof obj !== 'object') return [prefix];
  return Object.entries(obj).flatMap(([k, v]) => keys(v, prefix ? `${prefix}.${k}` : k));
}

describe('assistant i18n', () => {
  it('has the same keys in en and sv', () => {
    expect(keys(sv.assistant).sort()).toEqual(keys(en.assistant).sort());
  });
});
