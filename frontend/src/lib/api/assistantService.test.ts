import { describe, it, expect, vi, beforeEach } from 'vitest';

const del = vi.fn();
const get = vi.fn();
const put = vi.fn();
const post = vi.fn();
vi.mock('./client', () => ({
  apiClient: {
    get: (...a: unknown[]) => get(...a),
    put: (...a: unknown[]) => put(...a),
    post: (...a: unknown[]) => post(...a),
    delete: (...a: unknown[]) => del(...a)
  }
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

  it('lists the feature request drafts of the event', async () => {
    await assistantApi.listFeatureRequests('e1');
    expect(get).toHaveBeenCalledWith('/assistant/events/e1/feature-requests/');
  });

  it('confirms a feature request as it is, with no body, when nothing was edited', async () => {
    await assistantApi.confirmFeatureRequest('e1', 'FR-3');
    expect(post).toHaveBeenCalledWith('/assistant/events/e1/feature-requests/FR-3/confirm/', undefined);
  });

  it('confirms with the edited fields as the body', async () => {
    const edits = {
      title: 'Family price',
      problem: 'p',
      desired: 'd',
      tried: ['t'],
      workaround: { used: 'u', cost: 'extra_steps' as const }
    };
    await assistantApi.confirmFeatureRequest('e1', 'FR-3', edits);
    expect(post).toHaveBeenCalledWith('/assistant/events/e1/feature-requests/FR-3/confirm/', edits);
  });

  it('discards a feature request by POST, never a DELETE of the draft', async () => {
    await assistantApi.discardFeatureRequest('e1', 'FR-3');
    expect(post).toHaveBeenCalledWith('/assistant/events/e1/feature-requests/FR-3/discard/');
    expect(del).not.toHaveBeenCalled();
  });
});
