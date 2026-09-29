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
    'register.parentLabel': 'Parent {number}',
    // Error-summary banner (increment 5, 2026-09-28) — mapped for real here
    // (rather than left to the fallback-to-raw-key behavior below) so tests
    // can assert on the actual named, interpolated sentence a guardian
    // would see, not just the translation key.
    'register.contactEmailRequired': 'A valid email address is required.',
    'register.ticketTypeRequired': 'Choose a ticket type for {name}.',
    'register.relationshipRequired': 'Choose a relationship for {name}.',
    'register.requiredExtraMissing': 'Choose {extra} for {name}.',
    'register.requiredExtraMissingRegistration': 'Make a choice for {extra}.',
    'register.errorBannerHeading': 'Please fix the following before you can submit:',
    // R4 (registration dev-cycle round 4, increment 5 revision): the visual
    // "*" span in the legend markup already states the marker once — this
    // sentence must not repeat it as a literal character.
    'register.requiredFieldLegend': 'marks a required field.',
    'register.childInfoIncomplete': 'Fill in first name, last name and birthdate for {name}.',
    'register.fieldErrorNamed': '{name}: {message}'
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

// registration_already_pending (registration dev-cycle round 4, increment 6,
// 2026-09-29): the backend's (event, contact_email) dedup for a still-pending
// registration used to come back as a plain 2xx with no way to tell it apart
// from a genuine new registration — a guardian who used "Edit and resend" to
// add a forgotten child saw the ordinary success screen while the child was
// silently dropped (2026-09-28 incident). The backend now rides a `code` on
// that same 2xx body; these tests cover the frontend routing on it.
describe('Register page — registration already pending (dedup made visible)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows the dedicated pending-duplicate screen, not the ordinary success screen, when the backend resent a fresh email', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    submit.mockResolvedValue({
      reference_code: 'REF9',
      message: 'A registration for this email is already waiting for confirmation.',
      email_sent: true,
      code: 'registration_already_pending'
    });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await fillMinimalRequiredFields(user);
    await user.click(screen.getByTestId('register-submit-button'));

    await screen.findByTestId('register-pending-duplicate');
    expect(screen.queryByTestId('register-success-email')).not.toBeInTheDocument();
    // A fresh email really did go out — the "we sent a new one" copy, not
    // the "use the one already sent" copy.
    expect(screen.getByText('register.pendingDuplicateEmailResent')).toBeInTheDocument();
    expect(screen.queryByText('register.pendingDuplicateUseExisting')).not.toBeInTheDocument();
    expect(screen.getByTestId('register-pending-duplicate-reference')).toBeInTheDocument();
  });

  it('shows "use the email already sent" (not "we sent a new one") when the backend was throttled by the resend cooldown', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    // Throttled branch: no email_sent field at all (see
    // registrations/views.py — the cooldown branch never attempts a send).
    submit.mockResolvedValue({
      reference_code: 'REF9',
      message: 'A registration for this email is already waiting for confirmation.',
      code: 'registration_already_pending'
    });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await fillMinimalRequiredFields(user);
    await user.click(screen.getByTestId('register-submit-button'));

    await screen.findByTestId('register-pending-duplicate');
    expect(screen.getByText('register.pendingDuplicateUseExisting')).toBeInTheDocument();
    expect(screen.queryByText('register.pendingDuplicateEmailResent')).not.toBeInTheDocument();
  });

  it('the pending-duplicate screen\'s back button reuses the same "back into the form" action as the success screen\'s relabelled link', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    submit.mockResolvedValueOnce({
      reference_code: 'REF9',
      message: 'A registration for this email is already waiting for confirmation.',
      code: 'registration_already_pending'
    });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await fillMinimalRequiredFields(user);
    await user.click(screen.getByTestId('register-submit-button'));
    await screen.findByTestId('register-pending-duplicate');

    // Same handler, same label key as the success screen's relabelled
    // "editEmailButton" (Button has no data-testid passthrough — see
    // Button.svelte — so this targets it by its rendered text, same as the
    // idempotency-conflict button above) — no longer promises editing the
    // sent registration, just drops back into the still-populated form.
    await user.click(screen.getByText('register.editEmailButton'));
    await screen.findByTestId('register-form');
    expect(screen.queryByTestId('register-pending-duplicate')).not.toBeInTheDocument();

    // A fresh idempotency key, exactly like the success screen's own "edit
    // and resubmit" path — this is a genuinely new attempt.
    submit.mockResolvedValueOnce({ reference_code: 'REF10', message: 'ok', email_sent: true });
    await user.click(screen.getByTestId('register-submit-button'));
    await waitFor(() => expect(submit).toHaveBeenCalledTimes(2));
    const firstKey = (submit.mock.calls[0][0] as { idempotency_key?: string }).idempotency_key;
    const secondKey = (submit.mock.calls[1][0] as { idempotency_key?: string }).idempotency_key;
    expect(secondKey).toBeTruthy();
    expect(secondKey).not.toBe(firstKey);
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

// 2026-09-24 owner decision (kitchen counts / data quality): default_selected
// must never pre-tick an extra on this public guest form, even though the
// backend field itself is unchanged and other consumers (admin, event
// cloning, demo seeding) still honor it — see +page.svelte's extraState.
function extrasEventInfo(overrides: Partial<Record<string, unknown>> = {}) {
  return baseEventInfo({
    extras: [
      {
        id: 'extra-meals',
        name: 'Måltider hela helgen',
        price: '300.00',
        session_id: null,
        per_attendee: true,
        applies_to: 'either',
        requires_choice: false,
        required: false,
        default_selected: true,
        choices: []
      }
    ],
    ...overrides
  });
}

describe('Register page — extras default state', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('starts an opt-out extra unticked even when the event marks it default_selected, and prices it as 0', async () => {
    getEvent.mockResolvedValue(extrasEventInfo());
    render(RegisterPage);

    // per_attendee + applies_to 'either' renders this extra on both the
    // parent row and the child row — assert every instance, not just one.
    const checkboxes = await screen.findAllByRole('checkbox', { name: /Måltider hela helgen/ });
    expect(checkboxes.length).toBeGreaterThan(0);
    for (const checkbox of checkboxes) {
      expect(checkbox).not.toBeChecked();
    }

    const total = await screen.findByTestId('register-running-total');
    expect(total.textContent).toContain('0.00');
    expect(total.textContent).not.toContain('300.00');
  });

  it('prices the extra once the guardian explicitly ticks it', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(extrasEventInfo());
    render(RegisterPage);

    const [checkbox] = await screen.findAllByRole('checkbox', { name: /Måltider hela helgen/ });
    await user.click(checkbox);
    expect(checkbox).toBeChecked();

    const total = await screen.findByTestId('register-running-total');
    expect(total.textContent).toContain('300.00');
  });

  it('still defaults a required extra to selected, since it has no checkbox to opt out with', async () => {
    getEvent.mockResolvedValue(
      extrasEventInfo({
        extras: [
          {
            id: 'extra-cabin',
            name: 'Boende',
            price: '500.00',
            session_id: null,
            per_attendee: false,
            applies_to: 'either',
            requires_choice: false,
            required: true,
            default_selected: false,
            choices: []
          }
        ]
      })
    );
    render(RegisterPage);

    const total = await screen.findByTestId('register-running-total');
    expect(total.textContent).toContain('500.00');
  });
});

describe('Register page — Relation is required (no default)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('blocks submit with a clear message when a named parent has not chosen a relationship', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await fillMinimalRequiredFields(user);
    // Naming a parent row makes it a "valid" parent that must be submitted
    // — and therefore must have a Relation chosen.
    await user.type(document.getElementById('parent-first-name-0') as HTMLInputElement, 'Kim');

    const relationSelect = screen.getByTestId('parent-relationship-0') as HTMLSelectElement;
    expect(relationSelect.value).toBe('');

    await user.click(screen.getByTestId('register-submit-button'));

    expect(submit).not.toHaveBeenCalled();
    // Increment 5 (2026-09-28): the banner names who it's about, using the
    // typed first name — not a generic "choose a relationship for
    // everyone" line (see the error-summary describe block below for the
    // fallback-to-ordinal-label case, which only applies to attendees with
    // no name typed at all).
    const bannerItem = await screen.findByText('Choose a relationship for Kim.');
    const caption = await screen.findByTestId('parent-relationship-missing-0');
    expect(caption.textContent).toBe('register.relationshipRequiredCaption');
    expect(relationSelect.getAttribute('aria-invalid')).toBe('true');
    expect(relationSelect.getAttribute('aria-describedby')).toBe('parent-relationship-missing-0');

    // Clicking the banner line focuses the field it's about.
    await user.click(bannerItem);
    expect(document.activeElement).toBe(relationSelect);
  });

  it('submits once a relationship is chosen', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    submit.mockResolvedValue({ reference_code: 'REF1', message: 'ok', email_sent: true });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await fillMinimalRequiredFields(user);
    await user.type(document.getElementById('parent-first-name-0') as HTMLInputElement, 'Kim');

    const relationSelect = screen.getByTestId('parent-relationship-0') as HTMLSelectElement;
    await user.selectOptions(relationSelect, 'MOM');

    await user.click(screen.getByTestId('register-submit-button'));

    await waitFor(() => expect(submit).toHaveBeenCalledTimes(1));
    const payload = submit.mock.calls[0][0] as { parents: Array<{ relationship_type: string }> };
    expect(payload.parents[0].relationship_type).toBe('MOM');
  });

  it('does not block submit when no parent row is named', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    submit.mockResolvedValue({ reference_code: 'REF1', message: 'ok', email_sent: true });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await fillMinimalRequiredFields(user);
    // Default parent row is left entirely empty (not "valid"), so Relation
    // must not be required for it.
    await user.click(screen.getByTestId('register-submit-button'));

    await waitFor(() => expect(submit).toHaveBeenCalledTimes(1));
  });
});

// Increment 5 (2026-09-28) — driven by a gate finding: a parent who
// submitted without picking Boende (a required per-attendee choice) got a
// generic "a required choice is missing for everyone"-style message with no
// hint of which field or which person, and had to hunt through the whole
// form. These cover the top-of-form error summary that replaced it: one
// named line per problem, each a clickable link into the field it's about.
function boendeEventInfo(overrides: Partial<Record<string, unknown>> = {}) {
  return ticketlessEventInfo({
    extras: [
      {
        id: 'extra-boende',
        name: 'Boende',
        price: '0.00',
        session_id: null,
        per_attendee: true,
        applies_to: 'either',
        requires_choice: true,
        required: true,
        default_selected: false,
        choices: [
          { id: 'choice-tent', label: 'Tält', price_delta: '0.00' },
          { id: 'choice-cabin', label: 'Stuga', price_delta: '0.00' }
        ]
      }
    ],
    ...overrides
  });
}

describe('Register page — error summary banner', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('names the attendee for a missing required-choice extra, and a click focuses the choice', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(boendeEventInfo());
    render(RegisterPage);

    await screen.findByTestId('register-form');
    // fillMinimalRequiredFields names the default child "Alex" but never
    // touches Boende, which this event marks required.
    await fillMinimalRequiredFields(user);

    await user.click(screen.getByTestId('register-submit-button'));

    expect(submit).not.toHaveBeenCalled();
    const bannerItem = await screen.findByText('Choose Boende for Alex.');

    const fieldset = screen.getByTestId('child-extra-required-extra-boende-0');
    const firstChoice = fieldset.querySelector('input[type="radio"]') as HTMLInputElement;
    await user.click(bannerItem);
    expect(document.activeElement).toBe(firstChoice);
  });

  it('falls back to the ordinal label for an attendee with no name typed', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(baseEventInfo());
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await fillMinimalRequiredFields(user);
    await user.selectOptions(screen.getByTestId('child-ticket-type-0'), 'tt-child');

    // A second child, left entirely blank — no birthdate means
    // suggestChildTicketType never auto-picks a type for it (see
    // handleChildBirthdateChange), so the missing-ticket-type problem is
    // still live for this row and must name it with the ordinal fallback,
    // same as the (also true, but separate) "fill in this child's info"
    // problem for the same untouched row.
    await user.click(screen.getByText(/Add another child/));

    await user.click(screen.getByTestId('register-submit-button'));

    expect(submit).not.toHaveBeenCalled();
    await screen.findByText('Choose a ticket type for Child 2.');
  });

  it('lists more than one problem at once, instead of stopping at the first', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(boendeEventInfo());
    render(RegisterPage);

    await screen.findByTestId('register-form');
    // Neither the contact email nor the child's Boende choice is filled in.
    await user.type(document.getElementById('child-first-name-0') as HTMLInputElement, 'Leo');
    await user.type(document.getElementById('child-last-name-0') as HTMLInputElement, 'Karlsson');
    await user.type(document.getElementById('child-birthdate-0') as HTMLInputElement, '2015-05-01');
    await user.tab();

    await user.click(screen.getByTestId('register-submit-button'));

    expect(submit).not.toHaveBeenCalled();
    await screen.findByText('A valid email address is required.');
    await screen.findByText('Choose Boende for Leo.');
  });

  it('marks the required controls this increment covers with `required`, and the form with novalidate', async () => {
    getEvent.mockResolvedValue(boendeEventInfo());
    render(RegisterPage);

    await screen.findByTestId('register-form');

    const form = screen.getByTestId('register-form') as HTMLFormElement;
    expect(form.noValidate).toBe(true);

    expect(screen.getByTestId('register-contact-email')).toBeRequired();
    expect(document.getElementById('child-first-name-0')).toBeRequired();
    expect(document.getElementById('child-last-name-0')).toBeRequired();
    expect(document.getElementById('child-birthdate-0')).toBeRequired();

    const boendeFieldset = screen.getByTestId('child-extra-required-extra-boende-0');
    for (const radio of boendeFieldset.querySelectorAll('input[type="radio"]')) {
      expect(radio).toBeRequired();
    }
  });
});

// Registration dev-cycle round 4, increment 5 revision (2026-09-29) — R1
// through R5 on top of the error summary above.
describe('Register page — error summary revision (R1-R5)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('R1: Förälder 1 first name carries no required star or attribute, and a blank row is still silently dropped', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    submit.mockResolvedValue({ reference_code: 'REF1', message: 'ok', email_sent: true });
    render(RegisterPage);

    await screen.findByTestId('register-form');

    const firstNameInput = document.getElementById('parent-first-name-0') as HTMLInputElement;
    expect(firstNameInput).not.toBeRequired();
    expect(firstNameInput.getAttribute('aria-required')).toBeNull();
    // The owner deferred the actual guardian requirement (knowitall
    // c129cd8d) — this label must not promise an enforcement the form
    // doesn't have.
    const label = document.querySelector('label[for="parent-first-name-0"]');
    expect(label?.textContent?.trim()).toBe('checkin.parentFirstName');

    await fillMinimalRequiredFields(user);
    // Förälder 1 stays entirely blank.
    await user.click(screen.getByTestId('register-submit-button'));

    await waitFor(() => expect(submit).toHaveBeenCalledTimes(1));
    const payload = submit.mock.calls[0][0] as { parents: unknown[] };
    expect(payload.parents).toHaveLength(0);
  });

  it('R2: a malformed email produces a named, focusable banner line', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await user.type(screen.getByTestId('register-contact-email'), 'not-an-email');
    await user.type(document.getElementById('child-first-name-0') as HTMLInputElement, 'Alex');
    await user.type(document.getElementById('child-last-name-0') as HTMLInputElement, 'Karlsson');
    await user.type(document.getElementById('child-birthdate-0') as HTMLInputElement, '2015-05-01');
    await user.tab();

    await user.click(screen.getByTestId('register-submit-button'));

    expect(submit).not.toHaveBeenCalled();
    const bannerItem = await screen.findByText('A valid email address is required.');
    const emailInput = screen.getByTestId('register-contact-email');
    await user.click(bannerItem);
    expect(document.activeElement).toBe(emailInput);
  });

  it('R2: a server 400 on contact_email lands in the same banner item as the client-side check', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    submit.mockRejectedValueOnce({
      status: 400,
      message: 'Enter a valid email address.',
      details: { contact_email: ['Enter a valid email address.'] }
    });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await fillMinimalRequiredFields(user);

    await user.click(screen.getByTestId('register-submit-button'));

    await waitFor(() => expect(submit).toHaveBeenCalledTimes(1));
    await screen.findByText('Please fix the following before you can submit:');
    const bannerItem = await screen.findByText('A valid email address is required.');
    // Not the raw server string — the banner keeps its usual wording/item,
    // not extractErrorMessage's generic top line.
    expect(screen.queryByText('Enter a valid email address.')).not.toBeInTheDocument();

    const emailInput = screen.getByTestId('register-contact-email');
    await user.click(bannerItem);
    expect(document.activeElement).toBe(emailInput);
  });

  it('R3: aria-invalid and the danger border appear on a flagged field and clear as soon as it changes, removing the banner line', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await user.type(document.getElementById('child-first-name-0') as HTMLInputElement, 'Alex');
    await user.type(document.getElementById('child-last-name-0') as HTMLInputElement, 'Karlsson');
    await user.type(document.getElementById('child-birthdate-0') as HTMLInputElement, '2015-05-01');
    await user.tab();
    // Contact email left blank.

    await user.click(screen.getByTestId('register-submit-button'));

    expect(submit).not.toHaveBeenCalled();
    const emailInput = screen.getByTestId('register-contact-email') as HTMLInputElement;
    await screen.findByText('A valid email address is required.');
    expect(emailInput.getAttribute('aria-invalid')).toBe('true');
    expect(emailInput.className).toMatch(/border-danger-600/);

    await user.type(emailInput, 'guardian@example.com');

    expect(emailInput.getAttribute('aria-invalid')).toBe('false');
    expect(emailInput.className).not.toMatch(/border-danger-600/);
    expect(screen.queryByText('A valid email address is required.')).not.toBeInTheDocument();
    // The whole banner (heading and all) disappears once the last problem clears.
    expect(screen.queryByText('Please fix the following before you can submit:')).not.toBeInTheDocument();
  });

  it('R4: the error banner has role=alert and no aria-live (avoids double announcement)', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await user.click(screen.getByTestId('register-submit-button'));

    const banner = await screen.findByRole('alert');
    expect(banner.getAttribute('aria-live')).toBeNull();
  });

  it('R5: name/phone/email inputs carry maxlength matching the backend model limits', async () => {
    getEvent.mockResolvedValue(ticketlessEventInfo());
    render(RegisterPage);

    await screen.findByTestId('register-form');

    expect(screen.getByTestId('register-contact-email')).toHaveAttribute('maxlength', '254');
    expect(document.getElementById('family-name')).toHaveAttribute('maxlength', '255');
    expect(document.getElementById('parent-first-name-0')).toHaveAttribute('maxlength', '255');
    expect(document.getElementById('parent-last-name-0')).toHaveAttribute('maxlength', '255');
    expect(document.getElementById('parent-phone-0')).toHaveAttribute('maxlength', '50');
    expect(document.getElementById('parent-email-0')).toHaveAttribute('maxlength', '254');
    expect(document.getElementById('child-first-name-0')).toHaveAttribute('maxlength', '255');
    expect(document.getElementById('child-last-name-0')).toHaveAttribute('maxlength', '255');
  });
});
