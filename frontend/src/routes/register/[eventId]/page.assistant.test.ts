/**
 * Assistant mode of the register page (?preview=1&assistant=1): spec source,
 * quiet reload, banner chrome, guards. Plan: docs/event-assistant-plan.md,
 * "Register page touch points". Kept apart from page.test.ts (3.8k lines).
 */
import { describe, it, expect, vi, beforeAll, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import RegisterPage from './+page.svelte';
import specFixture from '$lib/registration/__fixtures__/form-spec.v1.json';

Element.prototype.scrollIntoView = vi.fn();

vi.mock('svelte-i18n', () => {
  const translations: Record<string, string> = {
    'register.heading': 'Register for {event}',
    'register.reloadConfig': 'Reload form config',
    'register.reloadFailed': 'Could not reload the form config.',
    'register.previewBanner': 'Preview mode',
    'register.previewSubmitDisabled': 'Submission is disabled in preview mode',
    'register.submitButton': 'Submit registration',
    'register.reloadClearedTitle': 'The form changed. These selections were cleared:',
    'assistant.preview.draft': 'Draft',
    'assistant.preview.saved': 'Saved',
    'assistant.preview.fallback': 'Assistant not available',
    'assistant.review.stale': 'The setup changed after this draft was made.'
  };
  const translator = (key: string) => translations[key] ?? key;
  const store = {
    subscribe: (cb: (v: typeof translator) => void) => {
      cb(translator);
      return () => {};
    }
  };
  return {
    t: store,
    _: store,
    locale: { subscribe: (cb: (v: string) => void) => (cb('en'), () => {}) }
  };
});

const pageState = vi.hoisted(() => {
  let current = {
    params: { eventId: 'event-1' },
    url: new URL('http://localhost/register/event-1'),
    state: {} as Record<string, unknown>
  };
  const subs = new Set<(v: typeof current) => void>();
  return {
    subscribe(fn: (v: typeof current) => void) {
      subs.add(fn);
      fn(current);
      return () => subs.delete(fn);
    },
    setUrl(href: string) {
      current = { ...current, url: new URL(href) };
      subs.forEach((fn) => fn(current));
    }
  };
});
vi.mock('$app/stores', () => ({ page: { subscribe: pageState.subscribe } }));
vi.mock('$app/navigation', () => ({
  goto: vi.fn(),
  pushState: vi.fn(),
  replaceState: vi.fn(),
  invalidate: vi.fn(),
  invalidateAll: vi.fn(),
  beforeNavigate: vi.fn(),
  afterNavigate: vi.fn()
}));

const fakeStore = vi.hoisted(() => {
  const listeners = new Set<(v: number) => void>();
  const unsubscribe = vi.fn();
  const connect = vi.fn();
  const disconnect = vi.fn();
  const created = vi.fn();
  const store = {
    subscribe: (cb: (v: unknown) => void) => (cb({}), () => {}),
    connect,
    disconnect,
    onDraftUpdated(fn: (v: number) => void) {
      listeners.add(fn);
      return () => {
        unsubscribe();
        listeners.delete(fn);
      };
    }
  };
  return { listeners, unsubscribe, connect, disconnect, created, store };
});
vi.mock('$lib/assistant/assistantStore', () => ({
  createAssistantStore: (opts: unknown) => {
    fakeStore.created(opts);
    return fakeStore.store;
  }
}));
vi.mock('$lib/assistant/AssistantHost.svelte', async () => ({
  default: (await import('$lib/assistant/testing/HostStub.svelte')).default
}));

const getEvent = vi.fn();
const submit = vi.fn();
const validatePromoCode = vi.fn();
vi.mock('$lib/api/registrationService', () => ({
  registrationApi: {
    getEvent: (...a: unknown[]) => getEvent(...a),
    submit: (...a: unknown[]) => submit(...a),
    validatePromoCode: (...a: unknown[]) => validatePromoCode(...a)
  }
}));

const getPreview = vi.fn();
const getConversation = vi.fn();
vi.mock('$lib/api/assistantService', () => ({
  assistantApi: {
    getPreview: (...a: unknown[]) => getPreview(...a),
    getConversation: (...a: unknown[]) => getConversation(...a)
  }
}));

const authGet = vi.fn();
vi.mock('$lib/api/client', async (importOriginal) => ({
  ...(await importOriginal<typeof import('$lib/api/client')>()),
  apiClient: { get: (...a: unknown[]) => authGet(...a) }
}));

function eventInfo(overrides: Record<string, unknown> = {}) {
  const tt = (id: string, name: string, price: string) => ({
    id,
    name,
    price,
    applies_to: 'child',
    min_birthdate: null,
    max_birthdate: null,
    kind: 'event',
    requires_ticket_type_id: null,
    max_per_required: null,
    available: true
  });
  return {
    id: 'event-1',
    name: 'Sommarläger',
    start_date: '2026-06-01',
    end_date: '2026-06-07',
    is_paid: true,
    price: null,
    currency: 'SEK',
    header_image_url: null,
    accent_color: null,
    ticket_types: [tt('tt-a', 'Barn', '100.00'), tt('tt-b', 'Ungdom', '150.00')],
    has_hidden_ticket_types: false,
    extras: [],
    spec_version: 1,
    sessions: [],
    fields: structuredClone(specFixture.fields),
    registration_window_status: 'open',
    registration_opens_at: null,
    registration_closes_at: null,
    ...overrides
  };
}

const previewOf = (formSpec: unknown, over: Record<string, unknown> = {}) => ({
  source: 'draft',
  stale: false,
  draft_unusable: false,
  form_spec: formSpec,
  diff: [],
  warnings: [],
  ...over
});
const apiError = (status: number) => ({ status, message: '', details: { errors: [] } });
const ASSISTANT = 'http://localhost/register/event-1?preview=1&assistant=1';
// Fires what the socket's draft_updated does, once the lazy chat has mounted.
async function emitDraftUpdated() {
  await waitFor(() => expect(fakeStore.listeners.size).toBe(1));
  fakeStore.listeners.forEach((fn) => fn(1));
}

// The chat chunk is loaded lazily; a cold first import must not eat a test's timeout.
beforeAll(async () => {
  await import('$lib/assistant/AssistantHost.svelte');
  await import('$lib/assistant/assistantStore');
});

beforeEach(() => {
  fakeStore.listeners.clear();
  vi.clearAllMocks();
  pageState.setUrl('http://localhost/register/event-1');
  authGet.mockResolvedValue({ authenticated: true });
});

describe('public render makes no assistant requests', () => {
  it.each([
    ['http://localhost/register/event-1'],
    ['http://localhost/register/event-1?preview=1']
  ])('%s', async (url) => {
    pageState.setUrl(url);
    getEvent.mockResolvedValue(eventInfo());
    render(RegisterPage);
    await screen.findByTestId('register-form');
    expect(authGet).not.toHaveBeenCalled();
    expect(getPreview).not.toHaveBeenCalled();
    expect(getEvent).toHaveBeenCalledTimes(1);
    expect(screen.queryByTestId('assistant-strip')).toBeNull();
  });
});

describe('assistant mode', () => {
  beforeEach(() => pageState.setUrl(ASSISTANT));

  it('reads the spec from the preview endpoint, not from getEvent', async () => {
    const draft = eventInfo();
    draft.ticket_types[0].name = 'Draft pass';
    getPreview.mockResolvedValue(previewOf(draft));
    render(RegisterPage);
    const strip = await screen.findByTestId('assistant-strip');
    expect(authGet).toHaveBeenCalledWith('/auth/check/');
    expect(getPreview).toHaveBeenCalledWith('event-1');
    expect(getEvent).not.toHaveBeenCalled();
    expect(strip.textContent).toContain('Draft');
    expect(document.body.textContent).toContain('Draft pass');
  });

  it('says Saved, and says why when the draft no longer fits', async () => {
    getPreview.mockResolvedValue(
      previewOf(eventInfo(), { source: 'saved', stale: true, draft_unusable: true })
    );
    render(RegisterPage);
    expect((await screen.findByTestId('assistant-strip')).textContent).toContain('Saved');
    expect(screen.getByTestId('assistant-stale').textContent).toContain(
      'assistant.preview.draftUnusable'
    );
  });

  it('flags a stale draft that still renders', async () => {
    getPreview.mockResolvedValue(previewOf(eventInfo(), { source: 'draft', stale: true }));
    render(RegisterPage);
    expect((await screen.findByTestId('assistant-stale')).textContent).toContain(
      'The setup changed after this draft was made.'
    );
  });

  it('replaces the reload button and notices with the slim strip', async () => {
    getPreview.mockResolvedValue(previewOf(eventInfo()));
    render(RegisterPage);
    await screen.findByTestId('assistant-strip');
    expect(screen.queryByRole('button', { name: 'Reload form config' })).toBeNull();
    expect(screen.queryByTestId('register-reload-notice')).toBeNull();
  });

  it.each(['open', 'not_open_yet', 'closed', 'not_configured'])(
    'renders the form for window status %s',
    async (status) => {
      getPreview.mockResolvedValue(previewOf(eventInfo({ registration_window_status: status })));
      render(RegisterPage);
      expect(await screen.findByTestId('register-form')).toBeInTheDocument();
    }
  );

  it('blocks submit: disabled button, and a forced submit sends nothing', async () => {
    getPreview.mockResolvedValue(previewOf(eventInfo()));
    render(RegisterPage);
    const form = await screen.findByTestId('register-form');
    expect(screen.getByRole('button', { name: 'Submit registration' })).toBeDisabled();
    await fireEvent.submit(form);
    expect(submit).not.toHaveBeenCalled();
  });
});

describe('falling back to the saved spec', () => {
  beforeEach(() => pageState.setUrl(ASSISTANT));

  it.each([401, 403, 409, 503])('on %i from the preview endpoint', async (status) => {
    getPreview.mockRejectedValue(apiError(status));
    const saved = eventInfo();
    saved.ticket_types[0].name = 'Saved pass';
    getEvent.mockResolvedValue(saved);
    render(RegisterPage);
    await screen.findByTestId('assistant-fallback');
    expect(document.body.textContent).toContain('Saved pass');
    expect(screen.queryByTestId('assistant-strip')).toBeNull();
    // Plain preview chrome is back, submit stays off.
    expect(screen.getByRole('button', { name: 'Reload form config' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Submit registration' })).toBeDisabled();
  });

  it('without a signed-in user, without asking the preview endpoint', async () => {
    authGet.mockResolvedValue({ authenticated: false });
    getEvent.mockResolvedValue(eventInfo());
    render(RegisterPage);
    await screen.findByTestId('assistant-fallback');
    expect(getPreview).not.toHaveBeenCalled();
  });

  it('when the auth check fails outright it is the same as not being signed in', async () => {
    authGet.mockRejectedValue(apiError(401));
    getEvent.mockResolvedValue(eventInfo());
    render(RegisterPage);
    await screen.findByTestId('assistant-fallback');
  });

  it('a network error on the preview still reports the event as unavailable', async () => {
    getPreview.mockRejectedValue({ status: 0, message: 'Network error' });
    render(RegisterPage);
    await waitFor(() => expect(screen.queryByTestId('register-form')).toBeNull());
    expect(getEvent).not.toHaveBeenCalled();
  });

  it('drops to the saved preview when permission disappears during a reload', async () => {
    const user = userEvent.setup();
    getPreview
      .mockResolvedValueOnce(previewOf(eventInfo()))
      .mockRejectedValueOnce(apiError(403));
    getEvent.mockResolvedValue(eventInfo());
    render(RegisterPage);
    await screen.findByTestId('assistant-strip');
    await emitDraftUpdated();
    await screen.findByTestId('assistant-fallback');
  });
});

describe('quiet reload (what draft_updated triggers)', () => {
  beforeEach(() => pageState.setUrl(ASSISTANT));

  it('swaps the spec, keeps typed data and selections of unchanged ids, shows no notice', async () => {
    const user = userEvent.setup();
    const after = eventInfo();
    after.ticket_types[0].price = '125.00';
    getPreview
      .mockResolvedValueOnce(previewOf(eventInfo()))
      .mockResolvedValueOnce(previewOf(after));
    render(RegisterPage);
    await screen.findByTestId('assistant-strip');
    await user.type(document.getElementById('parent-first-name-0') as HTMLInputElement, 'Sam');
    const select = screen.getByTestId('child-ticket-type-0') as HTMLSelectElement;
    await user.selectOptions(select, 'tt-b');
    // The live region is there before the update, so the change is announced.
    const status = screen.getByTestId('assistant-updated');
    expect(status.textContent?.trim()).toBe('');

    await emitDraftUpdated();

    await waitFor(() => expect(select.textContent).toContain('125.00'));
    expect((document.getElementById('parent-first-name-0') as HTMLInputElement).value).toBe('Sam');
    expect(select.value).toBe('tt-b');
    expect(screen.queryByTestId('register-reload-notice')).toBeNull();
    await waitFor(() =>
      expect(screen.getByTestId('assistant-updated').textContent?.trim()).toBe(
        'assistant.preview.updated'
      )
    );
    expect(screen.getByTestId('assistant-updated')).toBe(status);
  });

  it('still clears a selection that is gone, silently', async () => {
    const user = userEvent.setup();
    const after = eventInfo();
    after.ticket_types = after.ticket_types.filter((t) => t.id !== 'tt-b');
    getPreview
      .mockResolvedValueOnce(previewOf(eventInfo()))
      .mockResolvedValueOnce(previewOf(after));
    render(RegisterPage);
    await screen.findByTestId('assistant-strip');
    const select = screen.getByTestId('child-ticket-type-0') as HTMLSelectElement;
    await user.selectOptions(select, 'tt-b');

    await emitDraftUpdated();

    await waitFor(() =>
      expect(Array.from(select.options).some((o) => o.value === 'tt-b')).toBe(false)
    );
    expect(select.value).not.toBe('tt-b');
    expect(screen.queryByTestId('register-reload-notice')).toBeNull();
  });

  it('collapses updates that arrive mid-reload into exactly one more reload', async () => {
    let release!: () => void;
    const gate = new Promise<void>((r) => (release = r));
    getPreview.mockResolvedValueOnce(previewOf(eventInfo()));
    getPreview.mockImplementationOnce(async () => {
      await gate;
      return previewOf(eventInfo());
    });
    getPreview.mockResolvedValue(previewOf(eventInfo()));
    render(RegisterPage);
    await screen.findByTestId('assistant-strip');
    expect(getPreview).toHaveBeenCalledTimes(1);

    await emitDraftUpdated();
    await emitDraftUpdated();
    await emitDraftUpdated();
    await emitDraftUpdated();
    expect(getPreview).toHaveBeenCalledTimes(2);

    release();
    await waitFor(() => expect(getPreview).toHaveBeenCalledTimes(3));
    await new Promise((r) => setTimeout(r, 20));
    expect(getPreview).toHaveBeenCalledTimes(3);
  });

  it('shows a failed reload in the strip and leaves the form as it was', async () => {
    const user = userEvent.setup();
    getPreview
      .mockResolvedValueOnce(previewOf(eventInfo()))
      .mockRejectedValueOnce({ status: 0, message: 'Network error' });
    render(RegisterPage);
    await screen.findByTestId('assistant-strip');
    await user.type(document.getElementById('parent-first-name-0') as HTMLInputElement, 'Sam');
    await emitDraftUpdated();
    expect(await screen.findByTestId('register-reload-failed')).toBeInTheDocument();
    expect((document.getElementById('parent-first-name-0') as HTMLInputElement).value).toBe('Sam');
  });
});

describe('chat mounting', () => {
  beforeEach(() => {
    fakeStore.listeners.clear();
    pageState.setUrl(ASSISTANT);
  });

  it('is a lazy chunk mounted only in assistant mode, with the page state as props', async () => {
    getPreview.mockResolvedValue(previewOf(eventInfo(), { stale: true, draft_unusable: true, source: 'saved' }));
    render(RegisterPage);
    const host = await screen.findByTestId('host-stub');
    expect(host.dataset.event).toBe('event-1');
    expect(host.dataset.source).toBe('saved');
    expect(host.dataset.stale).toBe('true');
    expect(host.dataset.unusable).toBe('true');
    expect(fakeStore.connect).toHaveBeenCalledTimes(1);
    // The store re-reads the conversation through the HTTP service.
    getConversation.mockResolvedValue({});
    (fakeStore.created.mock.calls[0][0] as { fetchConversation: () => unknown }).fetchConversation();
    expect(getConversation).toHaveBeenCalledWith('event-1');
  });

  it.each([
    ['http://localhost/register/event-1'],
    ['http://localhost/register/event-1?preview=1']
  ])('is not created on the public render %s', async (url) => {
    pageState.setUrl(url);
    getEvent.mockResolvedValue(eventInfo());
    render(RegisterPage);
    await screen.findByTestId('register-form');
    await new Promise((r) => setTimeout(r, 20));
    expect(fakeStore.created).not.toHaveBeenCalled();
    expect(screen.queryByTestId('host-stub')).toBeNull();
  });

  it('is not created when the preview falls back to the saved spec', async () => {
    getPreview.mockRejectedValue(apiError(403));
    getEvent.mockResolvedValue(eventInfo());
    render(RegisterPage);
    await screen.findByTestId('register-form');
    await new Promise((r) => setTimeout(r, 20));
    expect(fakeStore.created).not.toHaveBeenCalled();
  });

  it('survives spec reloads without reconnecting, and unsubscribes and disconnects on destroy', async () => {
    getPreview.mockResolvedValue(previewOf(eventInfo()));
    const { unmount } = render(RegisterPage);
    await screen.findByTestId('host-stub');
    await emitDraftUpdated();
    await waitFor(() => expect(getPreview).toHaveBeenCalledTimes(2));
    expect(fakeStore.created).toHaveBeenCalledTimes(1);
    expect(fakeStore.disconnect).not.toHaveBeenCalled();

    unmount();
    expect(fakeStore.unsubscribe).toHaveBeenCalledTimes(1);
    expect(fakeStore.disconnect).toHaveBeenCalledTimes(1);
    expect(fakeStore.listeners.size).toBe(0);
  });

  it('the host reload prop runs a quiet reload', async () => {
    const user = userEvent.setup();
    getPreview.mockResolvedValue(previewOf(eventInfo()));
    render(RegisterPage);
    await screen.findByTestId('host-stub');
    await user.click(screen.getByRole('button', { name: 'stub reload' }));
    await waitFor(() => expect(getPreview).toHaveBeenCalledTimes(2));
    expect(screen.queryByTestId('register-reload-notice')).toBeNull();
  });
});
