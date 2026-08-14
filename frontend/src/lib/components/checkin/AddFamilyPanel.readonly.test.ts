/**
 * The Volontär's view of an existing family: read-only, with the allergy and
 * emergency-medical text behind an explicit reveal.
 *
 * Separate file from AddFamilyPanel.test.ts because that one mocks svelte-i18n
 * with its own small translation table and asserts on the create flow; the
 * mock has to be module-scoped, so sharing it would mean one table serving two
 * unrelated sets of assertions.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import AddFamilyPanel from './AddFamilyPanel.svelte';
import type { Family } from '$lib/checkin/types';

vi.mock('svelte-i18n', () => ({
  _: {
    subscribe: (fn: (t: (key: string, options?: unknown) => string) => void) => {
      fn((key: string) => {
        const translations: Record<string, string> = {
          'checkin.safetyInfoOnFile': 'Safety information on file',
          'checkin.safetyInfoReveal': 'Show safety information',
          'checkin.safetyInfoRevealLogged': 'This access has been logged.',
          'checkin.safetyInfoNone': 'No allergies or emergency medical information recorded.',
          'checkin.safetyInfoRevealError': "Couldn't load the safety information.",
          'checkin.familyDetailsTitle': 'Family Details',
          'checkin.familyDetailsReadOnly': 'Read-only.'
        };
        return translations[key] || key;
      });
      return () => {};
    }
  }
}));

/** What the API hands a Volontär: the flag, never the text. */
function maskedFamily(): Family {
  return {
    id: 'fam-1',
    last_name: 'Andersson',
    display_name: 'Andersson',
    name: 'Andersson',
    children: [
      {
        id: 'child-1',
        first_name: 'Alva',
        last_name: 'Andersson',
        name: 'Alva Andersson',
        ticket: 'event',
        ticket_type: 'event',
        checkedIn: false,
        family: 'fam-1',
        birthdate: '2018-01-01',
        allergies: null,
        notes: null,
        has_safety_info: true,
        health_consent_status: 'granted'
      },
      {
        id: 'child-2',
        first_name: 'Bo',
        last_name: 'Andersson',
        name: 'Bo Andersson',
        ticket: 'event',
        ticket_type: 'event',
        checkedIn: false,
        family: 'fam-1',
        birthdate: '2020-01-01',
        allergies: null,
        notes: null,
        has_safety_info: false,
        health_consent_status: 'not_applicable'
      }
    ],
    parents: []
  } as unknown as Family;
}

describe('AddFamilyPanel — read-behind-reveal for a volunteer', () => {
  const onAdd = vi.fn();
  const onSave = vi.fn();
  const onClose = vi.fn();

  beforeEach(() => vi.clearAllMocks());

  function renderPanel(onRevealSafetyInfo = vi.fn()) {
    render(AddFamilyPanel, {
      props: {
        family: maskedFamily(),
        canEditFamily: false,
        onRevealSafetyInfo,
        onAdd,
        onSave,
        onClose
      }
    });
    return onRevealSafetyInfo;
  }

  it('flags safety info without showing the text', () => {
    renderPanel();
    expect(screen.getByText('Safety information on file')).toBeInTheDocument();
    expect(screen.getByTestId('child-safety-info-reveal-0')).toBeInTheDocument();
    expect(screen.queryByText('Jordnötter')).not.toBeInTheDocument();
  });

  it('offers no way to save', () => {
    renderPanel();
    expect(screen.queryByTestId('add-family-submit-button')).not.toBeInTheDocument();
    expect(screen.getByTestId('add-family-name-input')).toBeDisabled();
  });

  it('shows the text after an explicit reveal, and says the access was logged', async () => {
    const user = userEvent.setup();
    const reveal = vi
      .fn()
      .mockResolvedValue({ allergies: 'Jordnötter', notes: 'Epilepsi' });
    renderPanel(reveal);

    await user.click(screen.getByTestId('child-safety-info-reveal-0'));

    await waitFor(() => {
      expect(screen.getByText('Jordnötter')).toBeInTheDocument();
    });
    expect(screen.getByText('Epilepsi')).toBeInTheDocument();
    expect(screen.getByText('This access has been logged.')).toBeInTheDocument();
    expect(reveal).toHaveBeenCalledWith('child-1');
    expect(reveal).toHaveBeenCalledTimes(1);
  });

  it('reveals one attendee at a time — a sibling stays unrevealed', async () => {
    const user = userEvent.setup();
    const reveal = vi.fn().mockResolvedValue({ allergies: 'Jordnötter', notes: '' });
    renderPanel(reveal);

    await user.click(screen.getByTestId('child-safety-info-reveal-0'));
    await waitFor(() => expect(screen.getByText('Jordnötter')).toBeInTheDocument());

    // The sibling has nothing on file, so there is no second control to press
    // and nothing was disclosed about them.
    expect(
      screen.getByText('No allergies or emergency medical information recorded.')
    ).toBeInTheDocument();
    expect(reveal).toHaveBeenCalledTimes(1);
  });

  it('surfaces a failed reveal instead of showing nothing', async () => {
    const user = userEvent.setup();
    const reveal = vi.fn().mockRejectedValue(new Error('network'));
    renderPanel(reveal);

    await user.click(screen.getByTestId('child-safety-info-reveal-0'));

    await waitFor(() => {
      expect(screen.getByText("Couldn't load the safety information.")).toBeInTheDocument();
    });
    expect(screen.getByTestId('child-safety-info-reveal-0')).toBeEnabled();
  });

  it('is still a normal edit form for a coordinator', () => {
    render(AddFamilyPanel, {
      props: { family: maskedFamily(), canEditFamily: true, onAdd, onSave, onClose }
    });
    expect(screen.getByTestId('add-family-submit-button')).toBeInTheDocument();
    expect(screen.queryByText('Safety information on file')).not.toBeInTheDocument();
  });
});
