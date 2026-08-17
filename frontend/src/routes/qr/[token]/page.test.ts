import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { readable } from 'svelte/store';
import QRPage from './+page.svelte';

// Mock svelte-i18n: unmapped keys fall back to the raw key string, so only
// keys actually asserted on below need a real translation.
vi.mock('svelte-i18n', () => {
  const translations: Record<string, string> = {
    'qr.pageTitle': 'Child Information',
    'qr.loading': 'Loading...',
    'qr.showSafetyInfo': 'Show safety info',
    'qr.safetyInfoRevealLogged': 'This access has been logged.',
    'qr.safetyInfoTitle': 'Safety Information',
    'qr.revealSafetyInfoError': "Couldn't load safety info. Please try again or ask a staff member for help.",
    'qr.allergyAlert': 'Allergy Alert',
    'qr.medicalConditions': 'Emergency Medical Information',
    'qr.contactStaff': 'For more information, please contact a staff member.',
    'qr.privacyNotice': 'This information is processed for child safeguarding during the event.',
    'qr.privacyLink': 'Privacy notice',
    'common.loading': 'Loading...'
  };
  const translator = (key: string) => translations[key] || key;
  return {
    t: {
      subscribe: (callback: (v: (key: string) => string) => void) => {
        callback(translator);
        return () => {};
      }
    }
  };
});

// $app/stores is aliased to a mock file defaulting params to {} — override
// it locally so `$page.params.token` resolves to a code these tests use.
vi.mock('$app/stores', () => ({
  page: readable({ params: { token: 'TESTCODE' } })
}));

const getInfo = vi.fn();
const revealSafetyInfo = vi.fn();

vi.mock('$lib/api/services', () => ({
  qrApi: {
    getInfo: (...args: unknown[]) => getInfo(...args),
    revealSafetyInfo: (...args: unknown[]) => revealSafetyInfo(...args)
  },
  checkInApi: { checkOut: vi.fn() },
  printingApi: { getPrinters: vi.fn().mockResolvedValue([]), createJob: vi.fn() },
  printQueueApi: { getPrintPageUrl: vi.fn() }
}));

function baseQrInfo(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    qr_code: 'TESTCODE',
    checkin_record_id: 'record-1',
    child: {
      id: 'child-1',
      first_name: 'Alice',
      last_name: 'Testsson',
      birthdate: '2018-01-01',
      allergies: null,
      notes: null,
      has_safety_info: true,
      is_parent: false,
      ...overrides
    },
    current_session: { id: 'session-1', name: 'Morning', check_in_time: '2026-07-11T09:00:00Z' },
    parents: [],
    family_id: 'family-1',
    supervised: false
  };
}

describe('QR page — safety info reveal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows a locked reveal button for an anonymous viewer, no text', async () => {
    getInfo.mockResolvedValue(baseQrInfo());

    render(QRPage, { props: { data: { user: null } } });

    await waitFor(() => {
      expect(screen.getByText('Show safety info')).toBeInTheDocument();
    });
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('reveals allergy and notes text after clicking the button', async () => {
    const user = userEvent.setup();
    getInfo.mockResolvedValue(baseQrInfo());
    revealSafetyInfo.mockResolvedValue({ allergies: 'Peanuts', notes: 'Epilepsy' });

    render(QRPage, { props: { data: { user: null } } });

    // The "logged" notice must not appear before the reveal (it would inform
    // the choice rather than confirm it — the rejected alternative).
    expect(screen.queryByText('This access has been logged.')).not.toBeInTheDocument();

    const button = await screen.findByText('Show safety info');
    await user.click(button);

    await waitFor(() => {
      expect(screen.getByText('Peanuts')).toBeInTheDocument();
    });
    expect(screen.getByText('Epilepsy')).toBeInTheDocument();
    expect(
      screen.queryByText('Show safety info')
    ).not.toBeInTheDocument();
    expect(revealSafetyInfo).toHaveBeenCalledWith('TESTCODE');
    // C1: the notice now appears after the reveal, matching the check-in screen.
    expect(screen.getByText('This access has been logged.')).toBeInTheDocument();
  });

  it('shows an error and re-enables the button when reveal fails', async () => {
    const user = userEvent.setup();
    getInfo.mockResolvedValue(baseQrInfo());
    revealSafetyInfo.mockRejectedValue(new Error('network error'));

    render(QRPage, { props: { data: { user: null } } });

    const button = await screen.findByText('Show safety info');
    await user.click(button);

    await waitFor(() => {
      expect(
        screen.getByText("Couldn't load safety info. Please try again or ask a staff member for help.")
      ).toBeInTheDocument();
    });

    const retryButton = screen.getByText('Show safety info');
    expect(retryButton.closest('button')).not.toBeDisabled();
  });

  it('shows nothing when there is no safety info to reveal', async () => {
    getInfo.mockResolvedValue(baseQrInfo({ has_safety_info: false }));

    render(QRPage, { props: { data: { user: null } } });

    await waitFor(() => {
      expect(screen.getByText('Alice')).toBeInTheDocument();
    });
    expect(
      screen.queryByText('Show safety info')
    ).not.toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('shows allergy/notes text immediately to an authenticated viewer, no button', async () => {
    getInfo.mockResolvedValue(
      baseQrInfo({ allergies: 'Peanuts', notes: 'Epilepsy', has_safety_info: true })
    );

    render(QRPage, {
      props: {
        data: {
          user: {
            id: '1',
            username: 'staff',
            name: 'Staff',
            is_staff: false,
            is_superuser: false,
            roles: ['Volontär'],
            permissions: ['families.view_family']
          }
        }
      }
    });

    await waitFor(() => {
      expect(screen.getByText('Peanuts')).toBeInTheDocument();
    });
    expect(screen.getByText('Epilepsy')).toBeInTheDocument();
    expect(
      screen.queryByText('Show safety info')
    ).not.toBeInTheDocument();
    expect(revealSafetyInfo).not.toHaveBeenCalled();
    // No audited reveal happened here (privileged GET, not qr_reveal_safety_info),
    // so the "logged" notice must not appear.
    expect(screen.queryByText('This access has been logged.')).not.toBeInTheDocument();
  });

  it('masks text and shows the reveal button for a logged-in viewer without edit access', async () => {
    // The backend masks allergies/notes to null unless the viewer holds
    // change_child/change_parent; a merely-authenticated viewer (e.g. a
    // Volontär with only view access) gets the same null the anonymous
    // path gets, so the frontend must gate on the payload, not on
    // `data.user` — that used to unmask on login alone with no reveal step.
    const user = userEvent.setup();
    getInfo.mockResolvedValue(baseQrInfo());
    revealSafetyInfo.mockResolvedValue({ allergies: 'Peanuts', notes: 'Epilepsy' });

    render(QRPage, {
      props: {
        data: {
          user: {
            id: '1',
            username: 'staff',
            name: 'Staff',
            is_staff: false,
            is_superuser: false,
            roles: ['Volontär'],
            permissions: ['families.view_family']
          }
        }
      }
    });

    const button = await screen.findByText('Show safety info');
    expect(screen.queryByText('Peanuts')).not.toBeInTheDocument();

    await user.click(button);

    await waitFor(() => {
      expect(screen.getByText('Peanuts')).toBeInTheDocument();
    });
    expect(screen.getByText('Epilepsy')).toBeInTheDocument();
    expect(revealSafetyInfo).toHaveBeenCalledWith('TESTCODE');
  });
});
