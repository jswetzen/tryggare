/** Apply and discard, per docs/event-assistant-plan.md ("Apply flow"). */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import en from '$lib/i18n/locales/en.json';
import DraftReview from './DraftReview.svelte';
import type { DraftPayload } from './types';

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
  discardDraft: vi.fn()
}));
vi.mock('$lib/api/assistantService', () => ({ assistantApi: api }));

const draft = (over: Partial<DraftPayload> = {}): DraftPayload => ({
  spec: { event_spec_version: 1, marker: 'the-spec' },
  diff: [
    { kind: 'ticket_types', key: 'youth', change: 'added', new: { name: 'Youth pass', price: '450.00' } },
    { kind: 'extras', key: 'lunch', change: 'removed', old: { name: 'Lunch' } }
  ],
  warnings: [{ path: 'extras.lunch', code: 'w', message: 'Lunch has no price.' }],
  stale: false,
  token: 'tok-1',
  version: 4,
  ...over
});

let reload: ReturnType<typeof vi.fn<() => Promise<void>>>;
const mount = (props: Partial<{ draftUnusable: boolean; pageStale: boolean; version: number; running: boolean }> = {}) => {
  reload = vi.fn<() => Promise<void>>().mockResolvedValue(undefined);
  return render(DraftReview, { eventId: 'e1', version: 4, reload, ...props });
};
const apiError = (status: number, errors: object[] = []) => ({ status, message: '', details: { errors } });

beforeEach(() => {
  vi.clearAllMocks();
  api.getDraft.mockResolvedValue(draft());
  api.applySpec.mockResolvedValue({});
  api.discardDraft.mockResolvedValue({});
});

describe('DraftReview', () => {
  it('lists the changes and the warnings from the draft', async () => {
    mount();
    const review = await screen.findByTestId('assistant-review');
    expect(review).toHaveTextContent('Ticket type');
    expect(review).toHaveTextContent('Youth pass');
    expect(review).toHaveTextContent('added, 450 kr');
    expect(review).toHaveTextContent('Extra');
    expect(review).toHaveTextContent('removed');
    expect(review).toHaveTextContent('Lunch has no price.');
  });

  it('names changed fields through the field labels', async () => {
    api.getDraft.mockResolvedValue(
      draft({
        diff: [
          { kind: 'ticket_types', key: 'child', change: 'changed', new: { name: 'Child', price: '100.00' }, fields: { price: { old: '400', new: '100' } } }
        ]
      })
    );
    mount();
    const review = await screen.findByTestId('assistant-review');
    expect(review).toHaveTextContent('changed: price');
  });

  it('renders nothing when there is no draft', async () => {
    api.getDraft.mockRejectedValue(apiError(404));
    mount();
    await waitFor(() => expect(api.getDraft).toHaveBeenCalled());
    expect(screen.queryByTestId('assistant-review')).toBeNull();
  });

  it('Apply PUTs the draft spec, then discards by version and token, then reloads', async () => {
    const user = userEvent.setup();
    mount();
    await user.click(await screen.findByRole('button', { name: 'Apply draft' }));
    await waitFor(() => expect(reload).toHaveBeenCalled());
    expect(api.applySpec).toHaveBeenCalledWith('e1', { event_spec_version: 1, marker: 'the-spec' });
    expect(api.discardDraft).toHaveBeenCalledWith('e1', 4, 'tok-1');
    expect(api.applySpec.mock.invocationCallOrder[0]).toBeLessThan(api.discardDraft.mock.invocationCallOrder[0]);
    expect(await screen.findByTestId('assistant-applied')).toHaveTextContent(en.assistant.review.applied);
    expect(screen.queryByRole('button', { name: 'Apply draft' })).toBeNull();
  });

  it('shows the server errors as a list and keeps the draft when the PUT is refused', async () => {
    const user = userEvent.setup();
    api.applySpec.mockRejectedValue(
      apiError(409, [{ path: '', code: 'registration_open_on_target', message: 'Registration is open.' }])
    );
    mount();
    await user.click(await screen.findByRole('button', { name: 'Apply draft' }));
    const err = await screen.findByTestId('assistant-review-error');
    expect(err).toHaveTextContent(en.assistant.review.applyFailed);
    expect(err).toHaveTextContent('Registration is open.');
    expect(api.discardDraft).not.toHaveBeenCalled();
    expect(reload).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Apply draft' })).toBeEnabled();
  });

  it('draft_changed on the discard: the setup is saved, the newer draft is kept and shown', async () => {
    const user = userEvent.setup();
    api.discardDraft.mockRejectedValue(apiError(409, [{ path: '', code: 'draft_changed', message: 'x' }]));
    mount();
    await user.click(await screen.findByRole('button', { name: 'Apply draft' }));
    api.getDraft.mockResolvedValue(draft({ version: 5, token: 'tok-2' }));
    await waitFor(() => expect(screen.getByText(en.assistant.review.draftChanged)).toBeInTheDocument());
    expect(screen.queryByTestId('assistant-applied')).toBeNull();
    expect(screen.getByRole('button', { name: 'Apply draft' })).toBeInTheDocument();
    expect(reload).toHaveBeenCalled();
  });

  it('the setup is saved but the discard fails: says saved and shows what the server still holds', async () => {
    const user = userEvent.setup();
    api.discardDraft.mockRejectedValue(apiError(500));
    api.getDraft.mockResolvedValueOnce(draft()).mockResolvedValue(draft({ diff: [] }));
    mount();
    await user.click(await screen.findByRole('button', { name: 'Apply draft' }));
    expect(await screen.findByTestId('assistant-applied')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(en.assistant.review.none)).toBeInTheDocument());
    expect(screen.getByRole('button', { name: 'Discard' })).toBeInTheDocument();
  });

  it('a later successful load clears an earlier load failure', async () => {
    api.getDraft.mockRejectedValueOnce(apiError(500));
    const view = mount();
    expect(await screen.findByText(en.assistant.review.loadFailed)).toBeInTheDocument();
    await view.rerender({ eventId: 'e1', version: 5, reload });
    await waitFor(() => expect(screen.queryByText(en.assistant.review.loadFailed)).toBeNull());
    expect(screen.getByRole('button', { name: 'Apply draft' })).toBeInTheDocument();
  });

  it('Discard names the version and token it showed, then reloads', async () => {
    const user = userEvent.setup();
    mount();
    await user.click(await screen.findByRole('button', { name: 'Discard' }));
    await waitFor(() => expect(reload).toHaveBeenCalled());
    expect(api.discardDraft).toHaveBeenCalledWith('e1', 4, 'tok-1');
    expect(api.applySpec).not.toHaveBeenCalled();
    expect(screen.queryByTestId('assistant-review')).toBeNull();
  });

  it('a stale draft stays applicable, with a notice (last write wins)', async () => {
    api.getDraft.mockResolvedValue(draft({ stale: true }));
    mount();
    expect(await screen.findByTestId('assistant-review-stale')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Apply draft' })).toBeEnabled();
  });

  it('the page saying the draft is stale is enough', async () => {
    mount({ pageStale: true });
    expect(await screen.findByTestId('assistant-review-stale')).toBeInTheDocument();
  });

  it('a draft that does not fit cannot be applied, only discarded', async () => {
    mount({ draftUnusable: true });
    expect(await screen.findByTestId('assistant-review-unusable')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Apply draft' })).toBeDisabled();
  });

  it('collapses a long change list', async () => {
    api.getDraft.mockResolvedValue(
      draft({
        diff: Array.from({ length: 8 }, (_, i) => ({
          kind: 'sessions',
          key: `s${i}`,
          change: 'added' as const,
          new: { name: `Session ${i}` }
        }))
      })
    );
    mount();
    expect(await screen.findByText('and 3 more')).toBeInTheDocument();
  });

  it('drops the "saved" banner when a new run starts', async () => {
    const user = userEvent.setup();
    const view = mount();
    await user.click(await screen.findByRole('button', { name: 'Apply draft' }));
    await screen.findByTestId('assistant-applied');
    await view.rerender({ eventId: 'e1', version: 4, reload, running: true });
    await waitFor(() => expect(screen.queryByTestId('assistant-applied')).toBeNull());
  });
});
