import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { get } from 'svelte/store';
import {
  backoffDelay,
  createAssistantStore,
  initialState,
  reduce,
  wsUrl,
  type SocketLike
} from './assistantStore';
import type { ConversationState, ServerEvent } from './types';

class FakeSocket implements SocketLike {
  static all: FakeSocket[] = [];
  readyState = 0;
  sent: string[] = [];
  onopen: SocketLike['onopen'] = null;
  onmessage: SocketLike['onmessage'] = null;
  onclose: SocketLike['onclose'] = null;
  onerror: SocketLike['onerror'] = null;
  closed = false;
  constructor(public url: string) {
    FakeSocket.all.push(this);
  }
  send(data: string) {
    this.sent.push(data);
  }
  close() {
    this.closed = true;
  }
  open() {
    this.readyState = 1;
    this.onopen?.();
  }
  receive(event: ServerEvent | string) {
    this.onmessage?.({ data: typeof event === 'string' ? event : JSON.stringify(event) });
  }
  drop(code = 1006) {
    this.readyState = 3;
    this.onclose?.({ code });
  }
}

const conversation = (over: Partial<ConversationState> = {}): ConversationState => ({
  available: true,
  conversation_id: 'conv-1',
  transcript: [],
  running: false,
  notice_accepted: true,
  draft_version: 0,
  ...over
});

const ready = (over: Partial<Extract<ServerEvent, { type: 'ready' }>> = {}): ServerEvent => ({
  type: 'ready',
  conversation_id: 'conv-1',
  running: false,
  draft_version: 3,
  notice_required: false,
  ...over
});

const apply = (events: ServerEvent[], start = initialState()) =>
  events.reduce((s, event) => reduce(s, { kind: 'server', event }), start);

describe('reduce', () => {
  it('ready opens the conversation', () => {
    const s = apply([ready({ running: true, notice_required: true })]);
    expect(s).toMatchObject({
      connection: 'open',
      conversationId: 'conv-1',
      running: true,
      noticeRequired: true,
      draftVersion: 3
    });
  });

  it('follows a run: started, tools, text, draft, finished', () => {
    let s = apply([
      ready(),
      { type: 'run_started', run_id: 'r-1', reply_to: 'c-1' },
      { type: 'tool_started', run_id: 'r-1', call_id: 't-1', tool: 'validate_spec' }
    ]);
    expect(s.running).toBe(true);
    expect(s.tools).toEqual([{ callId: 't-1', tool: 'validate_spec', state: 'running' }]);

    s = apply(
      [
        { type: 'tool_finished', run_id: 'r-1', call_id: 't-1', tool: 'validate_spec', ok: false },
        { type: 'text_delta', run_id: 'r-1', text: 'Two ' },
        { type: 'text_delta', run_id: 'r-1', text: 'bands' },
        { type: 'draft_updated', run_id: 'r-1', draft_version: 4 }
      ],
      s
    );
    expect(s.tools[0].state).toBe('failed');
    expect(s.transcript).toEqual([{ role: 'assistant', text: 'Two bands', runId: 'r-1' }]);
    expect(s.draftVersion).toBe(4);

    s = apply([{ type: 'run_finished', run_id: 'r-1' }], s);
    expect(s).toMatchObject({ running: false, runId: null, tools: [] });
  });

  it('a successful tool is marked done', () => {
    const s = apply([
      { type: 'tool_started', run_id: 'r', call_id: 't-1', tool: 'get_capabilities' },
      { type: 'tool_finished', run_id: 'r', call_id: 't-1', tool: 'get_capabilities', ok: true }
    ]);
    expect(s.tools[0].state).toBe('done');
  });

  it('text of a new run starts a new assistant entry', () => {
    const s = apply([
      { type: 'text_delta', run_id: 'r-1', text: 'one' },
      { type: 'text_delta', run_id: 'r-2', text: 'two' }
    ]);
    expect(s.transcript.map((e) => e.text)).toEqual(['one', 'two']);
  });

  it('run_failed ends the run and keeps the code', () => {
    const s = apply([
      { type: 'run_started', run_id: 'r-1', reply_to: 'c-1' },
      { type: 'run_failed', run_id: 'r-1', reply_to: 'c-1', code: 'timeout' }
    ]);
    expect(s.running).toBe(false);
    expect(s.error).toEqual({ code: 'timeout', replyTo: 'c-1' });
  });

  it('a refusal before a run drops the unsent message and leaves a live run alone', () => {
    let s = reduce(apply([ready(), { type: 'run_started', run_id: 'r-1', reply_to: 'c-0' }]), {
      kind: 'sent',
      id: 'c-2',
      text: 'again'
    });
    s = apply([{ type: 'run_failed', run_id: null, reply_to: 'c-2', code: 'busy' }], s);
    expect(s.running).toBe(true);
    expect(s.runId).toBe('r-1');
    expect(s.transcript).toEqual([]);
    expect(s.error?.code).toBe('busy');
  });

  it('a personal-data warning removes the message and keeps its text for "Send anyway"', () => {
    let s = reduce(initialState(), { kind: 'sent', id: 'c-1', text: 'Anna 070-123 45 67' });
    s = reduce(
      s,
      { kind: 'server', event: { type: 'warning', code: 'personal_data', reply_to: 'c-1' } },
      { 'c-1': 'Anna 070-123 45 67' }
    );
    expect(s.transcript).toEqual([]);
    expect(s.warnings).toEqual([
      { code: 'personal_data', replyTo: 'c-1', text: 'Anna 070-123 45 67' }
    ]);
    expect(reduce(s, { kind: 'dismissWarning', replyTo: 'c-1' }).warnings).toEqual([]);
  });

  it('error frames are recorded without a run', () => {
    expect(apply([{ type: 'error', code: 'bad_request' }]).error).toEqual({ code: 'bad_request' });
  });

  it('sending clears an earlier error', () => {
    const s = reduce(apply([{ type: 'error', code: 'bad_request' }]), {
      kind: 'sent',
      id: 'c-1',
      text: 'hi'
    });
    expect(s.error).toBeNull();
    expect(s.transcript).toEqual([{ id: 'c-1', role: 'user', text: 'hi' }]);
  });

  it('hydrate replaces the transcript but never lowers the draft version', () => {
    const s = reduce(apply([ready({ draft_version: 5 })]), {
      kind: 'hydrate',
      conversation: conversation({
        transcript: [{ role: 'user', text: 'hi' }],
        draft_version: 4,
        notice_accepted: false
      })
    });
    expect(s.transcript).toEqual([{ role: 'user', text: 'hi' }]);
    expect(s.draftVersion).toBe(5);
    expect(s.noticeRequired).toBe(true);
  });

  it('hydrate keeps text streamed here while the run is still live', () => {
    const live = apply([
      { type: 'run_started', run_id: 'r-1', reply_to: 'c-1' },
      { type: 'text_delta', run_id: 'r-1', text: 'partial' }
    ]);
    const s = reduce(live, { kind: 'hydrate', conversation: conversation({ running: true }) });
    expect(s.transcript[0].text).toBe('partial');
  });
});

describe('backoffDelay and wsUrl', () => {
  it('doubles from 1 s and stops at 15 s', () => {
    expect([0, 1, 2, 3, 4, 5, 9].map(backoffDelay)).toEqual([1000, 2000, 4000, 8000, 15000, 15000, 15000]);
  });
  it('builds the per-event path', () => {
    expect(wsUrl('e1', 'wss://x.test')).toBe('wss://x.test/ws/assistant/events/e1/');
  });
});

describe('createAssistantStore', () => {
  beforeEach(() => {
    FakeSocket.all = [];
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  function setup(fetchConversation = vi.fn(async () => conversation())) {
    const store = createAssistantStore({
      eventId: 'e1',
      url: 'ws://test/ws/assistant/events/e1/',
      createSocket: (u) => new FakeSocket(u),
      fetchConversation
    });
    return { store, fetchConversation };
  }
  const sock = () => FakeSocket.all[FakeSocket.all.length - 1];

  it('connects, reports state and re-reads the conversation on ready', async () => {
    const { store, fetchConversation } = setup(
      vi.fn(async () => conversation({ transcript: [{ role: 'user', text: 'hi' }] }))
    );
    store.connect();
    expect(get(store).connection).toBe('connecting');
    expect(sock().url).toBe('ws://test/ws/assistant/events/e1/');
    sock().open();
    sock().receive(ready());
    await vi.advanceTimersByTimeAsync(0);
    expect(fetchConversation).toHaveBeenCalledTimes(1);
    expect(get(store)).toMatchObject({
      connection: 'open',
      draftVersion: 3,
      transcript: [{ role: 'user', text: 'hi' }]
    });
  });

  it('notifies draft listeners on draft_updated and not after unsubscribe', () => {
    const { store } = setup();
    const seen: number[] = [];
    const off = store.onDraftUpdated((v) => seen.push(v));
    store.connect();
    sock().open();
    sock().receive({ type: 'draft_updated', run_id: 'r', draft_version: 4 });
    off();
    sock().receive({ type: 'draft_updated', run_id: 'r', draft_version: 5 });
    expect(seen).toEqual([4]);
    expect(get(store).draftVersion).toBe(5);
  });

  it('ignores garbage frames', () => {
    const { store } = setup();
    store.connect();
    sock().open();
    sock().receive('not json');
    sock().receive('{"no":"type"}');
    sock().receive('null');
    expect(get(store).connection).toBe('open');
    expect(get(store).error).toBeNull();
  });

  it('sends a user_message with an id and the optimistic entry; the confirm flag only when asked', () => {
    const { store } = setup();
    store.connect();
    sock().open();
    const id = store.send('a camp');
    const again = store.send('a camp', { confirmPersonalData: true });
    // The first send started nothing server side yet, so a second is allowed.
    expect(JSON.parse(sock().sent[0])).toEqual({ type: 'user_message', id, text: 'a camp' });
    expect(JSON.parse(sock().sent[1])).toEqual({
      type: 'user_message',
      id: again,
      text: 'a camp',
      confirm_personal_data: true
    });
    expect(get(store).transcript.map((e) => e.id)).toEqual([id, again]);
  });

  it('does not send while a run is live or the socket is not open', () => {
    const { store } = setup();
    store.connect();
    expect(store.send('too early')).toBeNull();
    sock().open();
    sock().receive(ready({ running: true }));
    expect(store.send('second run')).toBeNull();
    expect(sock().sent).toEqual([]);
  });

  it('cancel sends a cancel frame', () => {
    const { store } = setup();
    store.connect();
    sock().open();
    store.cancel();
    expect(JSON.parse(sock().sent[0])).toEqual({ type: 'cancel' });
  });

  it('reconnects with 1 s, 2 s, 4 s backoff and resets after an open', () => {
    const { store } = setup();
    store.connect();
    sock().open();
    sock().drop();
    expect(get(store).connection).toBe('reconnecting');
    vi.advanceTimersByTime(999);
    expect(FakeSocket.all).toHaveLength(1);
    vi.advanceTimersByTime(1);
    expect(FakeSocket.all).toHaveLength(2);
    sock().drop();
    vi.advanceTimersByTime(1999);
    expect(FakeSocket.all).toHaveLength(2);
    vi.advanceTimersByTime(1);
    expect(FakeSocket.all).toHaveLength(3);
    sock().drop();
    vi.advanceTimersByTime(3999);
    expect(FakeSocket.all).toHaveLength(3);
    vi.advanceTimersByTime(1);
    expect(FakeSocket.all).toHaveLength(4);
    sock().open();
    sock().drop();
    vi.advanceTimersByTime(1000);
    expect(FakeSocket.all).toHaveLength(5);
  });

  it('after reconnecting it re-reads the conversation on ready', async () => {
    const { store, fetchConversation } = setup();
    store.connect();
    sock().open();
    sock().drop();
    vi.advanceTimersByTime(1000);
    sock().open();
    sock().receive(ready());
    await vi.advanceTimersByTimeAsync(0);
    expect(fetchConversation).toHaveBeenCalledTimes(1);
    expect(get(store).connection).toBe('open');
  });

  it.each([4401, 4403, 4404, 4409, 4503])('does not reconnect after a refusal (%i)', (code) => {
    const { store } = setup();
    store.connect();
    sock().drop(code);
    vi.advanceTimersByTime(60000);
    expect(FakeSocket.all).toHaveLength(1);
    expect(get(store)).toMatchObject({ connection: 'refused', refusedCode: code });
  });

  it('disconnect closes without reconnecting and cancels a pending retry', () => {
    const { store } = setup();
    store.connect();
    sock().open();
    sock().drop();
    store.disconnect();
    vi.advanceTimersByTime(60000);
    expect(FakeSocket.all).toHaveLength(1);
    expect(get(store).connection).toBe('closed');

    store.connect();
    const live = sock();
    live.open();
    store.disconnect();
    expect(live.closed).toBe(true);
  });

  it('a late frame from a replaced socket is ignored', () => {
    const { store } = setup();
    store.connect();
    const old = sock();
    old.open();
    old.drop();
    vi.advanceTimersByTime(1000);
    old.receive({ type: 'error', code: 'stale' });
    expect(get(store).error).toBeNull();
  });

  it('re-reads the conversation when a run ends', async () => {
    const { store, fetchConversation } = setup(
      vi.fn(async () => conversation({ transcript: [{ role: 'assistant', text: 'done' }] }))
    );
    store.connect();
    sock().open();
    sock().receive({ type: 'run_started', run_id: 'r', reply_to: 'c-1' });
    sock().receive({ type: 'run_finished', run_id: 'r' });
    await vi.advanceTimersByTimeAsync(0);
    expect(fetchConversation).toHaveBeenCalledTimes(1);
    expect(get(store).transcript).toEqual([{ role: 'assistant', text: 'done' }]);
  });

  it('keeps going when the HTTP re-read fails', async () => {
    const { store } = setup(vi.fn(async () => Promise.reject(new Error('net'))));
    store.connect();
    sock().open();
    sock().receive(ready());
    await vi.advanceTimersByTimeAsync(0);
    expect(get(store).connection).toBe('open');
  });
});
