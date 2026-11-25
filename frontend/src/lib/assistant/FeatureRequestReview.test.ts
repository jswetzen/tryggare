/** The card list: its one live region announces new and settled cards, not the ones already there. */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import en from '$lib/i18n/locales/en.json';
import FeatureRequestReview from './FeatureRequestReview.svelte';
import type { FeatureRequestCard } from './types';

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

const api = vi.hoisted(() => ({ discardFeatureRequest: vi.fn() }));
vi.mock('$lib/api/assistantService', () => ({ assistantApi: api }));

const card = (id: string, over: Partial<FeatureRequestCard> = {}): FeatureRequestCard => ({
  id,
  title: `Request ${id}`,
  problem: 'p',
  desired: 'd',
  workaround: null,
  matches_existing: null,
  ...over
});

const status = () => screen.getByTestId('assistant-feature-status');

describe('FeatureRequestReview', () => {
  it('renders nothing but the status line when there are no cards', () => {
    render(FeatureRequestReview, { eventId: 'e1', cards: [], ondone: vi.fn(), onremoved: vi.fn() });
    expect(screen.queryByTestId('assistant-feature-requests')).toBeNull();
    expect(status()).toHaveTextContent('');
    expect(status()).toHaveAttribute('role', 'status');
  });

  it('does not announce the cards that were already there when it mounted', () => {
    render(FeatureRequestReview, {
      eventId: 'e1',
      cards: [card('FR-1')],
      ondone: vi.fn(),
      onremoved: vi.fn()
    });
    expect(screen.getAllByTestId('feature-request-card')).toHaveLength(1);
    expect(status()).toHaveTextContent('');
  });

  it('announces a new card, then a saved one', async () => {
    const view = render(FeatureRequestReview, {
      eventId: 'e1',
      cards: [card('FR-1')],
      ondone: vi.fn(),
      onremoved: vi.fn()
    });
    await view.rerender({ eventId: 'e1', cards: [card('FR-1'), card('FR-2')], ondone: vi.fn(), onremoved: vi.fn() });
    expect(status()).toHaveTextContent('Feature request FR-2 is ready to review.');
    await view.rerender({
      eventId: 'e1',
      cards: [card('FR-1'), card('FR-2', { outcome: 'confirmed', duplicate_of: null })],
      ondone: vi.fn(),
      onremoved: vi.fn()
    });
    expect(status()).toHaveTextContent('Feature request FR-2 saved.');
  });

  it('a second new card is announced with its own text, so the region speaks again', async () => {
    const view = render(FeatureRequestReview, { eventId: 'e1', cards: [], ondone: vi.fn(), onremoved: vi.fn() });
    await view.rerender({ eventId: 'e1', cards: [card('FR-1')], ondone: vi.fn(), onremoved: vi.fn() });
    const first = status().textContent;
    await view.rerender({ eventId: 'e1', cards: [card('FR-1'), card('FR-2')], ondone: vi.fn(), onremoved: vi.fn() });
    expect(status().textContent).not.toBe(first);
    expect(status()).toHaveTextContent('FR-2');
  });

  it('announces a join differently from a save', async () => {
    const view = render(FeatureRequestReview, {
      eventId: 'e1',
      cards: [card('FR-1')],
      ondone: vi.fn(),
      onremoved: vi.fn()
    });
    await view.rerender({
      eventId: 'e1',
      cards: [card('FR-1', { outcome: 'duplicate', duplicate_of: 'FR-9' })],
      ondone: vi.fn(),
      onremoved: vi.fn()
    });
    expect(status()).toHaveTextContent('Feature request FR-1 joined an existing one.');
  });

  it('announces a discard, as it does a confirm', async () => {
    api.discardFeatureRequest.mockResolvedValue({});
    const view = render(FeatureRequestReview, {
      eventId: 'e1',
      cards: [card('FR-1'), card('FR-2')],
      ondone: vi.fn(),
      onremoved: vi.fn()
    });
    await userEvent.setup().click(screen.getAllByTestId('feature-request-discard')[1]);
    await vi.waitFor(() => expect(status()).toHaveTextContent('Feature request FR-2 discarded.'));
  });
});
