import { describe, it, expect, vi, beforeEach } from 'vitest';

const del = vi.fn();
const get = vi.fn();
const put = vi.fn();
vi.mock('./client', () => ({
  apiClient: { get: (...a: unknown[]) => get(...a), put: (...a: unknown[]) => put(...a), delete: (...a: unknown[]) => del(...a) }
}));

const lang = vi.hoisted(() => ({ value: 'en' }));
vi.mock('svelte-i18n', () => ({
  locale: { subscribe: (run: (v: string) => void) => (run(lang.value), () => {}) }
}));

import { assistantApi } from './assistantService';

describe('assistantApi', () => {
  beforeEach(() => vi.clearAllMocks());

  it('always sends the version on discard, and the token when known', async () => {
    await assistantApi.discardDraft('e1', 4);
    await assistantApi.discardDraft('e1', 4, 'a b');
    expect(del).toHaveBeenNthCalledWith(1, '/assistant/events/e1/draft/?version=4');
    expect(del).toHaveBeenNthCalledWith(2, '/assistant/events/e1/draft/?version=4&token=a%20b');
  });

  it('reads the preview from the assistant endpoint', async () => {
    await assistantApi.getPreview('e1');
    expect(get).toHaveBeenCalledWith('/assistant/events/e1/preview/?lang=en');
  });

  it('asks for draft texts in the UI language', async () => {
    lang.value = 'sv';
    await assistantApi.getDraft('e1');
    expect(get).toHaveBeenCalledWith('/assistant/events/e1/draft/?lang=sv');
    lang.value = 'en';
  });

  it('applies a draft through the existing spec endpoint', async () => {
    await assistantApi.applySpec('e1', { a: 1 });
    expect(put).toHaveBeenCalledWith('/events/e1/spec/', { a: 1 });
  });
});
