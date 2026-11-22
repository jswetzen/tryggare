/**
 * Per-event assistant socket and state. `reduce` is pure (unit-tested without
 * a socket); `createAssistantStore` owns the socket, backoff and HTTP refresh.
 * The WebSocket carries progress only: transcript text is re-read over HTTP
 * after each run and on every (re)connect.
 */
import { writable, get, type Readable } from 'svelte/store';
import type {
  ClientFrame,
  ConversationState,
  FeatureRequestCard,
  FeatureRequestDraft,
  RunFailedCode,
  ServerEvent,
  TranscriptEntry
} from './types';
import { REFUSED_CLOSE_CODES } from './types';

export type ConnectionState = 'idle' | 'connecting' | 'open' | 'reconnecting' | 'refused' | 'closed';

export interface ChatEntry extends TranscriptEntry {
  // Set on a message typed in this tab and on text streamed during a run.
  id?: string;
  runId?: string;
}

export interface ToolStatus {
  callId: string;
  tool: string;
  state: 'running' | 'done' | 'failed';
}

export interface AssistantWarning {
  code: 'personal_data';
  replyTo: string;
  // What the organizer typed, so the UI can offer "Send anyway".
  text: string;
}

export interface AssistantError {
  code: RunFailedCode | string;
  replyTo?: string;
}

export interface AssistantState {
  connection: ConnectionState;
  // The close code of a refusal before accept (4401 ... 4503), else null.
  refusedCode: number | null;
  conversationId: string | null;
  running: boolean;
  noticeRequired: boolean;
  draftVersion: number;
  transcript: ChatEntry[];
  runId: string | null;
  tools: ToolStatus[];
  warnings: AssistantWarning[];
  error: AssistantError | null;
  // Pending drafts from the GET and the event, plus cards settled in this tab.
  featureRequests: FeatureRequestCard[];
}

export const initialState = (): AssistantState => ({
  connection: 'idle',
  refusedCode: null,
  conversationId: null,
  running: false,
  noticeRequired: false,
  draftVersion: 0,
  transcript: [],
  runId: null,
  tools: [],
  warnings: [],
  error: null,
  featureRequests: []
});

export type Action =
  | { kind: 'server'; event: ServerEvent }
  | { kind: 'connection'; connection: ConnectionState; refusedCode?: number | null }
  | { kind: 'sent'; id: string; text: string }
  | { kind: 'hydrate'; conversation: ConversationState }
  | { kind: 'noticeAccepted' }
  | { kind: 'dismissWarning'; replyTo: string }
  | { kind: 'featureRequestsLoaded'; drafts: FeatureRequestDraft[] }
  | { kind: 'featureRequestSettled'; id: string; outcome: 'confirmed' | 'duplicate'; duplicate_of: string | null; title?: string }
  | { kind: 'featureRequestRemoved'; id: string }
  | { kind: 'featureReceiptsCleared' };

// A message typed here that the server refused before a run existed was never
// stored, so it leaves the transcript (its text lives on in the warning).
const without = (list: ChatEntry[], id?: string) =>
  id ? list.filter((e) => e.id !== id) : list;

// Replaces the card with the same id, or appends it. A settled card is never
// reopened by a late draft event or GET.
function upsertCard(list: FeatureRequestCard[], card: FeatureRequestCard): FeatureRequestCard[] {
  const i = list.findIndex((c) => c.id === card.id);
  if (i === -1) return [...list, card];
  if (list[i].outcome) return list;
  return list.map((c, j) => (j === i ? { ...c, ...card } : c));
}

// The GET lists pending drafts only, so settled cards are kept here and the
// pending ones are exactly what the server said.
function loadedCards(current: FeatureRequestCard[], drafts: FeatureRequestDraft[]): FeatureRequestCard[] {
  const settled = current.filter((c) => c.outcome);
  const settledIds = new Set(settled.map((c) => c.id));
  const pending = drafts
    .filter((d) => !settledIds.has(d.id))
    .map((d) => ({ ...current.find((c) => c.id === d.id), ...d }));
  return [...pending, ...settled];
}

function appendDelta(list: ChatEntry[], runId: string, text: string): ChatEntry[] {
  const last = list[list.length - 1];
  if (last && last.role === 'assistant' && last.runId === runId) {
    return [...list.slice(0, -1), { ...last, text: last.text + text }];
  }
  return [...list, { role: 'assistant', text, runId }];
}

export function reduce(
  state: AssistantState,
  action: Action,
  sent: Record<string, string> = {}
): AssistantState {
  switch (action.kind) {
    case 'connection':
      return {
        ...state,
        connection: action.connection,
        refusedCode: action.refusedCode ?? (action.connection === 'refused' ? state.refusedCode : null)
      };
    case 'sent':
      return {
        ...state,
        error: null,
        transcript: [...state.transcript, { id: action.id, role: 'user', text: action.text }]
      };
    case 'noticeAccepted':
      return { ...state, noticeRequired: false };
    case 'dismissWarning':
      return { ...state, warnings: state.warnings.filter((w) => w.replyTo !== action.replyTo) };
    case 'featureRequestsLoaded':
      return { ...state, featureRequests: loadedCards(state.featureRequests, action.drafts) };
    case 'featureRequestSettled':
      return {
        ...state,
        featureRequests: state.featureRequests.map((c) =>
          // The confirm response has no title: an edited one is the one the server stored.
          c.id === action.id
            ? { ...c, outcome: action.outcome, duplicate_of: action.duplicate_of, title: action.title ?? c.title }
            : c
        )
      };
    case 'featureRequestRemoved':
      return { ...state, featureRequests: state.featureRequests.filter((c) => c.id !== action.id) };
    case 'featureReceiptsCleared':
      return { ...state, featureRequests: state.featureRequests.filter((c) => !c.outcome) };
    case 'hydrate': {
      const c = action.conversation;
      // Keep text streamed in this tab while a run is live: the server only
      // stores it when the run ends.
      const live = state.running && c.running;
      return {
        ...state,
        conversationId: c.conversation_id ?? state.conversationId,
        running: c.running,
        runId: c.running ? state.runId : null,
        tools: c.running ? state.tools : [],
        noticeRequired: !c.notice_accepted,
        draftVersion: Math.max(state.draftVersion, c.draft_version),
        transcript: live ? state.transcript : c.transcript.map((e) => ({ ...e }))
      };
    }
    case 'server':
      break;
  }

  const e = action.event;
  switch (e.type) {
    case 'ready':
      return {
        ...state,
        connection: 'open',
        conversationId: e.conversation_id,
        running: e.running,
        // A run that ended while disconnected leaves no run_finished behind.
        runId: e.running ? state.runId : null,
        tools: e.running ? state.tools : [],
        noticeRequired: e.notice_required,
        draftVersion: e.draft_version,
        error: null
      };
    case 'run_started':
      return { ...state, running: true, runId: e.run_id, tools: [], error: null };
    case 'tool_started':
      if (state.tools.some((t) => t.callId === e.call_id)) return state;
      return {
        ...state,
        tools: [...state.tools, { callId: e.call_id, tool: e.tool, state: 'running' }]
      };
    case 'tool_finished':
      return {
        ...state,
        tools: state.tools.map((t) =>
          t.callId === e.call_id ? { ...t, state: e.ok ? 'done' : 'failed' } : t
        )
      };
    case 'text_delta':
      return { ...state, transcript: appendDelta(state.transcript, e.run_id, e.text) };
    case 'draft_updated':
      return { ...state, draftVersion: e.draft_version };
    case 'feature_request_draft': {
      const { type: _type, run_id: _run, ...preview } = e;
      return { ...state, featureRequests: upsertCard(state.featureRequests, preview) };
    }
    case 'run_finished':
      return { ...state, running: false, runId: null, tools: [] };
    case 'run_failed': {
      const refusedBeforeRun = e.run_id === null;
      return {
        ...state,
        // A refusal before a run exists must not clear a run that is live.
        running: refusedBeforeRun ? state.running : false,
        runId: refusedBeforeRun ? state.runId : null,
        tools: refusedBeforeRun ? state.tools : [],
        transcript: refusedBeforeRun ? without(state.transcript, e.reply_to) : state.transcript,
        error: { code: e.code, replyTo: e.reply_to }
      };
    }
    case 'warning':
      return {
        ...state,
        transcript: without(state.transcript, e.reply_to),
        warnings: [
          ...state.warnings.filter((w) => w.replyTo !== e.reply_to),
          { code: e.code, replyTo: e.reply_to, text: sent[e.reply_to] ?? '' }
        ]
      };
    case 'error':
      return { ...state, error: { code: e.code } };
  }
  return state;
}

// --- socket

export interface SocketLike {
  readyState: number;
  send(data: string): void;
  close(code?: number): void;
  onopen: ((ev?: unknown) => void) | null;
  onmessage: ((ev: { data: unknown }) => void) | null;
  onclose: ((ev: { code: number }) => void) | null;
  onerror: ((ev?: unknown) => void) | null;
}

const OPEN = 1;

// HTTP status of the conversation endpoint -> the close code the consumer uses.
const REFUSAL_BY_STATUS: Record<number, number> = {
  401: 4401,
  403: 4403,
  404: 4404,
  409: 4409,
  503: 4503
};
export const BACKOFF_START_MS = 1000;
export const BACKOFF_MAX_MS = 15000;

export const backoffDelay = (attempt: number): number =>
  Math.min(BACKOFF_START_MS * 2 ** attempt, BACKOFF_MAX_MS);

export function wsUrl(eventId: string, base?: string): string {
  const root =
    base ??
    (import.meta.env.VITE_PUBLIC_WS_BASE_URL ||
      (typeof window !== 'undefined'
        ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`
        : 'ws://localhost:8000'));
  return `${root}/ws/assistant/events/${encodeURIComponent(eventId)}/`;
}

export interface AssistantStoreOptions {
  eventId: string;
  createSocket?: (url: string) => SocketLike;
  // Re-reads the conversation over HTTP (transcript is not carried by the WS).
  fetchConversation?: () => Promise<ConversationState>;
  // The organizer's pending feature request drafts on this event.
  fetchFeatureRequests?: () => Promise<FeatureRequestDraft[]>;
  url?: string;
}

export interface AssistantStore extends Readable<AssistantState> {
  connect(): void;
  disconnect(): void;
  /** Returns the frame id, or null when nothing was sent (not connected, or a run is live). */
  send(text: string, opts?: { confirmPersonalData?: boolean }): string | null;
  cancel(): void;
  acceptedNotice(): void;
  dismissWarning(replyTo: string): void;
  refresh(): Promise<void>;
  /** Called on every `draft_updated`; returns an unsubscribe. */
  onDraftUpdated(fn: (draftVersion: number) => void): () => void;
  /** An organizer's Confirm or merge succeeded: the card shows its receipt. */
  featureRequestSettled(id: string, outcome: 'confirmed' | 'duplicate', duplicateOf: string | null, title?: string): void;
  /** Discarded (or gone on the server): the card leaves the chat. */
  featureRequestRemoved(id: string): void;
  /** Clear conversation: receipts go; pending drafts stay (the server keeps them). */
  clearFeatureReceipts(): void;
}

export function createAssistantStore(opts: AssistantStoreOptions): AssistantStore {
  const store = writable<AssistantState>(initialState());
  const sent: Record<string, string> = {};
  const draftListeners = new Set<(v: number) => void>();
  let socket: SocketLike | null = null;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let attempt = 0;
  let wanted = false;
  let counter = 0;
  // Bumped on connect/disconnect, so a probe answering late is ignored.
  let generation = 0;
  // A re-read is applied only if it is the newest one and no run started or
  // ended after it was asked for: an older answer would undo the newer state
  // (e.g. `running: false` landing after `run_started`).
  let refreshSeq = 0;
  let runEpoch = 0;
  // Same rule for the feature request list. Settling or removing a card bumps
  // it too, so a GET sent before the organizer's click cannot bring the card back.
  let featureSeq = 0;

  const dispatch = (a: Action) => store.update((s) => reduce(s, a, sent));

  async function refreshConversation() {
    if (!opts.fetchConversation) return;
    const seq = ++refreshSeq;
    const epoch = runEpoch;
    try {
      const conversation = await opts.fetchConversation();
      if (seq === refreshSeq && epoch === runEpoch) dispatch({ kind: 'hydrate', conversation });
    } catch {
      // The socket state stays; the next run end or reconnect tries again.
    }
  }

  async function refreshFeatureRequests() {
    if (!opts.fetchFeatureRequests) return;
    const seq = ++featureSeq;
    try {
      const drafts = await opts.fetchFeatureRequests();
      if (seq === featureSeq) dispatch({ kind: 'featureRequestsLoaded', drafts });
    } catch {
      // Cards already shown stay; the next run end, reconnect or clear asks again.
    }
  }

  async function refresh() {
    await Promise.all([refreshConversation(), refreshFeatureRequests()]);
  }

  function retry() {
    dispatch({ kind: 'connection', connection: 'reconnecting' });
    timer = setTimeout(open, backoffDelay(attempt));
    attempt += 1;
  }

  function refuse(code: number) {
    wanted = false;
    dispatch({ kind: 'connection', connection: 'refused', refusedCode: code });
  }

  function open() {
    timer = null;
    dispatch({ kind: 'connection', connection: attempt === 0 ? 'connecting' : 'reconnecting' });
    const ws = (opts.createSocket ?? ((u) => new WebSocket(u) as unknown as SocketLike))(
      opts.url ?? wsUrl(opts.eventId)
    );
    socket = ws;
    let opened = false;
    ws.onopen = () => {
      if (socket !== ws) return;
      opened = true;
      attempt = 0;
      dispatch({ kind: 'connection', connection: 'open' });
    };
    ws.onmessage = (ev) => {
      if (socket !== ws) return;
      let event: ServerEvent;
      try {
        event = JSON.parse(String(ev.data));
      } catch {
        return;
      }
      if (!event || typeof event.type !== 'string') return;
      if (
        event.type === 'ready' ||
        event.type === 'run_started' ||
        event.type === 'run_finished' ||
        (event.type === 'run_failed' && event.run_id !== null)
      ) {
        runEpoch += 1;
      }
      dispatch({ kind: 'server', event });
      if (event.type === 'ready' || event.type === 'run_finished' || event.type === 'run_failed') {
        void refresh();
      }
      if (event.type === 'draft_updated') {
        const version = event.draft_version;
        draftListeners.forEach((fn) => fn(version));
      }
      // The event carries only a preview; the GET brings tried, touches and severity.
      if (event.type === 'feature_request_draft') void refreshFeatureRequests();
    };
    ws.onerror = () => {};
    ws.onclose = (ev) => {
      if (socket !== ws) return;
      socket = null;
      if (!wanted) {
        dispatch({ kind: 'connection', connection: 'closed' });
        return;
      }
      if (REFUSED_CLOSE_CODES.includes(ev.code)) {
        refuse(ev.code);
        return;
      }
      // Daphne turns a close before accept into an HTTP 403, so browsers see
      // 1006, not 44xx: a socket that never opened asks the HTTP endpoint why.
      if (!opened && opts.fetchConversation) {
        const gen = generation;
        dispatch({ kind: 'connection', connection: 'reconnecting' });
        opts.fetchConversation().then(
          () => gen === generation && retry(),
          (err) => {
            if (gen !== generation) return;
            const code = REFUSAL_BY_STATUS[(err as { status?: number } | null)?.status ?? -1];
            if (code) refuse(code);
            else retry();
          }
        );
        return;
      }
      retry();
    };
  }

  const transmit = (frame: ClientFrame): boolean => {
    if (!socket || socket.readyState !== OPEN) return false;
    socket.send(JSON.stringify(frame));
    return true;
  };

  return {
    subscribe: store.subscribe,
    connect() {
      if (wanted) return;
      generation += 1;
      wanted = true;
      attempt = 0;
      open();
    },
    disconnect() {
      generation += 1;
      wanted = false;
      if (timer) clearTimeout(timer);
      timer = null;
      const ws = socket;
      socket = null;
      ws?.close();
      dispatch({ kind: 'connection', connection: 'closed' });
    },
    send(text, o = {}) {
      if (get(store).running) return null;
      const id = `c-${++counter}`;
      const frame: ClientFrame = { type: 'user_message', id, text };
      if (o.confirmPersonalData) frame.confirm_personal_data = true;
      if (!transmit(frame)) return null;
      sent[id] = text;
      dispatch({ kind: 'sent', id, text });
      return id;
    },
    cancel() {
      transmit({ type: 'cancel' });
    },
    acceptedNotice() {
      dispatch({ kind: 'noticeAccepted' });
    },
    dismissWarning(replyTo) {
      dispatch({ kind: 'dismissWarning', replyTo });
    },
    refresh,
    onDraftUpdated(fn) {
      draftListeners.add(fn);
      return () => draftListeners.delete(fn);
    },
    featureRequestSettled(id, outcome, duplicateOf, title) {
      featureSeq += 1;
      dispatch({ kind: 'featureRequestSettled', id, outcome, duplicate_of: duplicateOf, title });
    },
    featureRequestRemoved(id) {
      featureSeq += 1;
      dispatch({ kind: 'featureRequestRemoved', id });
    },
    clearFeatureReceipts() {
      featureSeq += 1;
      dispatch({ kind: 'featureReceiptsCleared' });
    }
  };
}
