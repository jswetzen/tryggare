/** Feature request cards in the assistant store: reducer rules, and the GET and event wiring. */
import { describe, it, expect, vi } from 'vitest';
import { createAssistantStore, initialState, reduce, type SocketLike } from './assistantStore';
import { get } from 'svelte/store';
import type { FeatureRequestDraft, FeatureRequestPreview, ServerEvent } from './types';

const draft = (over: Partial<FeatureRequestDraft> = {}): FeatureRequestDraft => ({
  id: 'FR-1',
  title: 'Family price',
  problem: 'Families want one price.',
  desired: 'One price for a group.',
  workaround: { used: 'A code per family', cost: 'extra_steps' },
  matches_existing: null,
  tried: ['Two tickets'],
  touches: ['cap:family_groups'],
  severity: 'friction',
  brief_fragment: null,
  ...over
});

// The fields the WebSocket event carries (no tried, touches, severity or brief_fragment).
const preview = (over: Partial<FeatureRequestPreview> = {}): FeatureRequestPreview => ({
  id: 'FR-1',
  title: 'Family price',
  problem: 'Families want one price.',
  desired: 'One price for a group.',
  workaround: { used: 'A code per family', cost: 'extra_steps' },
  matches_existing: null,
  ...over
});

const filed = (over: Partial<FeatureRequestPreview> = {}): ServerEvent => ({
  type: 'feature_request_draft',
  run_id: 'r-1',
  ...preview(over)
});

const apply = (events: ServerEvent[]) =>
  events.reduce((s, event) => reduce(s, { kind: 'server', event }), initialState());

describe('feature request cards in the reducer', () => {
  it('adds a card from the event, once per id', () => {
    const s = apply([filed(), filed({ title: 'Family price, retitled' })]);
    expect(s.featureRequests.map((c) => c.id)).toEqual(['FR-1']);
    expect(s.featureRequests[0].title).toBe('Family price, retitled');
  });

  it('keeps the event fields off the run id and type', () => {
    const [card] = apply([filed()]).featureRequests;
    expect(card).not.toHaveProperty('run_id');
    expect(card).not.toHaveProperty('type');
  });

  it('loads the GET over the event preview, and drops a card the server no longer lists', () => {
    const s0 = apply([filed({ id: 'FR-1' }), filed({ id: 'FR-2', title: 'Gone soon' })]);
    const s1 = reduce(s0, { kind: 'featureRequestsLoaded', drafts: [draft({ id: 'FR-1' })] });
    expect(s1.featureRequests).toHaveLength(1);
    expect(s1.featureRequests[0]).toMatchObject({ id: 'FR-1', tried: ['Two tickets'], severity: 'friction' });
  });

  it('settles a card: it stays as a receipt across a reload, and is not reopened by a late event', () => {
    let s = apply([filed()]);
    s = reduce(s, { kind: 'featureRequestSettled', id: 'FR-1', outcome: 'confirmed', duplicate_of: null });
    s = reduce(s, { kind: 'server', event: filed({ title: 'late' }) });
    s = reduce(s, { kind: 'featureRequestsLoaded', drafts: [] });
    expect(s.featureRequests).toEqual([
      expect.objectContaining({ id: 'FR-1', outcome: 'confirmed', title: 'Family price' })
    ]);
  });

  it('a settled card keeps the title it was confirmed with, not the one it was filed with', () => {
    let s = apply([filed()]);
    s = reduce(s, {
      kind: 'featureRequestSettled',
      id: 'FR-1',
      outcome: 'confirmed',
      duplicate_of: null,
      title: 'Family ticket'
    });
    expect(s.featureRequests[0]).toMatchObject({ outcome: 'confirmed', title: 'Family ticket' });
  });

  it('settles as a join, with the request it joined', () => {
    let s = apply([filed()]);
    s = reduce(s, { kind: 'featureRequestSettled', id: 'FR-1', outcome: 'duplicate', duplicate_of: 'FR-9' });
    expect(s.featureRequests[0]).toMatchObject({ outcome: 'duplicate', duplicate_of: 'FR-9' });
  });

  it('removes a discarded card', () => {
    const s = reduce(apply([filed({ id: 'FR-1' }), filed({ id: 'FR-2' })]), {
      kind: 'featureRequestRemoved',
      id: 'FR-1'
    });
    expect(s.featureRequests.map((c) => c.id)).toEqual(['FR-2']);
  });

  it('a clear drops the receipts and keeps the pending drafts', () => {
    let s = apply([filed({ id: 'FR-1' }), filed({ id: 'FR-2' })]);
    s = reduce(s, { kind: 'featureRequestSettled', id: 'FR-1', outcome: 'confirmed', duplicate_of: null });
    s = reduce(s, { kind: 'featureReceiptsCleared' });
    expect(s.featureRequests.map((c) => c.id)).toEqual(['FR-2']);
  });
});

describe('feature request cards in the store', () => {
  class FakeSocket implements SocketLike {
    readyState = 1;
    onopen: SocketLike['onopen'] = null;
    onmessage: SocketLike['onmessage'] = null;
    onclose: SocketLike['onclose'] = null;
    onerror: SocketLike['onerror'] = null;
    send() {}
    close() {}
    receive(e: ServerEvent) {
      this.onmessage?.({ data: JSON.stringify(e) });
    }
  }

  const deferred = <T,>() => {
    let resolve!: (v: T) => void;
    const promise = new Promise<T>((r) => (resolve = r));
    return { promise, resolve };
  };

  const conversation = {
    available: true,
    conversation_id: 'c1',
    transcript: [],
    running: false,
    notice_accepted: true,
    draft_version: 0
  };

  function setup(fetchFeatureRequests: () => Promise<FeatureRequestDraft[]>) {
    let socket: FakeSocket | null = null;
    const store = createAssistantStore({
      eventId: 'e1',
      createSocket: () => (socket = new FakeSocket()),
      fetchConversation: async () => conversation,
      fetchFeatureRequests
    });
    store.connect();
    const sock = () => socket as unknown as FakeSocket;
    sock().onopen?.();
    return { store, sock };
  }

  it('loads the drafts when the socket is ready', async () => {
    const fetchFeatureRequests = vi.fn(async () => [draft()]);
    const { store, sock } = setup(fetchFeatureRequests);
    sock().receive({ type: 'ready', conversation_id: 'c1', running: false, draft_version: 0, notice_required: false });
    await vi.waitFor(() => expect(get(store).featureRequests.map((c) => c.id)).toEqual(['FR-1']));
    expect(get(store).featureRequests[0].tried).toEqual(['Two tickets']);
  });

  it('a filed draft event triggers a GET, so the card gets its full fields', async () => {
    const fetchFeatureRequests = vi.fn(async () => [draft()]);
    const { store, sock } = setup(fetchFeatureRequests);
    sock().receive(filed());
    expect(get(store).featureRequests[0].tried).toBeUndefined();
    await vi.waitFor(() => expect(get(store).featureRequests[0].tried).toEqual(['Two tickets']));
    expect(fetchFeatureRequests).toHaveBeenCalled();
  });

  it('applies only the newest GET: an older answer cannot undo a newer one', async () => {
    const first = deferred<FeatureRequestDraft[]>();
    const second = deferred<FeatureRequestDraft[]>();
    const answers = [first, second];
    const fetchFeatureRequests = vi.fn(() => answers.shift()!.promise);
    const { store, sock } = setup(fetchFeatureRequests);
    sock().receive(filed({ id: 'FR-1' }));
    sock().receive(filed({ id: 'FR-2' }));
    second.resolve([draft({ id: 'FR-2' })]);
    await vi.waitFor(() => expect(get(store).featureRequests.map((c) => c.id)).toEqual(['FR-2']));
    first.resolve([draft({ id: 'FR-1' })]);
    await Promise.resolve();
    expect(get(store).featureRequests.map((c) => c.id)).toEqual(['FR-2']);
  });

  it('a GET sent before the organizer discarded a card cannot bring it back', async () => {
    const pending = deferred<FeatureRequestDraft[]>();
    const { store, sock } = setup(() => pending.promise);
    sock().receive(filed({ id: 'FR-1' }));
    store.featureRequestRemoved('FR-1');
    pending.resolve([draft({ id: 'FR-1' })]);
    await Promise.resolve();
    await Promise.resolve();
    expect(get(store).featureRequests).toEqual([]);
  });

  it('a failed GET keeps the cards already shown', async () => {
    const { store, sock } = setup(() => Promise.reject(new Error('offline')));
    sock().receive(filed({ id: 'FR-1' }));
    await Promise.resolve();
    await Promise.resolve();
    expect(get(store).featureRequests.map((c) => c.id)).toEqual(['FR-1']);
  });
});
