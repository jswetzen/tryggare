import { describe, it, expect, vi } from 'vitest';
import { render, screen, within } from '@testing-library/svelte';
import SessionSelector from './SessionSelector.svelte';

// Unmapped keys fall back to the key itself, so only the rule pills need real text.
vi.mock('svelte-i18n', () => {
  const translations: Record<string, string> = {
    'session.ruleOpen': 'Open - no ticket needed',
    'session.ruleChildren': 'Children need a ticket',
    'session.ruleAll': 'Everyone needs a ticket',
    'session.adultsNotCheckedIn': 'Adults are not checked in'
  };
  const translator = (key: string) => translations[key] ?? key;
  return {
    _: {
      subscribe: (cb: (v: (key: string) => string) => void) => {
        cb(translator);
        return () => {};
      }
    }
  };
});

const base = {
  event_name: 'Camp',
  start_time: '2026-07-11T09:00:00Z',
  end_time: '2026-07-11T12:00:00Z'
};

describe('SessionSelector rule pills', () => {
  const sessions = [
    { ...base, id: 's-open', name: 'Open play', effective_ticket_rule: 'open' as const },
    { ...base, id: 's-children', name: 'Kids club', effective_ticket_rule: 'children' as const },
    { ...base, id: 's-all', name: 'Family evening', effective_ticket_rule: 'all' as const },
    {
      ...base,
      id: 's-dropoff',
      name: 'Drop-off',
      effective_ticket_rule: 'children' as const,
      adults_not_checked_in: true
    },
    { ...base, id: 's-legacy', name: 'Older server' }
  ];

  function pills(id: string) {
    return screen.queryByTestId(`session-rules-${id}`);
  }

  it('shows one neutral pill per ticket rule', () => {
    render(SessionSelector, { props: { show: true, sessions, currentSession: null, onSelect: vi.fn(), onClose: vi.fn() } });

    expect(within(pills('s-open')!).getByText('Open - no ticket needed')).toBeInTheDocument();
    expect(within(pills('s-children')!).getByText('Children need a ticket')).toBeInTheDocument();
    expect(within(pills('s-all')!).getByText('Everyone needs a ticket')).toBeInTheDocument();
  });

  it('adds a second pill when adults are not checked in', () => {
    render(SessionSelector, { props: { show: true, sessions, currentSession: null, onSelect: vi.fn(), onClose: vi.fn() } });

    const dropoff = pills('s-dropoff')!;
    expect(within(dropoff).getByText('Children need a ticket')).toBeInTheDocument();
    expect(within(dropoff).getByText('Adults are not checked in')).toBeInTheDocument();
    expect(within(pills('s-children')!).queryByText('Adults are not checked in')).not.toBeInTheDocument();
  });

  it('shows no pills, and does not guess, when the server sends no rule', () => {
    render(SessionSelector, { props: { show: true, sessions, currentSession: null, onSelect: vi.fn(), onClose: vi.fn() } });
    expect(pills('s-legacy')).toBeNull();
  });
});
