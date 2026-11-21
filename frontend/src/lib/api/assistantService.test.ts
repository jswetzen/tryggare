import { describe, it, expect, vi, beforeEach } from 'vitest';

const del = vi.fn();
const get = vi.fn();
vi.mock('./client', () => ({
  apiClient: { get: (...a: unknown[]) => get(...a), delete: (...a: unknown[]) => del(...a) }
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
    expect(get).toHaveBeenCalledWith('/assistant/events/e1/preview/');
  });
});
