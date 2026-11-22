/** One feature request card: what it shows, Confirm / Edit / Discard, edit checks and the error path. */
import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import en from '$lib/i18n/locales/en.json';
import FeatureRequestCard from './FeatureRequestCard.svelte';
import type { FeatureRequestCard as Card } from './types';

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
  confirmFeatureRequest: vi.fn(),
  discardFeatureRequest: vi.fn()
}));
vi.mock('$lib/api/assistantService', () => ({ assistantApi: api }));

const F = en.assistant.featureRequest;

const card = (over: Partial<Card> = {}): Card => ({
  id: 'FR-3',
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

const apiError = (status: number, errors: object[] = []) => ({ status, message: '', details: { errors } });

type OnDone = (id: string, outcome: 'confirmed' | 'duplicate', duplicateOf: string | null) => void;
let ondone: Mock<OnDone>;
let onremoved: Mock<(id: string) => void>;
const mount = (c: Card = card()) => {
  ondone = vi.fn<OnDone>();
  onremoved = vi.fn<(id: string) => void>();
  return render(FeatureRequestCard, { eventId: 'e1', card: c, ondone, onremoved });
};

beforeEach(() => {
  vi.clearAllMocks();
  api.confirmFeatureRequest.mockResolvedValue({ id: 'FR-3', status: 'confirmed', duplicate_of: null });
  api.discardFeatureRequest.mockResolvedValue({});
});

describe('what the card shows', () => {
  it('shows the personal-data notice first, then the stored text as written', () => {
    mount();
    const card = screen.getByTestId('feature-request-card');
    const notice = screen.getByTestId('feature-request-notice');
    const fields = card.querySelector('.fields') as Element;
    expect(notice).toHaveTextContent(F.notice);
    expect(notice.compareDocumentPosition(fields) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(card).toHaveTextContent('Families want one price.');
    expect(card).toHaveTextContent('One price for a group.');
    expect(card).toHaveTextContent('Two tickets');
  });

  it('names the workaround and what it cost, in words', () => {
    mount();
    expect(screen.getByText('Built as: A code per family (cost: extra steps)')).toBeInTheDocument();
  });

  it('says it joins an existing request, with how often that was seen', () => {
    mount(card({ matches_existing: { id: 'FR-1', seen: 3 } }));
    expect(screen.getByTestId('feature-request-joins')).toHaveTextContent('Joins an existing request seen 3 times.');
  });

  it('uses the singular when the request was seen once', () => {
    mount(card({ matches_existing: { id: 'FR-1', seen: 1 } }));
    expect(screen.getByTestId('feature-request-joins')).toHaveTextContent('Joins an existing request seen once.');
  });

  it('cannot be edited while the full fields have not arrived', () => {
    mount(card({ tried: undefined }));
    expect(screen.getByTestId('feature-request-edit')).toBeDisabled();
    expect(screen.getByTestId('feature-request-confirm')).toBeEnabled();
  });
});

describe('confirm and discard', () => {
  // The store settles the card and hands it back; the card shows its receipt from that.
  it('Confirm stores the card as it is: no edits in the request', async () => {
    const user = userEvent.setup();
    const view = mount();
    await user.click(screen.getByTestId('feature-request-confirm'));
    await waitFor(() => expect(ondone).toHaveBeenCalledWith('FR-3', 'confirmed', null));
    expect(api.confirmFeatureRequest).toHaveBeenCalledWith('e1', 'FR-3', undefined);
    await view.rerender({
      eventId: 'e1',
      card: card({ outcome: 'confirmed', duplicate_of: null }),
      ondone,
      onremoved
    });
    expect(await screen.findByTestId('feature-request-settled')).toHaveTextContent('Saved as FR-3.');
    expect(screen.queryByTestId('feature-request-confirm')).toBeNull();
  });

  it('a join shows the joined variant with the request it joined', async () => {
    const user = userEvent.setup();
    api.confirmFeatureRequest.mockResolvedValue({ id: 'FR-3', status: 'duplicate', duplicate_of: 'FR-1' });
    const view = mount();
    await user.click(screen.getByTestId('feature-request-confirm'));
    await waitFor(() => expect(ondone).toHaveBeenCalledWith('FR-3', 'duplicate', 'FR-1'));
    await view.rerender({
      eventId: 'e1',
      card: card({ outcome: 'duplicate', duplicate_of: 'FR-1' }),
      ondone,
      onremoved
    });
    expect(screen.getByTestId('feature-request-settled')).toHaveTextContent('Joined request FR-1.');
  });

  it('Discard calls the server and removes the card', async () => {
    const user = userEvent.setup();
    mount();
    await user.click(screen.getByTestId('feature-request-discard'));
    await waitFor(() => expect(onremoved).toHaveBeenCalledWith('FR-3'));
    expect(api.discardFeatureRequest).toHaveBeenCalledWith('e1', 'FR-3');
    expect(ondone).not.toHaveBeenCalled();
  });

  it('a discard that finds the draft already gone removes the card too', async () => {
    const user = userEvent.setup();
    api.discardFeatureRequest.mockRejectedValue(apiError(404));
    mount();
    await user.click(screen.getByTestId('feature-request-discard'));
    await waitFor(() => expect(onremoved).toHaveBeenCalledWith('FR-3'));
  });

  it('a failed discard keeps the card and says so', async () => {
    const user = userEvent.setup();
    api.discardFeatureRequest.mockRejectedValue(apiError(500));
    mount();
    await user.click(screen.getByTestId('feature-request-discard'));
    expect(await screen.findByTestId('feature-request-failed')).toHaveTextContent(F.error.discard);
    expect(onremoved).not.toHaveBeenCalled();
  });

  it('a confirm for a draft that is gone removes the card, without an error', async () => {
    const user = userEvent.setup();
    api.confirmFeatureRequest.mockRejectedValue(apiError(400, [{ path: '', code: 'not_a_draft', message: 'x' }]));
    mount();
    await user.click(screen.getByTestId('feature-request-confirm'));
    await waitFor(() => expect(onremoved).toHaveBeenCalledWith('FR-3'));
    expect(screen.queryByTestId('feature-request-invalid')).toBeNull();
  });
});

describe('edit', () => {
  it('turns the fields into inputs with the stored values, and focuses the title', async () => {
    const user = userEvent.setup();
    mount();
    await user.click(screen.getByTestId('feature-request-edit'));
    expect(screen.getByLabelText('Title')).toHaveValue('Family price');
    expect(screen.getByLabelText('Problem')).toHaveValue('Families want one price.');
    expect(screen.getByLabelText('Tried 1')).toHaveValue('Two tickets');
    expect(screen.getByLabelText('Built as')).toHaveValue('A code per family');
    expect(screen.getByLabelText('Cost')).toHaveValue('extra_steps');
    expect(screen.getByLabelText('Title')).toHaveFocus();
  });

  it('Confirm sends the edited fields, trimmed, with the workaround and its cost', async () => {
    const user = userEvent.setup();
    mount();
    await user.click(screen.getByTestId('feature-request-edit'));
    const title = screen.getByLabelText('Title');
    await user.clear(title);
    await user.type(title, '  Family ticket  ');
    await user.selectOptions(screen.getByLabelText('Cost'), 'wrong_result');
    await user.click(screen.getByTestId('feature-request-confirm'));
    await waitFor(() => expect(ondone).toHaveBeenCalled());
    expect(api.confirmFeatureRequest).toHaveBeenCalledWith('e1', 'FR-3', {
      title: 'Family ticket',
      problem: 'Families want one price.',
      desired: 'One price for a group.',
      tried: ['Two tickets'],
      workaround: { used: 'A code per family', cost: 'wrong_result' }
    });
  });

  it('a blank title is refused in the form, and nothing is sent', async () => {
    const user = userEvent.setup();
    mount();
    await user.click(screen.getByTestId('feature-request-edit'));
    await user.clear(screen.getByLabelText('Title'));
    await user.click(screen.getByTestId('feature-request-confirm'));
    expect(await screen.findByText(F.error.required)).toBeInTheDocument();
    expect(screen.getByLabelText('Title')).toHaveAttribute('aria-invalid', 'true');
    expect(api.confirmFeatureRequest).not.toHaveBeenCalled();
  });

  it('the refused field is focused and described by its error, not only its counter', async () => {
    const user = userEvent.setup();
    mount();
    await user.click(screen.getByTestId('feature-request-edit'));
    await user.clear(screen.getByLabelText('Title'));
    await user.click(screen.getByTestId('feature-request-confirm'));
    const title = screen.getByLabelText('Title');
    await waitFor(() => expect(title).toHaveFocus());
    expect(title).toHaveAccessibleDescription(expect.stringContaining(F.error.required));
  });

  it('a problem over 600 characters is refused with the limit, and nothing is sent', async () => {
    const user = userEvent.setup();
    mount();
    await user.click(screen.getByTestId('feature-request-edit'));
    // Typing 601 characters key by key is slow; set the value and fire the input event.
    const problem = screen.getByLabelText('Problem') as HTMLTextAreaElement;
    problem.value = 'x'.repeat(601);
    problem.dispatchEvent(new Event('input', { bubbles: true }));
    await user.click(screen.getByTestId('feature-request-confirm'));
    expect(await screen.findByText('Use at most 600 characters.')).toBeInTheDocument();
    expect(api.confirmFeatureRequest).not.toHaveBeenCalled();
  });

  it('a tried item over 300 characters is named by its place in the list', async () => {
    const user = userEvent.setup();
    mount(card({ tried: ['Two tickets', 'ok'] }));
    await user.click(screen.getByTestId('feature-request-edit'));
    const second = screen.getByLabelText('Tried 2') as HTMLTextAreaElement;
    second.value = 'y'.repeat(301);
    second.dispatchEvent(new Event('input', { bubbles: true }));
    await user.click(screen.getByTestId('feature-request-confirm'));
    expect(await screen.findByText('Use at most 300 characters.')).toBeInTheDocument();
    expect(screen.getByLabelText('Tried 2')).toHaveAttribute('aria-invalid', 'true');
    expect(api.confirmFeatureRequest).not.toHaveBeenCalled();
  });

  it('Escape cancels the edit and keeps the card pending', async () => {
    const user = userEvent.setup();
    mount();
    await user.click(screen.getByTestId('feature-request-edit'));
    await user.type(screen.getByLabelText('Title'), '{Escape}');
    expect(screen.queryByLabelText('Title')).toBeNull();
    expect(screen.getByTestId('feature-request-confirm')).toBeInTheDocument();
    expect(api.confirmFeatureRequest).not.toHaveBeenCalled();
  });
});

describe('server errors', () => {
  it('a 400 lists the server messages by field, keeps the card and does not echo what was typed', async () => {
    const user = userEvent.setup();
    api.confirmFeatureRequest.mockRejectedValue(
      apiError(400, [
        { path: 'title', code: 'too_long', message: 'At most 100 characters.' },
        { path: 'workaround.used', code: 'personal_data', message: 'Looks like an email address.' }
      ])
    );
    mount();
    await user.click(screen.getByTestId('feature-request-edit'));
    const title = screen.getByLabelText('Title');
    await user.clear(title);
    await user.type(title, 'Kalle Secret Name');
    await user.click(screen.getByTestId('feature-request-confirm'));
    const box = await screen.findByTestId('feature-request-invalid');
    expect(box).toHaveTextContent(F.error.invalid);
    expect(box).toHaveTextContent('Title: At most 100 characters.');
    expect(box).toHaveTextContent('Built as: Looks like an email address.');
    expect(box).not.toHaveTextContent('Kalle Secret Name');
    expect(ondone).not.toHaveBeenCalled();
    expect(screen.getByTestId('feature-request-card')).toHaveAttribute('data-state', 'editing');
  });

  it('a 500 says the request could not be saved, and offers Confirm again', async () => {
    const user = userEvent.setup();
    api.confirmFeatureRequest.mockRejectedValue(apiError(500));
    mount();
    await user.click(screen.getByTestId('feature-request-confirm'));
    expect(await screen.findByTestId('feature-request-failed')).toHaveTextContent(F.error.save);
    expect(screen.getByTestId('feature-request-confirm')).toBeEnabled();
    expect(ondone).not.toHaveBeenCalled();
  });
});
