import { describe, it, expect } from 'vitest';
import en from './locales/en.json';
import sv from './locales/sv.json';
import { ERROR_CODES } from '$lib/assistant/helpers';

function keys(obj: unknown, prefix = ''): string[] {
  if (obj === null || typeof obj !== 'object') return [prefix];
  return Object.entries(obj).flatMap(([k, v]) => keys(v, prefix ? `${prefix}.${k}` : k));
}

describe('assistant i18n', () => {
  it('has the same keys in en and sv', () => {
    expect(keys(sv.assistant).sort()).toEqual(keys(en.assistant).sort());
  });

  it('covers every error code, tool, review kind and refusal reason the chat can show', () => {
    for (const locale of [en, sv] as const) {
      const a = locale.assistant as unknown as Record<string, Record<string, unknown>>;
      for (const code of ERROR_CODES) expect(a.error[code], code).toBeTruthy();
      expect(a.error.unknown).toBeTruthy();
      for (const tool of ['get_capabilities', 'get_current_spec', 'validate_spec', 'diff_spec', 'propose_spec', 'unknown'])
        expect(a.tool[tool], tool).toBeTruthy();
      const review = a.review as unknown as { kind: Record<string, string> };
      for (const kind of ['event', 'sessions', 'ticket_types', 'extras', 'choices', 'promo_codes'])
        expect(review.kind[kind], kind).toBeTruthy();
      for (const reason of ['unauthenticated', 'forbidden', 'notFound', 'blocked', 'notEnabled'])
        expect(a.unavailable[reason], reason).toBeTruthy();
    }
  });
});
