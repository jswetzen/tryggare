/**
 * Tests for AddFamilyPanel's parent health-consent capture (the staff
 * walk-up flow gaining the same ConsentCapture block children already had).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import AddFamilyPanel from './AddFamilyPanel.svelte';
import type { Family } from '$lib/checkin/types';

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
    await user.type(document.getElementById('parent-first-name-0') as HTMLInputElement, 'Nina');
    await user.type(document.getElementById('parent-last-name-0') as HTMLInputElement, 'Karlsson');
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
    await user.type(document.getElementById('parent-first-name-0') as HTMLInputElement, 'Nina');
    await user.type(document.getElementById('parent-last-name-0') as HTMLInputElement, 'Karlsson');
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
        first_name: 'Nina',
        last_name: 'Karlsson',
        health_consent_status: 'granted',
        allergies: 'Peanuts'
      })
    ]);
  });

  it('defaults an untouched parent to not_applicable with blank allergies/notes', async () => {
    const user = userEvent.setup();
    render(AddFamilyPanel, { props: { onAdd, onClose } });

    await user.type(screen.getByTestId('add-family-name-input'), 'Testsson');
    await user.type(document.getElementById('parent-first-name-0') as HTMLInputElement, 'Nina');
    await user.type(document.getElementById('parent-last-name-0') as HTMLInputElement, 'Karlsson');
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

describe('AddFamilyPanel — edit mode', () => {
  const onAdd = vi.fn();
  const onSave = vi.fn();
  const onClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  function makeFamily(overrides: Partial<Family> = {}): Family {
    return {
      id: 'family-1',
      last_name: 'Karlsson',
      display_name: 'Karlsson',
      name: 'Karlsson',
      children: [
        {
          id: 'child-1',
          first_name: 'Liam',
          last_name: 'Karlsson',
          name: 'Liam Karlsson',
          ticket: 'none',
          ticket_type: 'none',
          checkedIn: false,
          family: 'family-1',
          birthdate: '2018-05-01',
          allergies: 'Peanuts',
          notes: '',
          health_consent_status: 'granted'
        }
      ],
      parents: [
        {
          id: 'parent-1',
          first_name: 'Nina',
          last_name: 'Karlsson',
          name: 'Nina Karlsson',
          phone: '0701234567',
          email: 'nina@example.com',
          relationship_type: 'MOM',
          ticket: 'none',
          ticket_type: 'none',
          checkedIn: false,
          family: 'family-1',
          is_parent: true
        }
      ],
      ...overrides
    } as Family;
  }

  it('shows edit copy and pre-fills fields from the family prop', () => {
    render(AddFamilyPanel, { props: { family: makeFamily(), onAdd, onClose } });

    expect(screen.getByText('checkin.editFamilyTitle')).toBeInTheDocument();
    expect(screen.getByTestId('add-family-submit-button')).toHaveTextContent(
      'checkin.saveFamilyChanges'
    );
    expect(screen.getByTestId('add-family-name-input')).toHaveValue('Karlsson');
    expect(document.getElementById('child-first-name-0')).toHaveValue('Liam');
    expect(document.getElementById('child-last-name-0')).toHaveValue('Karlsson');
    expect(document.getElementById('child-birthdate-0')).toHaveValue('2018-05-01');
    expect(document.getElementById('parent-first-name-0')).toHaveValue('Nina');
    expect(document.getElementById('parent-last-name-0')).toHaveValue('Karlsson');
  });

  it('calls onSave (not onAdd) with familyId and existing member ids on submit', async () => {
    const user = userEvent.setup();
    render(AddFamilyPanel, { props: { family: makeFamily(), onAdd, onSave, onClose } });

    await user.click(screen.getByTestId('add-family-submit-button'));

    expect(onAdd).not.toHaveBeenCalled();
    expect(onSave).toHaveBeenCalledTimes(1);
    const payload = onSave.mock.calls[0][0];
    expect(payload.familyId).toBe('family-1');
    expect(payload.children).toEqual([
      expect.objectContaining({ id: 'child-1', first_name: 'Liam' })
    ]);
    expect(payload.parents).toEqual([
      expect.objectContaining({ id: 'parent-1', first_name: 'Nina', last_name: 'Karlsson' })
    ]);
  });

  it('a newly-added child during edit has no id in the outgoing payload', async () => {
    const user = userEvent.setup();
    render(AddFamilyPanel, { props: { family: makeFamily(), onAdd, onSave, onClose } });

    await user.click(screen.getByText(/checkin\.addAnotherChild/));
    await user.type(document.getElementById('child-first-name-1') as HTMLInputElement, 'Nyla');
    await user.type(document.getElementById('child-last-name-1') as HTMLInputElement, 'Karlsson');
    await user.type(document.getElementById('child-birthdate-1') as HTMLInputElement, '2022-02-02');

    await user.click(screen.getByTestId('add-family-submit-button'));

    const payload = onSave.mock.calls[0][0];
    expect(payload.children).toHaveLength(2);
    expect(payload.children[0].id).toBe('child-1');
    expect(payload.children[1].id).toBeUndefined();
    expect(payload.children[1].first_name).toBe('Nyla');
  });

  it('pre-fills consentNoticeShared for an already-granted consent so editing an unrelated field does not block submit', async () => {
    const user = userEvent.setup();
    render(AddFamilyPanel, { props: { family: makeFamily(), onAdd, onSave, onClose } });

    // The child's health consent was already 'granted' in the fixture —
    // submitting untouched must not raise the "notice not shared" error,
    // since the notice was already shared at the original consent capture.
    await user.click(screen.getByTestId('add-family-submit-button'));

    expect(onSave).toHaveBeenCalledTimes(1);
    const payload = onSave.mock.calls[0][0];
    expect(payload.children[0]).toEqual(
      expect.objectContaining({ health_consent_status: 'granted', allergies: 'Peanuts' })
    );
  });
});
