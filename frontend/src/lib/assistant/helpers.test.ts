import { describe, it, expect, vi } from 'vitest';
import {
  coalesce,
  describeUnavailable,
  isAssistantRequested,
  isFallbackStatus,
  isPreviewRequested,
  setupRedirectUrl
} from './helpers';

const err = (status: number, errors: unknown[] = []) => ({
  status,
  message: 'x',
  details: { errors, warnings: [] }
});

describe('setupRedirectUrl', () => {
  it('points at the register page in preview and assistant mode', () => {
    expect(setupRedirectUrl('abc')).toBe('/register/abc?preview=1&assistant=1');
  });
  it('encodes the id', () => {
    expect(setupRedirectUrl('a/b')).toBe('/register/a%2Fb?preview=1&assistant=1');
  });
});

describe('query flags', () => {
  const q = (s: string) => new URLSearchParams(s);
  it('assistant=1 implies preview', () => {
    expect(isPreviewRequested(q('assistant=1'))).toBe(true);
    expect(isAssistantRequested(q('assistant=1'))).toBe(true);
  });
  it('preview alone is not assistant mode', () => {
    expect(isPreviewRequested(q('preview=1'))).toBe(true);
    expect(isAssistantRequested(q('preview=1'))).toBe(false);
  });
  it('only the literal 1 counts', () => {
    expect(isPreviewRequested(q('assistant=true&preview=yes'))).toBe(false);
    expect(isPreviewRequested(q(''))).toBe(false);
  });
});

describe('isFallbackStatus', () => {
  it.each([401, 403, 404, 409, 503])('falls back on %i', (s) => {
    expect(isFallbackStatus(err(s))).toBe(true);
  });
  it.each([0, 400, 500, 502])('does not fall back on %i', (s) => {
    expect(isFallbackStatus(err(s))).toBe(false);
  });
  it('ignores non-API errors', () => {
    expect(isFallbackStatus(new Error('boom'))).toBe(false);
    expect(isFallbackStatus(undefined)).toBe(false);
  });
});

describe('describeUnavailable', () => {
  it('maps statuses to kinds', () => {
    expect(describeUnavailable(err(401)).kind).toBe('unauthenticated');
    expect(describeUnavailable(err(403)).kind).toBe('forbidden');
    expect(describeUnavailable(err(404)).kind).toBe('notFound');
    expect(describeUnavailable(err(503)).kind).toBe('notEnabled');
    expect(describeUnavailable(err(0)).kind).toBe('unknown');
  });
  it('lists the blockers of a 409 without the umbrella code', () => {
    const u = describeUnavailable(
      err(409, [
        { path: '', code: 'event_not_eligible', message: 'no' },
        { path: 'event', code: 'registration_open_on_target', message: 'open' },
        { path: 'event', code: 'event_not_empty', message: 'in use' }
      ])
    );
    expect(u.kind).toBe('blocked');
    expect(u.blockers.map((b) => b.code)).toEqual(['registration_open_on_target', 'event_not_empty']);
  });
  it('survives a body without errors', () => {
    expect(describeUnavailable({ status: 409, message: '', details: 'nope' }).blockers).toEqual([]);
  });
});

describe('coalesce', () => {
  function deferred() {
    let resolve!: () => void;
    const promise = new Promise<void>((r) => (resolve = r));
    return { promise, resolve };
  }

  it('runs once when called once', async () => {
    const job = vi.fn(async () => {});
    await coalesce(job)('a');
    expect(job).toHaveBeenCalledTimes(1);
  });

  it('turns any number of calls during a run into exactly one more, with the latest argument', async () => {
    const gates = [deferred(), deferred()];
    const job = vi.fn(async (_: string) => {
      await gates[job.mock.calls.length - 1].promise;
    });
    const run = coalesce(job);
    const first = run('a');
    run('b');
    run('c');
    expect(job).toHaveBeenCalledTimes(1);
    gates[0].resolve();
    await vi.waitFor(() => expect(job).toHaveBeenCalledTimes(2));
    expect(job).toHaveBeenLastCalledWith('c');
    gates[1].resolve();
    await first;
    expect(job).toHaveBeenCalledTimes(2);
  });

  it('can run again after it went quiet', async () => {
    const job = vi.fn(async () => {});
    const run = coalesce(job);
    await run(1);
    await run(2);
    expect(job).toHaveBeenCalledTimes(2);
  });

  it.each([0, 1, 2, 3, 4, 5, 6])(
    'never drops a call that lands %i microtasks after a run ends',
    async (depth) => {
      const job = vi.fn(async (_: number) => {});
      const run = coalesce(job);
      let tick = Promise.resolve();
      for (let i = 0; i < depth; i++) tick = tick.then(() => {});
      const late = tick.then(() => run(2));
      await run(1);
      await late;
      await vi.waitFor(() => expect(job).toHaveBeenLastCalledWith(2));
    }
  );

  it('a rejected job does not leave a stale queued run behind', async () => {
    const gate = deferred();
    const job = vi
      .fn<(a: number) => Promise<void>>()
      .mockImplementationOnce(async () => {
        await gate.promise;
        throw new Error('x');
      })
      .mockResolvedValue(undefined);
    const run = coalesce(job);
    const first = run(1);
    run(2);
    gate.resolve();
    await expect(first).rejects.toThrow('x');
    await run(3);
    expect(job.mock.calls.map((c) => c[0])).toEqual([1, 3]);
  });
});
