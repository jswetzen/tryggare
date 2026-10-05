import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import CheckoutPage from './+page.svelte';

// Mock svelte-i18n: unmapped keys fall back to the raw key string, which is
// enough because this test only asserts on child names and the header.
vi.mock('svelte-i18n', () => {
  const translator = (key: string) => key;
  const store = {
    subscribe: (callback: (v: (key: string) => string) => void) => {
      callback(translator);
      return () => {};
    }
  };
  return { t: store, _: store };
});

vi.mock('$lib/stores/websocket', () => ({
  websocketStore: {
    connect: vi.fn(),
    onMessage: vi.fn(() => () => {}),
    state: { subscribe: (cb: (v: unknown) => void) => { cb({ connected: true, connecting: false }); return () => {}; } }
  }
}));

const sessionActive = vi.fn();
const checkInActive = vi.fn();
const familyList = vi.fn();

vi.mock('$lib/api/services', () => ({
  sessionApi: { active: () => sessionActive() },
  checkInApi: { active: () => checkInActive(), checkOut: vi.fn() },
  familyApi: { list: () => familyList() }
}));

const sessionA = {
  id: 'session-a',
  name: 'Session A',
  event_name: 'Event One',
  start_time: '2026-07-11T09:00:00Z',
  end_time: '2026-07-11T12:00:00Z'
};
const sessionB = { ...sessionA, id: 'session-b', name: 'Session B', event_name: 'Event Two' };

function record(id: string, name: string, session: string) {
  return {
    id,
    child: `child-${id}`,
    child_name: name,
    session,
    session_name: session,
    check_in_time: '2026-07-11T09:30:00Z',
    supervised: false,
    check_in_staff: '',
    check_in_staff_name: ''
  };
}

function family(n: string, first: string, last: string) {
  return {
    id: `family-${n}`,
    display_name: `${last} family`,
    last_name: last,
    parents: [],
    children: [{ id: `child-${n}`, first_name: first, last_name: last, birthdate: '2018-01-01' }]
  };
}

describe('Checkout page - session filter', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    familyList.mockResolvedValue([
      family('1', 'Alice', 'Aliceson'),
      family('2', 'Bertil', 'Bertilsson')
    ]);
    checkInActive.mockResolvedValue([
      record('1', 'Alice InSessionA', 'session-a'),
      record('2', 'Bertil InSessionB', 'session-b')
    ]);
  });

  it('only lists check-ins of the session named in the header, even when the session loads slowly', async () => {
    // The session request resolves AFTER the check-in list would have. With
    // the concurrent start the list was filtered with activeSession === null
    // and showed every open check-in under a header naming session A.
    sessionActive.mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve([sessionA, sessionB]), 30))
    );

    render(CheckoutPage);

    await waitFor(() => expect(screen.getByTestId('session-indicator')).toHaveTextContent('Session A'));
    await waitFor(() => expect(screen.getAllByText(/Aliceson family/).length).toBeGreaterThan(0));
    expect(screen.queryByText(/Bertilsson family/)).not.toBeInTheDocument();
  });

  it('opens on the session this desk last picked, when it is still active', async () => {
    (localStorage.getItem as unknown as ReturnType<typeof vi.fn>).mockReturnValue('session-b');
    sessionActive.mockResolvedValue([sessionA, sessionB]);

    render(CheckoutPage);

    await waitFor(() => expect(screen.getByTestId('session-indicator')).toHaveTextContent('Session B'));
    await waitFor(() => expect(screen.getAllByText(/Bertilsson family/).length).toBeGreaterThan(0));
    expect(screen.queryByText(/Aliceson family/)).not.toBeInTheDocument();
  });

  it('falls back to the first session when storage cannot be read', async () => {
    (localStorage.getItem as unknown as ReturnType<typeof vi.fn>).mockImplementation(() => {
      throw new DOMException('denied', 'SecurityError');
    });
    sessionActive.mockResolvedValue([sessionA, sessionB]);

    render(CheckoutPage);

    await waitFor(() => expect(screen.getByTestId('session-indicator')).toHaveTextContent('Session A'));
    await waitFor(() => expect(screen.getAllByText(/Aliceson family/).length).toBeGreaterThan(0));
  });
});
