/**
 * Tests for AddFamilyPanel's parent health-consent capture (the staff
 * walk-up flow gaining the same ConsentCapture block children already had).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import AddFamilyPanel from './AddFamilyPanel.svelte';

// Mock svelte-i18n: unmapped keys fall back to the raw key string, so only
// keys actually asserted on below need a real translation.
vi.mock('svelte-i18n', () => ({
  _: {
    subscribe: (fn: (t: (key: string, options?: unknown) => string) => void) => {
      fn((key: string) => {
        const translations: Record<string, string> = {
          'checkin.adultHealthConsentRequired': 'Please confirm the consent notice was shared with them',
          'checkin.adultHealthInfoConsent': 'Yes — they consent to recording details',
          'checkin.adultHealthInfoDecline': 'Yes — they decline to have details recorded',
        };
        return translations[key] || key;
      });
      return () => {};
    }
  }
}));

describe('AddFamilyPanel — parent health consent', () => {
  const onAdd = vi.fn();
  const onClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // The default single child row has HTML `required` fields — jsdom's
  // native constraint validation blocks the form's submit event entirely
  // (handleSubmit never runs) if they're left empty, regardless of what
  // we're actually testing. Fill them in every test that submits.
  async function fillRequiredChildRow(user: ReturnType<typeof userEvent.setup>) {
    await user.type(document.getElementById('child-first-name-0') as HTMLInputElement, 'Alice');
    await user.type(document.getElementById('child-last-name-0') as HTMLInputElement, 'Testsson');
    await user.type(document.getElementById('child-birthdate-0') as HTMLInputElement, '2018-01-01');
  }

  it('renders a consent question per parent row', () => {
    render(AddFamilyPanel, { props: { onAdd, onClose } });

    // The attest checkbox only renders once "consented" is selected — the
    // radio question itself is what's always present for a parent row.
    expect(screen.getByText('Yes — they consent to recording details')).toBeInTheDocument();
  });

  it('blocks submit when a parent consents but the notice attestation is unchecked', async () => {
    const user = userEvent.setup();
    render(AddFamilyPanel, { props: { onAdd, onClose } });

    await user.type(screen.getByTestId('add-family-name-input'), 'Testsson');
    await user.type(document.getElementById('parent-name-0') as HTMLInputElement, 'Nina Karlsson');
    await fillRequiredChildRow(user);

    // Select "consented" for the parent's own health info without ticking
    // the attestation checkbox.
    await user.click(screen.getByText('Yes — they consent to recording details'));

    await user.click(screen.getByTestId('add-family-submit-button'));

    expect(
      screen.getByText('Please confirm the consent notice was shared with them')
    ).toBeInTheDocument();
    expect(onAdd).not.toHaveBeenCalled();
  });

  it('submits granted health_consent_status with allergies/notes once attested', async () => {
    const user = userEvent.setup();
    render(AddFamilyPanel, { props: { onAdd, onClose } });

    await user.type(screen.getByTestId('add-family-name-input'), 'Testsson');
    await user.type(document.getElementById('parent-name-0') as HTMLInputElement, 'Nina Karlsson');
    await fillRequiredChildRow(user);

    await user.click(screen.getByText('Yes — they consent to recording details'));
    await user.click(screen.getByTestId('parent-consent-attest-parent-0'));

    const allergiesInput = document.getElementById('parent-allergies-parent-0') as HTMLInputElement;
    await user.type(allergiesInput, 'Peanuts');

    await user.click(screen.getByTestId('add-family-submit-button'));

    expect(onAdd).toHaveBeenCalledTimes(1);
    const payload = onAdd.mock.calls[0][0];
    expect(payload.parents).toEqual([
      expect.objectContaining({
        name: 'Nina Karlsson',
        health_consent_status: 'granted',
        allergies: 'Peanuts'
      })
    ]);
  });

  it('defaults an untouched parent to not_applicable with blank allergies/notes', async () => {
    const user = userEvent.setup();
    render(AddFamilyPanel, { props: { onAdd, onClose } });

    await user.type(screen.getByTestId('add-family-name-input'), 'Testsson');
    await user.type(document.getElementById('parent-name-0') as HTMLInputElement, 'Nina Karlsson');
    await fillRequiredChildRow(user);

    await user.click(screen.getByTestId('add-family-submit-button'));

    expect(onAdd).toHaveBeenCalledTimes(1);
    const payload = onAdd.mock.calls[0][0];
    expect(payload.parents).toEqual([
      expect.objectContaining({
        health_consent_status: 'not_applicable',
        allergies: '',
        notes: ''
      })
    ]);
  });

  it('skips consent validation for an empty (unused) parent row', async () => {
    const user = userEvent.setup();
    render(AddFamilyPanel, { props: { onAdd, onClose } });

    // Only the family name and child are filled; the default single
    // parent row stays empty and should be silently dropped, same as
    // before this change.
    await user.type(screen.getByTestId('add-family-name-input'), 'Testsson');
    await fillRequiredChildRow(user);

    await user.click(screen.getByTestId('add-family-submit-button'));

    expect(onAdd).toHaveBeenCalledTimes(1);
    const payload = onAdd.mock.calls[0][0];
    expect(payload.parents).toEqual([]);
  });
});
