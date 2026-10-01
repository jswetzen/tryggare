import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import CheckinPage from './+page.svelte';

// Unmapped keys fall back to the key itself; only the strings asserted on need real text.
vi.mock('svelte-i18n', () => {
  const translations: Record<string, string> = {
    'checkin.fullyCheckedInMatch': '{name} is already fully checked in',
    'checkin.noFamiliesFound': 'No families found matching "{query}"',
    'checkin.showCheckedInFamilies': 'Show checked-in families',
    'checkin.searchPlaceholder': 'Search'
  };
  const translator = (key: string, options?: { values?: Record<string, unknown> }) => {
    let out = translations[key] ?? key;
    for (const [k, v] of Object.entries(options?.values ?? {})) out = out.replace(`{${k}}`, String(v));
    return out;
  };
  const store = {
    subscribe: (cb: (v: typeof translator) => void) => {
      cb(translator);
      return () => {};
    }
  };
  return { _: store, t: store };
});

vi.mock('$lib/stores/websocket', () => ({
  websocketStore: {
    connect: vi.fn(),
    disconnect: vi.fn(),
    onMessage: vi.fn(() => () => {})
  }
}));

const getFamilies = vi.fn();
const getActiveSessions = vi.fn();

vi.mock('$lib/api/services', () => ({
  checkinApi: { getFamilies: () => getFamilies(), getActiveSessions: () => getActiveSessions() },
  checkInApi: {},
  ticketApi: {},
  printingApi: { getPrinters: vi.fn().mockResolvedValue([]) }
}));

const session = {
  id: 'session-a',
  event: 'event-1',
  name: 'Session A',
  event_name: 'Camp',
  start_time: '2026-07-11T09:00:00Z',
  end_time: '2026-07-11T12:00:00Z',
  is_active: true,
  requires_ticket: false,
  effective_ticket_rule: 'open',
  adults_not_checked_in: false
};

function apiFamily(n: string, last: string, checkedIn: boolean) {
  return {
    id: `family-${n}`,
    last_name: last,
    display_name: `${last} Family`,
    children: [
      {
        id: `child-${n}`,
        first_name: 'Kid',
        last_name: last,
        ticket_type: 'event',
        is_checked_in: checkedIn,
        family: `family-${n}`,
        qr_token: `qr-${n}`
      }
    ],
    parents: []
  };
}

describe('Check-in page - empty search state', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getActiveSessions.mockResolvedValue([session]);
    getFamilies.mockResolvedValue([apiFamily('1', 'Arrived', true), apiFamily('2', 'Waiting', false)]);
  });

  it('says a match is already fully checked in and offers the toggle, instead of "no families found"', async () => {
    const user = userEvent.setup();
    render(CheckinPage, { props: { data: { user: null } } });

    const search = await screen.findByTestId('family-search');
    await waitFor(() => expect(screen.getAllByText(/Waiting Family/).length).toBeGreaterThan(0));

    await user.type(search, 'Arrived');
    expect(await screen.findByText('Arrived Family is already fully checked in')).toBeInTheDocument();
    expect(screen.queryByText(/No families found/)).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Show checked-in families' }));
    await waitFor(() => expect(screen.getAllByText(/Arrived Family/).length).toBeGreaterThan(0));
    expect(screen.queryByText('Arrived Family is already fully checked in')).not.toBeInTheDocument();
  });

  it('keeps the plain "no families found" message when nothing matches at all', async () => {
    const user = userEvent.setup();
    render(CheckinPage, { props: { data: { user: null } } });

    const search = await screen.findByTestId('family-search');
    await waitFor(() => expect(screen.getAllByText(/Waiting Family/).length).toBeGreaterThan(0));

    await user.type(search, 'Nobody');
    expect(await screen.findByText('No families found matching "Nobody"')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Show checked-in families' })).not.toBeInTheDocument();
  });
});
