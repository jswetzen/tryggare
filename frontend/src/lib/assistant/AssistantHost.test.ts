/**
 * The floating chat, driven through the real store over a fake socket.
 * Plan: docs/event-assistant-plan.md, "Accessibility" and "Visual design".
 */
import { tick } from 'svelte';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import en from '$lib/i18n/locales/en.json';
import AssistantHost from './AssistantHost.svelte';
import { createAssistantStore, type AssistantStore, type SocketLike } from './assistantStore';
import type { ConversationState, DraftPayload, ServerEvent } from './types';

vi.mock('svelte-i18n', () => {
  const lookup = (key: string): string | undefined =>
    key.split('.').reduce<unknown>((o, k) => (o as Record<string, unknown> | undefined)?.[k], en) as
      | string
      | undefined;
  const translator = (key: string, opts?: { values?: Record<string, unknown> }) =>
    (lookup(key) ?? key).replace(/\{(\w+)\}/g, (_, n) => String(opts?.values?.[n] ?? ''));
  const store = { subscribe: (cb: (v: typeof translator) => void) => (cb(translator), () => {}) };
  return { t: store, _: store, locale: { subscribe: (cb: (v: string) => void) => (cb('en'), () => {}) } };
});

const api = vi.hoisted(() => ({
  getDraft: vi.fn(),
  applySpec: vi.fn(),
  discardDraft: vi.fn(),
  clearConversation: vi.fn(),
  acceptNotice: vi.fn(),
  getConversation: vi.fn()
}));
vi.mock('$lib/api/assistantService', () => ({ assistantApi: api }));

class FakeSocket implements SocketLike {
  static last: FakeSocket;
  readyState = 1;
  sent: string[] = [];
  onopen: SocketLike['onopen'] = null;
  onmessage: SocketLike['onmessage'] = null;
  onclose: SocketLike['onclose'] = null;
  onerror: SocketLike['onerror'] = null;
  constructor() {
    FakeSocket.last = this;
  }
  send(d: string) {
    this.sent.push(d);
  }
  close() {}
  receive(e: ServerEvent) {
    this.onmessage?.({ data: JSON.stringify(e) });
  }
  frames() {
    return this.sent.map((s) => JSON.parse(s));
  }
}

const conversation = (over: Partial<ConversationState> = {}): ConversationState => ({
  available: true,
  conversation_id: 'c1',
  transcript: [],
  running: false,
  notice_accepted: true,
  draft_version: 0,
  ...over
});
const ready = (over: Partial<Extract<ServerEvent, { type: 'ready' }>> = {}): ServerEvent => ({
  type: 'ready',
  conversation_id: 'c1',
  running: false,
  draft_version: 0,
  notice_required: false,
  ...over
});
const draft = (over: Partial<DraftPayload> = {}): DraftPayload => ({
  spec: { event_spec_version: 1 },
  diff: [
    { kind: 'ticket_types', key: 'sat', change: 'added', new: { name: 'Saturday workshop', price: '200.00' } },
    { kind: 'event', key: null, change: 'changed', fields: { name: { old: 'A', new: 'B' } } }
  ],
  warnings: [],
  stale: false,
  token: 'tok',
  version: 4,
  ...over
});

let store: AssistantStore;
let reload: ReturnType<typeof vi.fn<() => Promise<void>>>;

async function mount(opts: { open?: boolean; ready?: ServerEvent; conv?: ConversationState; props?: object } = {}) {
  api.getConversation.mockResolvedValue(opts.conv ?? conversation());
  store = createAssistantStore({
    eventId: 'e1',
    createSocket: () => new FakeSocket(),
    fetchConversation: () => api.getConversation('e1')
  });
  store.connect();
  FakeSocket.last.onopen?.();
  FakeSocket.last.receive(opts.ready ?? ready());
  reload = vi.fn<() => Promise<void>>().mockResolvedValue(undefined);
  if (opts.open) (localStorage.getItem as ReturnType<typeof vi.fn>).mockReturnValue('{"open":true}');
  const view = render(AssistantHost, { eventId: 'e1', store, reload, ...opts.props });
  await waitFor(() => expect(api.getConversation).toHaveBeenCalled());
  return view;
}
const status = () => screen.getByTestId('assistant-status');

beforeEach(() => {
  vi.clearAllMocks();
  api.getDraft.mockRejectedValue({ status: 404 });
  api.discardDraft.mockResolvedValue({});
  api.applySpec.mockResolvedValue({});
  api.clearConversation.mockResolvedValue({});
  api.acceptNotice.mockResolvedValue({ notice_accepted: true });
  document.body.style.paddingInlineEnd = '';
});

describe('launcher and panel', () => {
  it('starts minimized by default, as a labelled button that controls the panel', async () => {
    await mount();
    const launcher = screen.getByRole('button', { name: 'Open assistant' });
    expect(launcher).toHaveAttribute('aria-expanded', 'false');
    expect(launcher).toHaveAttribute('aria-controls', 'assistant-panel');
    expect(screen.queryByTestId('assistant-panel')).toBeNull();
  });

  it('opens on click, moves focus to the composer and remembers it', async () => {
    const user = userEvent.setup();
    await mount();
    await user.click(screen.getByTestId('assistant-launcher'));
    const panel = screen.getByRole('region', { name: 'Setup assistant' });
    expect(panel).toBeInTheDocument();
    expect(screen.getByLabelText('Describe what you want')).toHaveFocus();
    expect(localStorage.setItem).toHaveBeenLastCalledWith('assistant.ui.e1', '{"open":true}');
  });

  it('restores an open panel from storage without stealing focus', async () => {
    await mount({ open: true });
    expect(screen.getByTestId('assistant-panel')).toBeInTheDocument();
    expect(screen.getByLabelText('Describe what you want')).not.toHaveFocus();
  });

  it('stores only {open}, never message text', async () => {
    const user = userEvent.setup();
    await mount({ open: true });
    await user.type(screen.getByLabelText('Describe what you want'), 'secret words{Enter}');
    const written = (localStorage.setItem as ReturnType<typeof vi.fn>).mock.calls.map((c) => c[1]).join();
    expect(written).not.toContain('secret');
  });

  it('Escape minimizes and returns focus to the launcher', async () => {
    const user = userEvent.setup();
    await mount({ open: true });
    await user.click(screen.getByLabelText('Describe what you want'));
    await user.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByTestId('assistant-panel')).toBeNull());
    expect(screen.getByTestId('assistant-launcher')).toHaveFocus();
  });

  it('the minimize button does the same', async () => {
    const user = userEvent.setup();
    await mount({ open: true });
    await user.click(screen.getByRole('button', { name: 'Minimize assistant' }));
    expect(screen.getByTestId('assistant-launcher')).toHaveFocus();
  });

  it('does not trap focus: the page behind stays reachable', async () => {
    const outside = document.createElement('input');
    document.body.appendChild(outside);
    await mount({ open: true });
    outside.focus();
    expect(outside).toHaveFocus();
    expect(screen.getByTestId('assistant-panel')).toBeInTheDocument();
    outside.remove();
  });

  it('shows a dot when a run finishes while minimized, and clears it on open', async () => {
    const user = userEvent.setup();
    await mount();
    FakeSocket.last.receive({ type: 'run_started', run_id: 'r1', reply_to: 'c-1' });
    await tick();
    FakeSocket.last.receive({ type: 'run_finished', run_id: 'r1' });
    expect(await screen.findByTestId('assistant-unread')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /New reply/ })).toBeInTheDocument();
    await user.click(screen.getByTestId('assistant-launcher'));
    expect(screen.queryByTestId('assistant-unread')).toBeNull();
  });
});

describe('notice gate', () => {
  it('shows the notice first, keeps the composer off, and focuses Accept on open', async () => {
    const user = userEvent.setup();
    await mount({ ready: ready({ notice_required: true }), conv: conversation({ notice_accepted: false }) });
    await user.click(screen.getByTestId('assistant-launcher'));
    const accept = screen.getByRole('button', { name: 'I understand' });
    expect(accept).toHaveFocus();
    expect(screen.getByLabelText('Describe what you want')).toBeDisabled();
    expect(screen.queryByTestId('assistant-empty')).toBeNull();
  });

  it('posts the acceptance, then enables the composer', async () => {
    const user = userEvent.setup();
    await mount({ open: true, ready: ready({ notice_required: true }), conv: conversation({ notice_accepted: false }) });
    await user.click(screen.getByRole('button', { name: 'I understand' }));
    expect(api.acceptNotice).toHaveBeenCalledWith('e1');
    await waitFor(() => expect(screen.getByLabelText('Describe what you want')).toBeEnabled());
    expect(screen.queryByTestId('assistant-notice')).toBeNull();
  });

  it('keeps the notice when the acceptance fails', async () => {
    const user = userEvent.setup();
    api.acceptNotice.mockRejectedValue({ status: 500 });
    await mount({ open: true, ready: ready({ notice_required: true }), conv: conversation({ notice_accepted: false }) });
    await user.click(screen.getByRole('button', { name: 'I understand' }));
    expect(await screen.findByText(en.assistant.notice.failed)).toBeInTheDocument();
    expect(screen.getByLabelText('Describe what you want')).toBeDisabled();
  });
});

describe('composer', () => {
  it('Send is disabled while empty; Enter sends, Shift+Enter does not', async () => {
    const user = userEvent.setup();
    await mount({ open: true });
    const input = screen.getByLabelText('Describe what you want');
    const send = screen.getByRole('button', { name: 'Send' });
    expect(send).toBeDisabled();
    await user.type(input, 'two day camp{Shift>}{Enter}{/Shift}more');
    expect(FakeSocket.last.frames()).toHaveLength(0);
    expect((input as HTMLTextAreaElement).value).toContain('\n');
    await user.keyboard('{Enter}');
    const frames = FakeSocket.last.frames();
    expect(frames).toHaveLength(1);
    expect(frames[0]).toMatchObject({ type: 'user_message', text: 'two day camp\nmore' });
    expect((input as HTMLTextAreaElement).value).toBe('');
  });

  it('an example fills the composer without sending', async () => {
    const user = userEvent.setup();
    await mount({ open: true });
    await user.click(screen.getByRole('button', { name: en.assistant.empty['2'] }));
    expect(screen.getByLabelText('Describe what you want')).toHaveValue(en.assistant.empty['2']);
    expect(FakeSocket.last.frames()).toHaveLength(0);
  });

  it('the first open state is designed: heading, three examples', async () => {
    await mount({ open: true });
    const empty = screen.getByTestId('assistant-empty');
    expect(within(empty).getAllByRole('button')).toHaveLength(3);
  });
});

describe('a run', () => {
  async function startRun() {
    const user = userEvent.setup();
    await mount({ open: true });
    await user.type(screen.getByLabelText('Describe what you want'), 'add a workshop{Enter}');
    const sock = FakeSocket.last;
    const id = sock.frames()[0].id;
    sock.receive({ type: 'run_started', run_id: 'r1', reply_to: id });
    return { user, sock };
  }

  it('shows the message, tool chips by name only, streamed text, and a Stop button', async () => {
    const { sock } = await startRun();
    sock.receive({ type: 'tool_started', run_id: 'r1', call_id: 't-1', tool: 'get_current_spec' });
    sock.receive({ type: 'tool_started', run_id: 'r1', call_id: 't-2', tool: 'validate_spec' });
    sock.receive({ type: 'tool_finished', run_id: 'r1', call_id: 't-1', tool: 'get_current_spec', ok: true });
    sock.receive({ type: 'text_delta', run_id: 'r1', text: 'Adding ' });
    sock.receive({ type: 'text_delta', run_id: 'r1', text: 'it.' });

    expect(await screen.findByText('Reading the current setup')).toBeInTheDocument();
    expect(screen.getByText('Checking the draft')).toBeInTheDocument();
    const log = screen.getByRole('log');
    expect(log).toHaveAttribute('aria-busy', 'true');
    expect(within(log).getByText(/add a workshop/)).toBeInTheDocument();
    expect(within(log).getByText(/Adding it\./)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Stop' })).toBeInTheDocument();
    expect(status()).toHaveTextContent('Working on it…');
  });

  it('Stop sends cancel', async () => {
    const { user, sock } = await startRun();
    await user.click(screen.getByRole('button', { name: 'Stop' }));
    expect(sock.frames().at(-1)).toEqual({ type: 'cancel' });
  });

  it('does not announce what the page announces: no "draft updated" in the chat status', async () => {
    const { sock } = await startRun();
    sock.receive({ type: 'draft_updated', run_id: 'r1', draft_version: 4 });
    sock.receive({ type: 'run_finished', run_id: 'r1' });
    await waitFor(() => expect(status()).toHaveTextContent(''));
    expect(status().textContent?.trim()).toBe('');
    expect(screen.queryByText('Preview updated')).toBeNull();
    expect(within(screen.getByRole('log')).queryByText(/Draft updated/i)).toBeNull();
  });

  it('joining a run in progress shows the working state and never offers a second send', async () => {
    await mount({ open: true, ready: ready({ running: true }), conv: conversation({ running: true }) });
    expect(screen.getByTestId('assistant-working')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Stop' })).toBeInTheDocument();
    expect(store.send('again')).toBeNull();
  });

  it('keeps the page reload hook wired through draft_updated', async () => {
    const seen = vi.fn();
    await mount({ open: true });
    store.onDraftUpdated(seen);
    FakeSocket.last.receive({ type: 'draft_updated', run_id: 'r1', draft_version: 5 });
    expect(seen).toHaveBeenCalledWith(5);
  });
});

describe('errors and refusals', () => {
  const codes = [
    'rate_limited', 'not_enabled', 'busy', 'notice_required', 'blocked', 'timeout', 'limit',
    'model_error', 'auth_failed', 'provider_unreachable', 'cancelled'
  ] as const;

  it.each(codes)('maps %s to its own message, never raw text', async (code) => {
    await mount({ open: true });
    FakeSocket.last.receive({ type: 'run_failed', run_id: 'r1', code });
    const box = await screen.findByTestId('assistant-error');
    expect(box).toHaveTextContent(en.assistant.error[code]);
    expect(status()).toHaveTextContent(en.assistant.error[code]);
  });

  it('falls back to a generic line for a code it does not know', async () => {
    await mount({ open: true });
    FakeSocket.last.receive({ type: 'error', code: '<b>weird</b>' });
    expect(await screen.findByTestId('assistant-error')).toHaveTextContent(en.assistant.error.unknown);
    expect(screen.queryByText(/weird/)).toBeNull();
  });

  it('offers a retry for a transient failure, which resends the last message', async () => {
    const user = userEvent.setup();
    await mount({ open: true });
    await user.type(screen.getByLabelText('Describe what you want'), 'hello{Enter}');
    FakeSocket.last.receive({ type: 'run_started', run_id: 'r1', reply_to: 'c-1' });
    FakeSocket.last.receive({ type: 'run_failed', run_id: 'r1', code: 'timeout' });
    await user.click(await screen.findByRole('button', { name: 'Try again' }));
    expect(FakeSocket.last.frames().at(-1)).toMatchObject({ type: 'user_message', text: 'hello' });
  });

  it('offers no retry for blocked', async () => {
    await mount({ open: true });
    FakeSocket.last.receive({ type: 'run_failed', run_id: null, reply_to: 'c-9', code: 'blocked' });
    await screen.findByTestId('assistant-error');
    expect(screen.queryByRole('button', { name: 'Try again' })).toBeNull();
  });

  it.each([
    [4403, en.assistant.unavailable.forbidden],
    [4409, en.assistant.unavailable.blocked],
    [4503, en.assistant.unavailable.notEnabled],
    [4401, en.assistant.unavailable.unauthenticated]
  ])('a socket refused with %s shows the reason and no composer', async (code, text) => {
    api.getConversation.mockResolvedValue(conversation());
    await mount({ open: true });
    FakeSocket.last.onclose?.({ code });
    const box = await screen.findByTestId('assistant-unavailable');
    expect(box).toHaveTextContent(text);
    expect(screen.queryByLabelText('Describe what you want')).toBeNull();
  });

  it('says it is reconnecting and holds Send while offline', async () => {
    const user = userEvent.setup();
    await mount({ open: true });
    FakeSocket.last.onclose?.({ code: 1006 });
    await waitFor(() => expect(screen.getByTestId('assistant-offline')).toBeInTheDocument());
    await user.type(screen.getByLabelText('Describe what you want'), 'x');
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled();
  });
});

describe('composer after the first message', () => {
  it('asks for a change instead of showing the first-run example, and drops the key hint', async () => {
    await mount({ open: true, conv: conversation({ transcript: [{ role: 'user', text: 'hi' }] }) });
    const input = await screen.findByLabelText('Describe what you want');
    await waitFor(() => expect(input).toHaveAttribute('placeholder', en.assistant.input.placeholderFollowUp));
    expect(screen.queryByText(en.assistant.input.hint)).toBeNull();
  });

  it('a refused chat still gets focus inside the panel on open', async () => {
    const user = userEvent.setup();
    await mount();
    FakeSocket.last.onclose?.({ code: 4409 });
    await user.click(screen.getByTestId('assistant-launcher'));
    expect(screen.getByTestId('assistant-minimize')).toHaveFocus();
  });
});

describe('personal data warning', () => {
  async function warned() {
    const user = userEvent.setup();
    await mount({ open: true });
    await user.type(screen.getByLabelText('Describe what you want'), 'call 070-123 45 67{Enter}');
    const id = FakeSocket.last.frames()[0].id;
    FakeSocket.last.receive({ type: 'warning', code: 'personal_data', reply_to: id });
    await screen.findByTestId('assistant-pii');
    return { user, id };
  }

  it('warns, and "Send anyway" resends the same text with the confirmation', async () => {
    const { user } = await warned();
    expect(status()).toHaveTextContent(en.assistant.piiWarning);
    await user.click(screen.getByRole('button', { name: 'Send anyway' }));
    expect(FakeSocket.last.frames().at(-1)).toMatchObject({
      type: 'user_message',
      text: 'call 070-123 45 67',
      confirm_personal_data: true
    });
    expect(screen.queryByTestId('assistant-pii')).toBeNull();
  });

  it('"Edit message" puts the text back in the composer', async () => {
    const { user } = await warned();
    await user.click(screen.getByRole('button', { name: 'Edit message' }));
    expect(screen.getByLabelText('Describe what you want')).toHaveValue('call 070-123 45 67');
    expect(FakeSocket.last.frames()).toHaveLength(1);
  });
});

describe('clearing the conversation', () => {
  const withHistory = () =>
    conversation({ transcript: [{ role: 'user', text: 'hi' }, { role: 'assistant', text: 'hello' }] });

  it('asks in the page, not with a native confirm, and does nothing on Keep', async () => {
    const user = userEvent.setup();
    const confirm = vi.spyOn(window, 'confirm');
    await mount({ open: true, conv: withHistory() });
    await user.click(await screen.findByRole('button', { name: 'Clear conversation' }));
    expect(screen.getByTestId('assistant-clear-confirm')).toHaveTextContent(en.assistant.clearConfirm);
    await user.click(screen.getByRole('button', { name: 'Keep' }));
    expect(api.clearConversation).not.toHaveBeenCalled();
    expect(confirm).not.toHaveBeenCalled();
  });

  it('Delete clears on the server, re-reads and reloads the preview', async () => {
    const user = userEvent.setup();
    await mount({ open: true, conv: withHistory() });
    await user.click(await screen.findByRole('button', { name: 'Clear conversation' }));
    api.getConversation.mockResolvedValue(conversation());
    await user.click(screen.getByRole('button', { name: 'Delete' }));
    await waitFor(() => expect(api.clearConversation).toHaveBeenCalledWith('e1'));
    await waitFor(() => expect(reload).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByTestId('assistant-empty')).toBeInTheDocument());
  });

  it('a clear drops the review card too: the draft goes without a new version', async () => {
    const user = userEvent.setup();
    api.getDraft.mockResolvedValue(draft());
    await mount({ open: true, conv: withHistory(), ready: ready({ draft_version: 4 }) });
    expect(await screen.findByTestId('assistant-review')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Clear conversation' }));
    api.getConversation.mockResolvedValue(conversation({ draft_version: 4 }));
    api.getDraft.mockRejectedValue({ status: 404 });
    await user.click(screen.getByRole('button', { name: 'Delete' }));
    await waitFor(() => expect(screen.queryByTestId('assistant-review')).toBeNull());
    await waitFor(() => expect(screen.getByLabelText('Describe what you want')).toHaveFocus());
  });
});

describe('page margin on wide screens', () => {
  it('moves the page over while open and gives the room back when minimized', async () => {
    const user = userEvent.setup();
    const listeners = new Set<() => void>();
    vi.stubGlobal('matchMedia', (q: string) => ({
      matches: true,
      media: q,
      addEventListener: (_: string, fn: () => void) => listeners.add(fn),
      removeEventListener: (_: string, fn: () => void) => listeners.delete(fn)
    }));
    await mount({ open: true });
    await waitFor(() => expect(document.body.style.paddingInlineEnd).toBe('416px'));
    await user.click(screen.getByRole('button', { name: 'Minimize assistant' }));
    await waitFor(() => expect(document.body.style.paddingInlineEnd).toBe(''));
    vi.unstubAllGlobals();
  });
});

describe('transcript from the server', () => {
  it('hydrates the saved conversation', async () => {
    await mount({
      open: true,
      conv: conversation({ transcript: [{ role: 'user', text: 'earlier question' }, { role: 'assistant', text: 'earlier answer' }] })
    });
    const log = screen.getByRole('log');
    expect(await within(log).findByText(/earlier answer/)).toBeInTheDocument();
    expect(screen.queryByTestId('assistant-empty')).toBeNull();
  });
});

describe('review inside the chat', () => {
  it('shows the draft with a Draft badge once the server has one, and refetches on draft_updated', async () => {
    api.getDraft.mockResolvedValue(draft());
    await mount({ open: true, ready: ready({ draft_version: 4 }), conv: conversation({ draft_version: 4 }) });
    const review = await screen.findByTestId('assistant-review');
    expect(within(review).getByText('Draft')).toBeInTheDocument();
    expect(within(review).getByText('Saturday workshop')).toBeInTheDocument();
    expect(api.getDraft).toHaveBeenCalledTimes(1);
    FakeSocket.last.receive({ type: 'draft_updated', run_id: 'r1', draft_version: 5 });
    await waitFor(() => expect(api.getDraft).toHaveBeenCalledTimes(2));
  });

  it('passes the page state through: a draft that no longer fits cannot be applied', async () => {
    api.getDraft.mockResolvedValue(draft());
    await mount({ open: true, ready: ready({ draft_version: 4 }), props: { previewDraftUnusable: true } });
    expect(await screen.findByTestId('assistant-review-unusable')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Apply draft' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Discard' })).toBeEnabled();
  });

  it('keeps the review out of the log, so the page alone announces a preview update', async () => {
    api.getDraft.mockResolvedValue(draft());
    await mount({ open: true, ready: ready({ draft_version: 4 }) });
    const review = await screen.findByTestId('assistant-review');
    expect(screen.getByRole('log')).not.toContainElement(review);
  });
});
