import { describe, it, expect, vi, beforeEach } from 'vitest';

const getConversation = vi.fn();
vi.mock('$lib/api/assistantService', () => ({
  assistantApi: { getConversation: (...a: unknown[]) => getConversation(...a) }
}));

import { load } from './+page';

const run = () => load({ params: { eventId: 'e1' } } as never) as Promise<{ unavailable: unknown }>;
const apiError = (status: number, errors: unknown[] = []) => ({ status, message: '', details: { errors } });

async function redirectOf(p: Promise<unknown>) {
  try {
    await p;
  } catch (e) {
    return e as { status: number; location: string };
  }
  return null;
}

describe('/events/[eventId]/setup', () => {
  beforeEach(() => vi.clearAllMocks());

  it('redirects an eligible event to the register page in assistant mode', async () => {
    getConversation.mockResolvedValue({ available: true });
    const r = await redirectOf(run());
    expect(getConversation).toHaveBeenCalledWith('e1');
    expect(r).toMatchObject({ status: 302, location: '/register/e1?preview=1&assistant=1' });
  });

  it('sends a signed-out visitor to login', async () => {
    getConversation.mockRejectedValue(apiError(401));
    expect(await redirectOf(run())).toMatchObject({ status: 302, location: '/login' });
  });

  it.each([
    [403, 'forbidden'],
    [503, 'notEnabled'],
    [404, 'notFound']
  ])('shows a reason on %i', async (status, kind) => {
    getConversation.mockRejectedValue(apiError(status));
    expect(((await run()) as { unavailable: { kind: string } }).unavailable.kind).toBe(kind);
  });

  it('shows the blocker list on 409', async () => {
    getConversation.mockRejectedValue(
      apiError(409, [
        { path: '', code: 'event_not_eligible', message: 'x' },
        { path: 'event', code: 'event_not_empty', message: 'in use' }
      ])
    );
    const { unavailable } = (await run()) as { unavailable: { kind: string; blockers: { code: string }[] } };
    expect(unavailable.kind).toBe('blocked');
    expect(unavailable.blockers.map((b) => b.code)).toEqual(['event_not_empty']);
  });

  it('shows a generic reason when the check itself fails', async () => {
    getConversation.mockRejectedValue({ status: 0, message: 'Network error' });
    expect(((await run()) as { unavailable: { kind: string } }).unavailable.kind).toBe('unknown');
  });
});
