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
  error: null
});

export type Action =
  | { kind: 'server'; event: ServerEvent }
  | { kind: 'connection'; connection: ConnectionState; refusedCode?: number | null }
  | { kind: 'sent'; id: string; text: string }
  | { kind: 'hydrate'; conversation: ConversationState }
  | { kind: 'noticeAccepted' }
  | { kind: 'dismissWarning'; replyTo: string };

// A message typed here that the server refused before a run existed was never
// stored, so it leaves the transcript (its text lives on in the warning).
const without = (list: ChatEntry[], id?: string) =>
  id ? list.filter((e) => e.id !== id) : list;

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
    case 'hydrate': {
      const c = action.conversation;
      // Keep text streamed in this tab while a run is live: the server only
      // stores it when the run ends.
      const live = state.running && c.running;
      return {
        ...state,
        conversationId: c.conversation_id ?? state.conversationId,
        running: c.running,
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
        noticeRequired: e.notice_required,
        draftVersion: e.draft_version,
        error: null
      };
    case 'run_started':
      return { ...state, running: true, runId: e.run_id, tools: [], error: null };
    case 'tool_started':
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

  const dispatch = (a: Action) => store.update((s) => reduce(s, a, sent));

  async function refresh() {
    if (!opts.fetchConversation) return;
    try {
      dispatch({ kind: 'hydrate', conversation: await opts.fetchConversation() });
    } catch {
      // The socket state stays; the next run end or reconnect tries again.
    }
  }

  function open() {
    timer = null;
    dispatch({ kind: 'connection', connection: attempt === 0 ? 'connecting' : 'reconnecting' });
    const ws = (opts.createSocket ?? ((u) => new WebSocket(u) as unknown as SocketLike))(
      opts.url ?? wsUrl(opts.eventId)
    );
    socket = ws;
    ws.onopen = () => {
      if (socket !== ws) return;
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
      dispatch({ kind: 'server', event });
      if (event.type === 'ready' || event.type === 'run_finished' || event.type === 'run_failed') {
        void refresh();
      }
      if (event.type === 'draft_updated') {
        const version = event.draft_version;
        draftListeners.forEach((fn) => fn(version));
      }
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
        wanted = false;
        dispatch({ kind: 'connection', connection: 'refused', refusedCode: ev.code });
        return;
      }
      dispatch({ kind: 'connection', connection: 'reconnecting' });
      timer = setTimeout(open, backoffDelay(attempt));
      attempt += 1;
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
      wanted = true;
      attempt = 0;
      open();
    },
    disconnect() {
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
    }
  };
}
