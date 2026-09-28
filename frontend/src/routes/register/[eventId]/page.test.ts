import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { readable } from 'svelte/store';
import RegisterPage from './+page.svelte';

// jsdom (this project's vitest environment — see vitest.config.ts) doesn't
// implement scrollIntoView. The error-banner $effect in +page.svelte calls
// it whenever `error` becomes non-empty (so a failed submit is visible on
// this 2000+px page — see that effect's own comment), which the
// idempotency-key "retry after a failed submit" test below is the first in
// this file to actually trigger. Stubbed once, at module scope, rather than
// per-test, since nothing here asserts on scroll behavior itself.
Element.prototype.scrollIntoView = vi.fn();

// Mock svelte-i18n: unmapped keys fall back to a rendering of the key +
// values so assertions can still target substrings without maintaining a
// full translation table here.
vi.mock('svelte-i18n', () => {
  const translations: Record<string, string> = {
    'register.ticketTypeLabel': 'Ticket type',
    'register.ticketTypePlaceholder': 'Select a ticket type',
    'register.ticketAgeRangeBoth': '{min}–{max} yrs',
    'register.ticketAgeRangeMin': '{min}+ yrs',
    'register.ticketAgeRangeMax': 'up to {max} yrs',
    'register.ticketTypeIneligibleWarning':
      "{name} isn't eligible for the birthdate you entered ({range}). Please choose a different ticket type.",
    'register.ticketTypeIneligibleWarningNoRange':
      "{name} isn't eligible for the birthdate you entered. Please choose a different ticket type.",
    'register.birthdateInvalid': "That date isn't valid — check the day, month, and year.",
    'register.totalProvisional': '(provisional — includes a ticket that needs to change)',
    'register.totalLabel': 'Total so far',
    'register.ticketRequiresOther': '{name} requires at least one {required} ticket in this booking.',
    'register.ticketCapExceeded': 'Only {max} {name} ticket(s) allowed per {required} ticket.',
    'register.ticketCompositionOptionRequires': 'requires {required}',
    'register.ticketCompositionOptionCapReached': 'max {max} per {required}',
    'register.ticketSoldOutMarker': 'sold out',
    'register.ticketSoldOutWarning':
      '{name} sold out while you were filling in this form. Please choose a different ticket type.',
    'checkin.childFirstName': 'First name',
    'checkin.childLastName': 'Last name',
    'checkin.childBirthdate': 'Birthdate',
    'checkin.children': 'Children',
    'checkin.childNumber': 'Child {number}',
    'checkin.addAnotherChild': 'Add another child',
    'checkin.parentInfo': 'Parent info',
    'checkin.addParent': 'Add parent',
    'checkin.removeParent': 'Remove parent',
    'checkin.removeChild': 'Remove child',
    'checkin.familyName': 'Family name',
    'register.contactEmail': 'Contact email',
    'register.introText': '',
    'register.heading': 'Register for {event}',
    'register.privacyNotice': '',
    'register.privacyLink': 'Privacy notice',
    'register.submitButton': 'Submit registration',
    'register.idempotencyConflictTitle': 'Already submitted?',
    'register.idempotencyConflictMessage':
      'Your registration may have already gone through. Check {email} for a confirmation before submitting again.',
    'register.idempotencyConflictButton': 'Send the confirmation again',
    'register.promoCodeLabel': 'Promo code',
    'register.promoCodeInvalid': "This code isn't valid. Check the spelling, or contact the organiser.",
    'register.promoCodeNotApplied': 'Apply this code, or clear the field, before submitting.',
    'register.promoCodeRemoveButton': 'Remove',
    'register.promoCodeAppliedPrefix': 'Code applied',
    'register.promoEffectPercent': '{percent}% discount on the total.',
    'register.promoEffectFixed': '{amount} kr discount on the total.',
    'register.promoEffectUnlocks': '{names} — now available under Ticket type.',
    'register.promoRemoved': 'The code was removed.',
    'register.promoRemovedWithReset':
      'The code was removed. {ticket} is no longer selectable – choose a new ticket type for {attendees}.',
    'register.promoResetCaption': 'The code that unlocked this was removed — choose a new ticket type.',
    'register.parentLabel': 'Parent {number}'
  };
  const translator = (key: string, opts?: { values?: Record<string, unknown> }) => {
    let text = translations[key] ?? key;
    if (opts?.values) {
      for (const [k, v] of Object.entries(opts.values)) {
        text = text.replace(`{${k}}`, String(v));
      }
    }
    return text;
  };
  const store = {
    subscribe: (callback: (v: typeof translator) => void) => {
      callback(translator);
      return () => {};
    }
  };
  return {
    t: store,
    _: store,
    locale: {
      subscribe: (callback: (v: string) => void) => {
        callback('en');
        return () => {};
      }
    }
  };
});

vi.mock('$app/stores', () => ({
  page: readable({ params: { eventId: 'event-1' }, url: new URL('http://localhost/register/event-1') })
}));

const getEvent = vi.fn();
// Exposed like getEvent above (not an inline vi.fn() in the factory) so the
// idempotency-key tests below can inspect what handleSubmit actually sent —
// see the "Register page — idempotency key" describe block.
const submit = vi.fn();
// Same reasoning, exposed for the promo-code tests below.
const validatePromoCode = vi.fn();

vi.mock('$lib/api/registrationService', () => ({
  registrationApi: {
    getEvent: (...args: unknown[]) => getEvent(...args),
    submit: (...args: unknown[]) => submit(...args),
    validatePromoCode: (...args: unknown[]) => validatePromoCode(...args)
  }
}));

function baseEventInfo(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: 'event-1',
    name: 'Sommarläger 2026',
    start_date: '2026-06-01',
    end_date: '2026-06-07',
    is_paid: true,
    price: null,
    currency: 'SEK',
    header_image_url: null,
    accent_color: null,
    ticket_types: [
      {
        id: 'tt-child',
        name: 'Barn (0-12 år)',
        price: '100.00',
        applies_to: 'child',
        min_birthdate: '2014-06-01',
        max_birthdate: '2026-06-01',
        kind: 'event',
        requires_ticket_type_id: null,
        max_per_required: null,
        available: true
      },
      {
        id: 'tt-youth',
        name: 'Ungdom (13-17 år)',
        price: '150.00',
        applies_to: 'child',
        min_birthdate: '2009-06-02',
        max_birthdate: '2013-06-01',
        kind: 'event',
        requires_ticket_type_id: null,
        max_per_required: null,
        available: true
      }
    ],
    has_hidden_ticket_types: false,
    extras: [],
    registration_window_status: 'open',
    registration_opens_at: null,
    registration_closes_at: null,
    ...overrides
  };
}

describe('Register page — ticket type eligibility by birthdate', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('disables no options before a birthdate is entered', async () => {
    getEvent.mockResolvedValue(baseEventInfo());
    render(RegisterPage);

    const select = (await screen.findByTestId('child-ticket-type-0')) as HTMLSelectElement;
    const options = Array.from(select.options).filter((o) => o.value !== '');
    expect(options).toHaveLength(2);
    expect(options.every((o) => !o.disabled)).toBe(true);
  });

  it('disables an out-of-window option, keeps it in the list, and shows why', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(baseEventInfo());
    render(RegisterPage);

    const select = (await screen.findByTestId('child-ticket-type-0')) as HTMLSelectElement;
    const dateInput = document.getElementById('child-birthdate-0') as HTMLInputElement;
    await user.type(dateInput, '2015-05-01');
    await user.tab();

    const options = Array.from(select.options).filter((o) => o.value !== '');
    // Still both options present — disabled, not removed.
    expect(options).toHaveLength(2);
    const childOption = options.find((o) => o.value === 'tt-child')!;
    const youthOption = options.find((o) => o.value === 'tt-youth')!;
    expect(childOption.disabled).toBe(false);
    expect(youthOption.disabled).toBe(true);
    // Bare age-range marker, not a full sentence — the sentence lives in
    // the field-level warning instead (see next describe block).
    expect(youthOption.textContent).toContain('yrs');
    expect(youthOption.textContent).not.toContain('Not eligible');
  });

  it('flags an already-selected ticket that a later birthdate edit makes ineligible, without clearing it', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(baseEventInfo());
    render(RegisterPage);

    const select = (await screen.findByTestId('child-ticket-type-0')) as HTMLSelectElement;
    const dateInput = document.getElementById('child-birthdate-0') as HTMLInputElement;
    // Old enough for the "Ungdom" ticket at event start.
    await user.type(dateInput, '2011-05-01');
    await user.tab();

    await user.selectOptions(select, 'tt-youth');
    expect(select.value).toBe('tt-youth');

    // Now edit the birthdate to make the current selection ineligible.
    await user.clear(dateInput);
    await user.type(dateInput, '2020-05-01');
    await user.tab();

    // Selection is preserved, not silently cleared.
    expect(select.value).toBe('tt-youth');
    const warning = await screen.findByTestId('child-ticket-ineligible-0');
    expect(warning.textContent).toContain("isn't eligible for the birthdate you entered");

    // And the list of options is unchanged — still both, still present.
    const options = Array.from(select.options).filter((o) => o.value !== '');
    expect(options).toHaveLength(2);
  });

  it('marks the flagged select itself (border/aria), not just a caption below it', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(baseEventInfo());
    render(RegisterPage);

    const select = (await screen.findByTestId('child-ticket-type-0')) as HTMLSelectElement;
    const dateInput = document.getElementById('child-birthdate-0') as HTMLInputElement;
    await user.type(dateInput, '2011-05-01');
    await user.tab();
    await user.selectOptions(select, 'tt-youth');
    await user.clear(dateInput);
    await user.type(dateInput, '2020-05-01');
    await user.tab();

    await screen.findByTestId('child-ticket-ineligible-0');
    expect(select.getAttribute('aria-invalid')).toBe('true');
    expect(select.getAttribute('aria-describedby')).toBe('child-ticket-ineligible-0');

    // The selected option's own (truncatable, collapsed-control) text drops
    // the age-range marker — the reason lives in the warning paragraph,
    // which the select now points to via aria-describedby.
    const selectedOption = Array.from(select.options).find((o) => o.value === 'tt-youth')!;
    expect(selectedOption.textContent).not.toContain('yrs');
  });

  it('suppresses both the age caption and the ticket warning while the birthdate is invalid', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(baseEventInfo());
    render(RegisterPage);

    const select = (await screen.findByTestId('child-ticket-type-0')) as HTMLSelectElement;
    const dateInput = document.getElementById('child-birthdate-0') as HTMLInputElement;

    // A valid, eligible selection first.
    await user.type(dateInput, '2020-05-01');
    await user.tab();
    await user.selectOptions(select, 'tt-child');
    await screen.findByTestId('child-birthdate-prose-0');

    // Now corrupt the birthdate into a future date — invalid per the
    // input's own max, not a real ticket problem.
    await user.clear(dateInput);
    await user.type(dateInput, '2027-01-01');
    await user.tab();

    expect(screen.queryByTestId('child-birthdate-prose-0')).toBeNull();
    expect(screen.queryByTestId('child-ticket-ineligible-0')).toBeNull();
    const invalidNotice = await screen.findByTestId('child-birthdate-invalid-0');
    expect(invalidNotice.textContent).toContain("isn't valid");
    expect(select.getAttribute('aria-invalid')).toBe('false');
  });

  it('marks the running total provisional while a row has an ineligible selection, and clears when fixed', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(baseEventInfo());
    render(RegisterPage);

    const select = (await screen.findByTestId('child-ticket-type-0')) as HTMLSelectElement;
    const dateInput = document.getElementById('child-birthdate-0') as HTMLInputElement;
    await user.type(dateInput, '2011-05-01');
    await user.tab();
    await user.selectOptions(select, 'tt-youth');

    expect(screen.queryByTestId('register-total-provisional')).toBeNull();

    await user.clear(dateInput);
    await user.type(dateInput, '2020-05-01');
    await user.tab();

    // The arithmetic still prices the flagged ticket (not silently
    // dropped) — only a qualifier is added.
    const total = await screen.findByTestId('register-running-total');
    expect(total.textContent).toContain('150.00');
    await screen.findByTestId('register-total-provisional');

    // Switching to the now-eligible ticket clears the qualifier.
    await user.selectOptions(select, 'tt-child');
    expect(screen.queryByTestId('register-total-provisional')).toBeNull();
  });
});

// requires_ticket_type_id / max_per_required — mirrors the seeded demo pair
// (Familjebiljett / Familjebiljett - familjemedlem, max_per_required=4);
// max_per_required=1 here just to make the cap test compact.
function familyEventInfo(overrides: Partial<Record<string, unknown>> = {}) {
  return baseEventInfo({
    ticket_types: [
      {
        id: 'tt-family',
        name: 'Familjebiljett',
        price: '2000.00',
        applies_to: 'either',
        min_birthdate: null,
        max_birthdate: null,
        kind: 'event',
        requires_ticket_type_id: null,
        max_per_required: null,
        available: true
      },
      {
        id: 'tt-member',
        name: 'Familjebiljett - familjemedlem',
        price: '0.00',
        applies_to: 'either',
        min_birthdate: null,
        max_birthdate: null,
        kind: 'event',
        requires_ticket_type_id: 'tt-family',
        max_per_required: 1,
        available: true
      },
      {
        id: 'tt-solo',
        name: 'Solo',
        price: '300.00',
        applies_to: 'either',
        min_birthdate: null,
        max_birthdate: null,
        kind: 'event',
        requires_ticket_type_id: null,
        max_per_required: null,
        available: true
      }
    ],
    ...overrides
  });
}

describe('Register page — ticket composition (family ticket) rules', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('disables the dependent option when no required ticket is present in the booking', async () => {
    getEvent.mockResolvedValue(familyEventInfo());
    render(RegisterPage);

    const select = (await screen.findByTestId('child-ticket-type-0')) as HTMLSelectElement;
    const options = Array.from(select.options).filter((o) => o.value !== '');
    const familyOption = options.find((o) => o.value === 'tt-family')!;
    const memberOption = options.find((o) => o.value === 'tt-member')!;
    // Disabled, not removed — same convention as the age-window case.
    expect(options).toHaveLength(3);
    expect(familyOption.disabled).toBe(false);
    expect(memberOption.disabled).toBe(true);
    expect(memberOption.textContent).toContain('requires Familjebiljett');
  });

  it('disables the dependent option for a new picker once the cap is reached', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(familyEventInfo());
    render(RegisterPage);

    const parentSelect = (await screen.findByTestId('parent-ticket-type-0')) as HTMLSelectElement;
    await user.selectOptions(parentSelect, 'tt-family');

    const childSelect0 = (await screen.findByTestId('child-ticket-type-0')) as HTMLSelectElement;
    await user.selectOptions(childSelect0, 'tt-member');
    expect(childSelect0.value).toBe('tt-member');

    await user.click(screen.getByText(/Add another child/));
    const childSelect1 = (await screen.findByTestId('child-ticket-type-1')) as HTMLSelectElement;
    const options1 = Array.from(childSelect1.options).filter((o) => o.value !== '');
    const memberOption1 = options1.find((o) => o.value === 'tt-member')!;
    expect(memberOption1.disabled).toBe(true);
    expect(memberOption1.textContent).toContain('max 1 per Familjebiljett');

    // The first child's own pick stays put — it's already inside the cap,
    // not blocked by it.
    expect(childSelect0.value).toBe('tt-member');
  });

  it('keeps a family-member selection (flagged, not cleared) when the family ticket is changed away', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(familyEventInfo());
    render(RegisterPage);

    const parentSelect = (await screen.findByTestId('parent-ticket-type-0')) as HTMLSelectElement;
    await user.selectOptions(parentSelect, 'tt-family');
    const childSelect = (await screen.findByTestId('child-ticket-type-0')) as HTMLSelectElement;
    await user.selectOptions(childSelect, 'tt-member');
    expect(childSelect.value).toBe('tt-member');

    // The guardian changes their own ticket away from the required type.
    await user.selectOptions(parentSelect, 'tt-solo');

    // The child's selection survives — not silently cleared.
    expect(childSelect.value).toBe('tt-member');
    const warning = await screen.findByTestId('child-ticket-composition-0');
    expect(warning.textContent).toContain('requires at least one Familjebiljett');
    // Flagged on the control itself, not just a caption beside it.
    expect(childSelect.getAttribute('aria-invalid')).toBe('true');
    expect(childSelect.getAttribute('aria-describedby')).toContain('child-ticket-composition-0');

    // The total keeps pricing the flagged selection but marks it provisional.
    await screen.findByTestId('register-total-provisional');
  });

  it('flags the family-member selection when the person holding the required ticket is removed', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(familyEventInfo());
    render(RegisterPage);

    // A second parent so the first can be removed (the remove button only
    // shows once there's more than one row).
    await screen.findByTestId('parent-ticket-type-0');
    await user.click(screen.getByText(/Add parent/));
    const parentSelect0 = (await screen.findByTestId('parent-ticket-type-0')) as HTMLSelectElement;
    await user.selectOptions(parentSelect0, 'tt-family');

    const childSelect = (await screen.findByTestId('child-ticket-type-0')) as HTMLSelectElement;
    await user.selectOptions(childSelect, 'tt-member');
    expect(childSelect.value).toBe('tt-member');

    // Remove the parent holding the only Familjebiljett — not a select
    // edit at all, the route this increment exists to cover.
    const removeButtons = screen.getAllByText('Remove parent');
    await user.click(removeButtons[0]);

    // The child's member ticket is preserved, not silently cleared — and
    // is now visibly flagged rather than left looking fine.
    expect(childSelect.value).toBe('tt-member');
    const warning = await screen.findByTestId('child-ticket-composition-0');
    expect(warning.textContent).toContain('requires at least one Familjebiljett');
    expect(childSelect.getAttribute('aria-invalid')).toBe('true');
    await screen.findByTestId('register-total-provisional');
  });
});

// Idempotency key — added 2026-09-24 alongside the backend's
// RegistrationIdempotencyKey (see registrations/models.py) after an audit
// found no protection anywhere against a retried submit POST. These tests
// cover only the frontend's half of the contract: the key stays put across
// a retry of the same attempt, and only resets where the guardian is
// genuinely starting a new one (editing the email after a success).
// Ticket-type-free event info, so a submit only needs contact email +
// one filled-in child (the default row) to pass client-side validation —
// nothing here is about ticket selection.
function ticketlessEventInfo(overrides: Partial<Record<string, unknown>> = {}) {
  return baseEventInfo({ ticket_types: [], ...overrides });
}

async function fillMinimalRequiredFields(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByTestId('register-contact-email'), 'guardian@example.com');
  await user.type(document.getElementById('child-first-name-0') as HTMLInputElement, 'Alex');
  await user.type(document.getElementById('child-last-name-0') as HTMLInputElement, 'Karlsson');
  await user.type(document.getElementById('child-birthdate-0') as HTMLInputElement, '2015-05-01');
  await user.tab();
}

describe('Register page — idempotency key', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('sends the same idempotency_key on a retried submit after a failed attempt', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    // First attempt drops (e.g. a network failure) with no response at
    // all; the guardian clicks submit again with the form untouched —
    // exactly the retry this key exists to make safe.
    submit.mockRejectedValueOnce(new Error('network error'));
    submit.mockResolvedValueOnce({ reference_code: 'REF1', message: 'ok', email_sent: true });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await fillMinimalRequiredFields(user);

    const submitButton = screen.getByTestId('register-submit-button');
    await user.click(submitButton);
    await waitFor(() => expect(submit).toHaveBeenCalledTimes(1));

    await user.click(submitButton);
    await waitFor(() => expect(submit).toHaveBeenCalledTimes(2));

    const firstKey = (submit.mock.calls[0][0] as { idempotency_key?: string }).idempotency_key;
    const secondKey = (submit.mock.calls[1][0] as { idempotency_key?: string }).idempotency_key;
    expect(firstKey).toBeTruthy();
    expect(secondKey).toBe(firstKey);
  });

  it('issues a fresh idempotency_key after editing the email post-success and resubmitting', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    submit.mockResolvedValue({ reference_code: 'REF1', message: 'ok', email_sent: true });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await fillMinimalRequiredFields(user);
    await user.click(screen.getByTestId('register-submit-button'));
    await waitFor(() => expect(submit).toHaveBeenCalledTimes(1));
    const firstKey = (submit.mock.calls[0][0] as { idempotency_key?: string }).idempotency_key;

    // "Wrong email? Edit it" — the one point in this flow that is a
    // genuinely new attempt, not a retry of the one that just succeeded.
    await user.click(screen.getByTestId('register-edit-email'));
    await screen.findByTestId('register-form');
    await user.click(screen.getByTestId('register-submit-button'));
    await waitFor(() => expect(submit).toHaveBeenCalledTimes(2));

    const secondKey = (submit.mock.calls[1][0] as { idempotency_key?: string }).idempotency_key;
    expect(secondKey).toBeTruthy();
    expect(secondKey).not.toBe(firstKey);
  });

  it('omits idempotency_key from the resend request, unlike the primary submit', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    submit.mockResolvedValue({ reference_code: 'REF1', message: 'ok', email_sent: true });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await fillMinimalRequiredFields(user);
    await user.click(screen.getByTestId('register-submit-button'));
    await waitFor(() => expect(submit).toHaveBeenCalledTimes(1));
    expect(
      (submit.mock.calls[0][0] as { idempotency_key?: string }).idempotency_key
    ).toBeTruthy();

    // No data-testid on the resend Button; the i18n mock falls back to
    // rendering an unmapped key verbatim, so the key itself is the text.
    await user.click(screen.getByText('register.resendButton'));
    await waitFor(() => expect(submit).toHaveBeenCalledTimes(2));

    const resendPayload = submit.mock.calls[1][0] as { idempotency_key?: string };
    expect(resendPayload.idempotency_key).toBeUndefined();
  });

  // P1 (gate review, 2026-09-24): the "lost response" recovery UX — the
  // backend saw this key before with a different payload (code:
  // "idempotency_conflict"), most plausibly because an earlier submit
  // actually succeeded but the guardian never saw the response. See
  // idempotencyConflictPayload's own comment in +page.svelte.
  it('shows the idempotency-conflict guidance and resubmits with a fresh key on that button', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    submit.mockRejectedValueOnce({
      status: 409,
      message: 'This idempotency key was already used for a different submission.',
      details: {
        idempotency_key: ['This idempotency key was already used for a different submission.'],
        code: 'idempotency_conflict'
      }
    });
    submit.mockResolvedValueOnce({ reference_code: 'REF2', message: 'ok', email_sent: true });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await fillMinimalRequiredFields(user);
    await user.click(screen.getByTestId('register-submit-button'));
    await waitFor(() => expect(submit).toHaveBeenCalledTimes(1));

    // The dedicated guidance banner, not the generic error banner — and it
    // echoes the entered contact email.
    await screen.findByText(
      'Your registration may have already gone through. Check guardian@example.com for a confirmation before submitting again.'
    );

    const firstKey = (submit.mock.calls[0][0] as { idempotency_key?: string }).idempotency_key;
    const firstEmail = (submit.mock.calls[0][0] as { contact_email?: string }).contact_email;

    await user.click(screen.getByText('Send the confirmation again'));
    await waitFor(() => expect(submit).toHaveBeenCalledTimes(2));

    const secondCall = submit.mock.calls[1][0] as {
      idempotency_key?: string;
      contact_email?: string;
    };
    // A fresh key — this is a deliberate new attempt, not a replay of the
    // rejected one (see handleResubmitAfterConflict's comment) — but the
    // SAME payload otherwise: the captured, just-rejected attempt, not
    // lastSubmitPayload (which was never set — the first call never
    // succeeded).
    expect(secondCall.idempotency_key).toBeTruthy();
    expect(secondCall.idempotency_key).not.toBe(firstKey);
    expect(secondCall.contact_email).toBe(firstEmail);

    // A successful resubmit reaches the normal confirmation screen, same
    // as any other successful submit.
    await screen.findByTestId('register-success-email');
  });
});

// Capacity enforcement (registration dev-cycle round 4, increment 2, added
// 2026-09-24): the guest form must grey out a full ticket type rather than
// let a guardian find out at submit — mirrors the age-window disabled
// pattern above (commit ff4cc33), just keyed off `available` instead of a
// birthdate comparison.
function capacityEventInfo(overrides: Partial<Record<string, unknown>> = {}) {
  return baseEventInfo({
    ticket_types: [
      {
        id: 'tt-open',
        name: 'Adult',
        price: '100.00',
        // 'either', not 'parent': the default form always seeds one child
        // row too (fillMinimalRequiredFields fills it), and the page
        // requires *every* row to hold a ticket type once any exist on the
        // event at all (see the requiresTicketType check in handleSubmit)
        // — so the child row needs an option list to pick from as well.
        applies_to: 'either',
        min_birthdate: null,
        max_birthdate: null,
        kind: 'event',
        requires_ticket_type_id: null,
        max_per_required: null,
        available: true
      },
      {
        id: 'tt-full',
        name: 'VIP',
        price: '0.00',
        applies_to: 'either',
        min_birthdate: null,
        max_birthdate: null,
        kind: 'event',
        requires_ticket_type_id: null,
        max_per_required: null,
        available: false
      }
    ],
    ...overrides
  });
}

describe('Register page — ticket type capacity (sold out)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('disables a sold-out ticket option, keeps it in the list, and marks it', async () => {
    getEvent.mockResolvedValue(capacityEventInfo());
    render(RegisterPage);

    const select = (await screen.findByTestId('parent-ticket-type-0')) as HTMLSelectElement;
    const options = Array.from(select.options).filter((o) => o.value !== '');
    // Still both options present — disabled, not removed (same "don't
    // reorder/shrink mid-edit" reasoning as the age-window case).
    expect(options).toHaveLength(2);

    const openOption = options.find((o) => o.value === 'tt-open')!;
    const fullOption = options.find((o) => o.value === 'tt-full')!;
    expect(openOption.disabled).toBe(false);
    expect(fullOption.disabled).toBe(true);
    expect(fullOption.textContent).toContain('sold out');
  });

  it('leaves an available ticket selectable and submittable', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(capacityEventInfo());
    render(RegisterPage);

    const select = (await screen.findByTestId('parent-ticket-type-0')) as HTMLSelectElement;
    await user.selectOptions(select, 'tt-open');

    expect(select.value).toBe('tt-open');
    expect(screen.queryByTestId('parent-ticket-sold-out-0')).toBeNull();
  });

  it('shows the server-refused message if a race is lost at submit', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(capacityEventInfo());
    submit.mockRejectedValueOnce({
      status: 400,
      message: '"VIP" is sold out.',
      details: {
        ticket_type: ['"VIP" is sold out.'],
        code: 'ticket_sold_out'
      }
    });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    const select = (await screen.findByTestId('parent-ticket-type-0')) as HTMLSelectElement;
    // Selecting the (still momentarily) open option and submitting — the
    // server is the one that loses the race here, not the client-side
    // disabled state, which is exactly the scenario this covers.
    await user.selectOptions(select, 'tt-open');
    await fillMinimalRequiredFields(user);
    await user.click(screen.getByTestId('register-submit-button'));

    await waitFor(() => expect(submit).toHaveBeenCalledTimes(1));
    // extractErrorMessage's generic fallback surfaces the server's own
    // named-ticket message straight from the response body — no special
    // client-side handling of `code: "ticket_sold_out"` needed.
    await screen.findByText('"VIP" is sold out.');
  });
});

// Promo code (registration dev-cycle round 4, increment 3): an audit flagged
// "a rejected promo code still submits" as unverified. Investigation found
// the backend already refuses an invalid/expired/exhausted code at submit
// (400, registration never created) — these tests cover the frontend gap
// that was real: nothing stopped a guardian from submitting a promo code
// that was typed but never (successfully) validated, and a code's
// is_hidden-ticket-type unlock outliving the code itself.
//
// Revised (same dev-cycle, gated critique round): R1 — a promo code that
// changes the ticket-type option list could desync a hand-picked <select>
// from state (svelte 5.43.14 bind:value bug, see
// handleParentTicketTypeChange's comment in +page.svelte). R2 — an applied
// code is now a chip + explicit "Ta bort", not silently un-appliable by
// typing over it. R3 — the applied confirmation states the actual effect.
// R4 — a visible, associated label plus aria-live status/error. R5 — the
// shared invalid-code message now suggests a next step.
function hiddenTicketEventInfo(overrides: Partial<Record<string, unknown>> = {}) {
  return baseEventInfo({
    ticket_types: [
      {
        id: 'tt-child',
        name: 'Barn (0-12 år)',
        price: '100.00',
        applies_to: 'child',
        min_birthdate: null,
        max_birthdate: null,
        kind: 'event',
        requires_ticket_type_id: null,
        max_per_required: null,
        available: true
      }
    ],
    has_hidden_ticket_types: true,
    ...overrides
  });
}

const vipTicketType = {
  id: 'tt-vip',
  name: 'VIP',
  price: '500.00',
  applies_to: 'child',
  min_birthdate: null,
  max_birthdate: null,
  kind: 'event',
  requires_ticket_type_id: null,
  max_per_required: null,
  available: true
};

describe('Register page — promo code', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('blocks submit with a field error when a code is typed but never applied', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await fillMinimalRequiredFields(user);
    await user.type(screen.getByTestId('register-promo-code-input'), 'SAVE10');
    await user.click(screen.getByTestId('register-submit-button'));

    expect(submit).not.toHaveBeenCalled();
    const fieldError = await screen.findByTestId('register-promo-code-error');
    expect(fieldError.textContent).toContain('Apply this code, or clear the field');
  });

  it('blocks submit when Apply already rejected the code, and never sends it', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    validatePromoCode.mockResolvedValue({ valid: false });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await fillMinimalRequiredFields(user);
    await user.type(screen.getByTestId('register-promo-code-input'), 'BADCODE');
    await user.click(screen.getByTestId('register-promo-code-apply'));
    await screen.findByTestId('register-promo-code-error');

    await user.click(screen.getByTestId('register-submit-button'));

    expect(submit).not.toHaveBeenCalled();
  });

  // R5: one shared invalid message (deliberate — no leak of which codes
  // exist), but with a next step attached.
  it('gives a next-step hint alongside the shared invalid-code message', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    validatePromoCode.mockResolvedValue({ valid: false });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await user.type(screen.getByTestId('register-promo-code-input'), 'BADCODE');
    await user.click(screen.getByTestId('register-promo-code-apply'));

    const fieldError = await screen.findByTestId('register-promo-code-error');
    expect(fieldError.textContent).toContain("isn't valid");
    expect(fieldError.textContent).toContain('Check the spelling, or contact the organiser');
  });

  // R4: a real <label>, associated by `for`/id, not just a placeholder —
  // and the input/Apply button sit on the interactive-control radius rung
  // (rounded-button), not the bare `rounded` other legacy fields on this
  // page still use.
  it('has a visible label associated with the promo code input, on rounded-button controls', async () => {
    getEvent.mockResolvedValue(ticketlessEventInfo());
    render(RegisterPage);

    await screen.findByTestId('register-form');
    const input = screen.getByLabelText('Promo code') as HTMLInputElement;
    expect(input).toBe(screen.getByTestId('register-promo-code-input'));
    expect(input.className).toContain('rounded-button');
    expect(input.className).not.toMatch(/\brounded\b(?!-)/);

    const applyButton = screen.getByTestId('register-promo-code-apply');
    expect(applyButton.className).toContain('rounded-button');
  });

  // R4: while an error shows, the input is flagged for assistive tech and
  // points at the message that explains why.
  it('marks the input aria-invalid and aria-describedby while the invalid-code message shows', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    validatePromoCode.mockResolvedValue({ valid: false });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    const input = screen.getByTestId('register-promo-code-input');
    expect(input.getAttribute('aria-invalid')).toBe('false');

    await user.type(input, 'BADCODE');
    await user.click(screen.getByTestId('register-promo-code-apply'));
    const fieldError = await screen.findByTestId('register-promo-code-error');

    expect(input.getAttribute('aria-invalid')).toBe('true');
    expect(input.getAttribute('aria-describedby')).toBe(fieldError.id);
    expect(fieldError.getAttribute('aria-live')).toBe('polite');
  });

  // R2: once applied, the only way to change the code is the explicit "Ta
  // bort" on the chip — typing over the (now hidden) input isn't possible,
  // so this becomes "Ta bort, then type a new code without applying".
  it('blocks submit after Ta bort, then typing a new code without re-applying', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    validatePromoCode.mockResolvedValue({
      valid: true,
      discount_type: 'fixed',
      discount_value: '10',
      applies_to_ticket_type_ids: [],
      unlocks_ticket_types: []
    });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await fillMinimalRequiredFields(user);
    await user.type(screen.getByTestId('register-promo-code-input'), 'SAVE10');
    await user.click(screen.getByTestId('register-promo-code-apply'));
    await screen.findByTestId('register-promo-code-chip');

    await user.click(screen.getByTestId('register-promo-code-remove'));
    expect(screen.queryByTestId('register-promo-code-chip')).toBeNull();

    const newPromoInput = screen.getByTestId('register-promo-code-input');
    await user.type(newPromoInput, 'OTHER');

    await user.click(screen.getByTestId('register-submit-button'));
    expect(submit).not.toHaveBeenCalled();
    await screen.findByTestId('register-promo-code-error');
  });

  it('submits normally once a typed code matches the last successful validation', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    validatePromoCode.mockResolvedValue({
      valid: true,
      discount_type: 'fixed',
      discount_value: '10',
      applies_to_ticket_type_ids: [],
      unlocks_ticket_types: []
    });
    submit.mockResolvedValue({ reference_code: 'REF1', message: 'ok', email_sent: true });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await fillMinimalRequiredFields(user);
    await user.type(screen.getByTestId('register-promo-code-input'), 'SAVE10');
    await user.click(screen.getByTestId('register-promo-code-apply'));
    await screen.findByTestId('register-promo-code-chip');

    await user.click(screen.getByTestId('register-submit-button'));

    await waitFor(() => expect(submit).toHaveBeenCalledTimes(1));
    const payload = submit.mock.calls[0][0] as { promo_code?: string };
    expect(payload.promo_code).toBe('SAVE10');
  });

  describe('applied state — chip and stated effect', () => {
    // R2: a successful apply replaces the text input + Apply button with a
    // read-only chip (the code + a check) and an explicit "Ta bort" — the
    // input is genuinely gone, not just visually hidden, since editing an
    // applied code is no longer possible without un-applying it first.
    it('replaces the input with a code chip and a Ta bort button on successful apply', async () => {
      const user = userEvent.setup();
      getEvent.mockResolvedValue(ticketlessEventInfo());
      validatePromoCode.mockResolvedValue({
        valid: true,
        discount_type: 'fixed',
        discount_value: '10',
        applies_to_ticket_type_ids: [],
        unlocks_ticket_types: []
      });
      render(RegisterPage);

      await screen.findByTestId('register-form');
      await user.type(screen.getByTestId('register-promo-code-input'), 'SAVE10');
      await user.click(screen.getByTestId('register-promo-code-apply'));

      const chip = await screen.findByTestId('register-promo-code-chip');
      expect(chip.textContent).toContain('SAVE10');
      expect(screen.queryByTestId('register-promo-code-input')).toBeNull();
      expect(screen.queryByTestId('register-promo-code-apply')).toBeNull();
      expect(screen.getByTestId('register-promo-code-remove')).toBeInTheDocument();
    });

    // R3: the confirmation states the concrete effect, not just "applied".
    it('states a percent discount in the applied confirmation', async () => {
      const user = userEvent.setup();
      getEvent.mockResolvedValue(ticketlessEventInfo());
      validatePromoCode.mockResolvedValue({
        valid: true,
        discount_type: 'percent',
        discount_value: '15',
        applies_to_ticket_type_ids: [],
        unlocks_ticket_types: []
      });
      render(RegisterPage);

      await screen.findByTestId('register-form');
      await user.type(screen.getByTestId('register-promo-code-input'), 'SAVE15');
      await user.click(screen.getByTestId('register-promo-code-apply'));

      const applied = await screen.findByTestId('register-promo-code-applied');
      expect(applied.textContent).toContain('15% discount on the total.');
      expect(applied.getAttribute('aria-live')).toBe('polite');
    });

    it('states a fixed discount in the applied confirmation', async () => {
      const user = userEvent.setup();
      getEvent.mockResolvedValue(ticketlessEventInfo());
      validatePromoCode.mockResolvedValue({
        valid: true,
        discount_type: 'fixed',
        discount_value: '10',
        applies_to_ticket_type_ids: [],
        unlocks_ticket_types: []
      });
      render(RegisterPage);

      await screen.findByTestId('register-form');
      await user.type(screen.getByTestId('register-promo-code-input'), 'SAVE10');
      await user.click(screen.getByTestId('register-promo-code-apply'));

      const applied = await screen.findByTestId('register-promo-code-applied');
      expect(applied.textContent).toContain('10.00 kr discount on the total.');
    });

    it('states the unlocked ticket type in the applied confirmation', async () => {
      const user = userEvent.setup();
      getEvent.mockResolvedValue(hiddenTicketEventInfo());
      validatePromoCode.mockResolvedValue({
        valid: true,
        discount_type: 'fixed',
        discount_value: '0',
        applies_to_ticket_type_ids: [],
        unlocks_ticket_types: [vipTicketType]
      });
      render(RegisterPage);

      await screen.findByTestId('register-form');
      await user.type(screen.getByTestId('register-promo-code-input'), 'VIPCODE');
      await user.click(screen.getByTestId('register-promo-code-apply'));

      const applied = await screen.findByTestId('register-promo-code-applied');
      expect(applied.textContent).toContain('VIP — now available under Ticket type.');
      // A zero-value discount contributes nothing to the sentence.
      expect(applied.textContent).not.toContain('discount on the total');
    });
  });

  it('clearing an applied code via Ta bort retracts the hidden ticket type it unlocked, and any selection of it', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(hiddenTicketEventInfo());
    validatePromoCode.mockResolvedValue({
      valid: true,
      discount_type: 'fixed',
      discount_value: '0',
      applies_to_ticket_type_ids: [],
      unlocks_ticket_types: [vipTicketType]
    });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await fillMinimalRequiredFields(user);

    const promoInput = screen.getByTestId('register-promo-code-input');
    await user.type(promoInput, 'VIPCODE');
    await user.click(screen.getByTestId('register-promo-code-apply'));
    await screen.findByTestId('register-promo-code-chip');

    const childSelect = (await screen.findByTestId('child-ticket-type-0')) as HTMLSelectElement;
    expect(Array.from(childSelect.options).some((o) => o.value === 'tt-vip')).toBe(true);
    await user.selectOptions(childSelect, 'tt-vip');
    expect(childSelect.value).toBe('tt-vip');

    // "Ta bort" — the unlocked option must disappear again, and the
    // now-dangling selection must not be left pointing at it (the server
    // would otherwise reject it as "Invalid ticket type for this event.",
    // a confusing dead end with no visible cause).
    await user.click(screen.getByTestId('register-promo-code-remove'));
    expect(Array.from(childSelect.options).some((o) => o.value === 'tt-vip')).toBe(false);
    expect(childSelect.value).toBe('');
  });

  // R2: Ta bort is an explicit action, so it gets an explicit, named
  // confirmation of what it just changed — not a silent reset.
  it('names the retracted ticket and attendee in an aria-live line, and captions the reset select', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(hiddenTicketEventInfo());
    validatePromoCode.mockResolvedValue({
      valid: true,
      discount_type: 'fixed',
      discount_value: '0',
      applies_to_ticket_type_ids: [],
      unlocks_ticket_types: [vipTicketType]
    });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    const childSelect = (await screen.findByTestId('child-ticket-type-0')) as HTMLSelectElement;
    await user.type(screen.getByTestId('register-promo-code-input'), 'VIPCODE');
    await user.click(screen.getByTestId('register-promo-code-apply'));
    await screen.findByTestId('register-promo-code-chip');
    await user.selectOptions(childSelect, 'tt-vip');

    await user.click(screen.getByTestId('register-promo-code-remove'));

    const removalMessage = await screen.findByTestId('register-promo-removed-message');
    expect(removalMessage.textContent).toContain('VIP');
    expect(removalMessage.textContent).toContain('Child 1');
    expect(removalMessage.getAttribute('aria-live')).toBe('polite');

    const caption = await screen.findByTestId('child-ticket-promo-reset-0');
    expect(childSelect.getAttribute('aria-describedby')).toContain(caption.id);
  });

  it("clears a row's reset caption as soon as that row picks a ticket again", async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(hiddenTicketEventInfo());
    validatePromoCode.mockResolvedValue({
      valid: true,
      discount_type: 'fixed',
      discount_value: '0',
      applies_to_ticket_type_ids: [],
      unlocks_ticket_types: [vipTicketType]
    });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    const childSelect = (await screen.findByTestId('child-ticket-type-0')) as HTMLSelectElement;
    await user.type(screen.getByTestId('register-promo-code-input'), 'VIPCODE');
    await user.click(screen.getByTestId('register-promo-code-apply'));
    await screen.findByTestId('register-promo-code-chip');
    await user.selectOptions(childSelect, 'tt-vip');
    await user.click(screen.getByTestId('register-promo-code-remove'));
    await screen.findByTestId('child-ticket-promo-reset-0');

    await user.selectOptions(childSelect, 'tt-child');

    expect(screen.queryByTestId('child-ticket-promo-reset-0')).toBeNull();
    expect(childSelect.getAttribute('aria-describedby') ?? '').not.toContain('child-ticket-promo-reset-0');
  });

  // Follow-up (confirmation-persona gate): the field-level aria-live removal
  // line must not outlive the problem it announced — once every attendee it
  // named has repicked a ticket, it should drop, matching the per-row
  // caption's own clearing rule tested above.
  it('drops the field-level removal message once every named attendee has repicked a ticket', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(promoUnlockEventInfo());
    validatePromoCode.mockResolvedValue({
      valid: true,
      discount_type: 'fixed',
      discount_value: '0',
      applies_to_ticket_type_ids: [],
      unlocks_ticket_types: [vipWeekendTicketType]
    });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    const parentSelect = (await screen.findByTestId('parent-ticket-type-0')) as HTMLSelectElement;
    await user.type(screen.getByTestId('register-promo-code-input'), 'VIPUNLOCK');
    await user.click(screen.getByTestId('register-promo-code-apply'));
    await screen.findByTestId('register-promo-code-chip');
    await user.selectOptions(parentSelect, 'tt-vip-weekend');

    await user.click(screen.getByTestId('register-promo-code-remove'));
    await screen.findByTestId('register-promo-removed-message');
    await screen.findByTestId('parent-ticket-promo-reset-0');

    // The one row the message named repicks a ticket — the per-row caption
    // clears (already covered above); the field-level line must clear too,
    // not linger describing a now-resolved row.
    await user.selectOptions(parentSelect, 'tt-adult');

    expect(screen.queryByTestId('register-promo-removed-message')).toBeNull();
  });
});

// R1 (registration dev-cycle round 4, increment 3 revision, gated
// critique): a browser critic found that picking a ticket type by hand and
// then applying/removing a promo code could leave the <select> showing the
// "Välj biljettyp" placeholder while state still held the pick — svelte
// 5.43.14's bind_select_value only writes select.__value from its own
// state→DOM effect, which early-returns while the select is focused and the
// change came from that same batch, so __value sticks at the mount value
// (""); init_select's MutationObserver on the option list then reasserts
// that stale __value onto the DOM. These reproduce it via exactly the
// trigger the critic used (a promo code changing the option list) — both
// were confirmed FAILING against the old bind:value markup before the fix
// (see the fix's own comment on handleParentTicketTypeChange /
// handleChildTicketTypeChange in +page.svelte), and jsdom does reproduce
// it: this is pure Svelte-runtime JS, not a native-browser-only quirk.
function promoUnlockEventInfo(overrides: Partial<Record<string, unknown>> = {}) {
  return baseEventInfo({
    ticket_types: [
      {
        id: 'tt-adult',
        name: 'Vuxen',
        price: '1100.00',
        applies_to: 'parent',
        min_birthdate: null,
        max_birthdate: null,
        kind: 'event',
        requires_ticket_type_id: null,
        max_per_required: null,
        available: true
      },
      {
        id: 'tt-child',
        name: 'Barn (0-12 år)',
        price: '100.00',
        applies_to: 'child',
        min_birthdate: null,
        max_birthdate: null,
        kind: 'event',
        requires_ticket_type_id: null,
        max_per_required: null,
        available: true
      }
    ],
    has_hidden_ticket_types: true,
    ...overrides
  });
}

const vipWeekendTicketType = {
  id: 'tt-vip-weekend',
  name: 'VIP-helg',
  price: '0.00',
  applies_to: 'either',
  min_birthdate: null,
  max_birthdate: null,
  kind: 'event',
  requires_ticket_type_id: null,
  max_per_required: null,
  available: true
};

describe('Register page — promo code (ticket-select stays in sync with state)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('keeps a hand-picked parent ticket visible after a promo code unlocks a new option', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(promoUnlockEventInfo());
    validatePromoCode.mockResolvedValue({
      valid: true,
      discount_type: 'fixed',
      discount_value: '0',
      applies_to_ticket_type_ids: [],
      unlocks_ticket_types: [vipWeekendTicketType]
    });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    const parentSelect = (await screen.findByTestId('parent-ticket-type-0')) as HTMLSelectElement;
    parentSelect.focus();
    await user.selectOptions(parentSelect, 'tt-adult');
    expect(parentSelect.value).toBe('tt-adult');

    await user.type(screen.getByTestId('register-promo-code-input'), 'VIPUNLOCK');
    await user.click(screen.getByTestId('register-promo-code-apply'));
    await screen.findByTestId('register-promo-code-chip');

    // The DOM select must still reflect the guardian's own pick — not the
    // "" placeholder the bind:value bug leaves it showing.
    expect(parentSelect.value).toBe('tt-adult');
  });

  it("keeps a child's hand-picked selection after Ta bort resets the parent's unlocked pick", async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(promoUnlockEventInfo());
    validatePromoCode.mockResolvedValue({
      valid: true,
      discount_type: 'fixed',
      discount_value: '0',
      applies_to_ticket_type_ids: [],
      unlocks_ticket_types: [vipWeekendTicketType]
    });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    const childSelect = (await screen.findByTestId('child-ticket-type-0')) as HTMLSelectElement;
    childSelect.focus();
    await user.selectOptions(childSelect, 'tt-child');
    expect(childSelect.value).toBe('tt-child');

    await user.type(screen.getByTestId('register-promo-code-input'), 'VIPUNLOCK');
    await user.click(screen.getByTestId('register-promo-code-apply'));
    await screen.findByTestId('register-promo-code-chip');

    const parentSelect = (await screen.findByTestId('parent-ticket-type-0')) as HTMLSelectElement;
    parentSelect.focus();
    await user.selectOptions(parentSelect, 'tt-vip-weekend');
    expect(parentSelect.value).toBe('tt-vip-weekend');

    await user.click(screen.getByTestId('register-promo-code-remove'));

    expect(childSelect.value).toBe('tt-child');
    expect(parentSelect.value).toBe('');
  });
});
