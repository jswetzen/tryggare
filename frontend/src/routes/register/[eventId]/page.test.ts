import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
// The mocked pushState below (see the $app/navigation vi.mock further down)
// — imported here so the "Back button from confirmation" tests can assert
// on its call args, same pattern as `submit`/`getEvent`.
import { pushState } from '$app/navigation';
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
    'register.fieldErrorNamed': '{name}: {message}',
    // Guardian rule (owner decision eb5d26f4) — mapped so tests assert the
    // sentence a guardian actually reads, not the key.
    'register.guardianRequired': 'Add an adult guardian for the children.',
    'register.parentPhoneRequired': 'Enter a phone number for {name}.',
    'register.ticketGuardianOnly': 'No ticket – guardian only',
    // Guardian-only = not attending (owner decision d9245e21).
    'register.guardianOnlyCheckbox': 'Guardian only – I am not attending myself',
    'register.guardianOnlyNoHealth': '{name}: a guardian who is not attending cannot have health details.',
    'register.noOneAttending': 'At least one person on the registration needs to be attending.',
    // Success screen (increment 7 revision, R1/R2/R5) — mapped for real so
    // tests can assert the actual copy a guardian sees, same pattern as the
    // error-summary entries above. wrongEmailPrompt/fixEmailButton are
    // deliberately left unmapped (see the success-screen describe block's
    // own comment) — those tests only care about the button's identity and
    // position, not its exact wording.
    'register.successTitle': 'Confirm your email to finish',
    'register.successIntro':
      "We've received your registration to {event}. We've sent a confirmation link to:",
    'register.successIntroNotSent':
      "We've received your registration to {event}, but we couldn't send the confirmation link to:",
    'register.successCalloutText':
      "Your registration isn't complete until you click the link — within 48 hours.",
    'register.successSpamHint': "Don't see it? Check your spam folder.",
    'register.referenceCodeCopiedAnnouncement': 'Reference code copied',
    'register.summaryWholeRegistrationLine': 'Whole registration: {extras}',
    // Summary row states and the flat price line (guardian-only increment 2) —
    // mapped for real so tests assert the sentence a guardian reads.
    'register.summaryNoTicket': 'No ticket',
    'register.summaryAttending': 'Attending',
    'register.summaryGuardianOnly': 'Guardian – not attending',
    'register.summaryFlatPrice': 'Price for the whole registration',
    'register.summaryTotal': 'Total',
    'register.summaryDiscountLine': 'Discount ({code}) −{amount} kr',
    // Closed screen — mapped so the test can read the formatted instant.
    'register.closedMessage': 'Registration for {event} closed on {date}.'
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

// Increment 8 (registration dev-cycle round 4, 2026-09-29): a real,
// subscribable stand-in for $page — plain `readable(...)` (what this mock
// used to be) can't model $page.state changing, which is exactly what
// drives `submitted` now (see +page.svelte's own comment on that variable).
// vi.hoisted so both the $app/stores mock below and the $app/navigation
// mock's `pushState` (further down) can share one instance — a real
// pushState/$page pairing is provided by SvelteKit's router, which isn't
// present in this jsdom render.
const pageStateHelper = vi.hoisted(() => {
  const initial = {
    params: { eventId: 'event-1' },
    url: new URL('http://localhost/register/event-1'),
    state: {} as Record<string, unknown>
  };
  let current = initial;
  const subscribers = new Set<(v: typeof current) => void>();
  return {
    subscribe(fn: (v: typeof current) => void) {
      subscribers.add(fn);
      fn(current);
      return () => subscribers.delete(fn);
    },
    // Mirrors the real pushState(url, state)'s shallow-merge into
    // $page.state closely enough for these tests.
    pushState(_url: string, state: Record<string, unknown>) {
      current = { ...current, state: { ...current.state, ...state } };
      subscribers.forEach((fn) => fn(current));
    },
    // Test-only: simulates what SvelteKit's router does to $page.state on
    // popstate (a native browser Back/Forward) — jsdom has no real
    // navigable session history for `history.back()` (stubbed below) to
    // drive this from, see the history.back stub a few lines down.
    setState(state: Record<string, unknown>) {
      current = { ...current, state };
      subscribers.forEach((fn) => fn(current));
    }
  };
});

vi.mock('$app/stores', () => ({
  page: { subscribe: pageStateHelper.subscribe }
}));

vi.mock('$app/navigation', () => ({
  goto: vi.fn(),
  invalidate: vi.fn(),
  invalidateAll: vi.fn(),
  preloadData: vi.fn(),
  preloadCode: vi.fn(),
  beforeNavigate: vi.fn(),
  afterNavigate: vi.fn(),
  disableScrollHandling: vi.fn(),
  // Spy-able (tests assert on call args) AND wired to pageStateHelper (see
  // its own comment) so the component's derived `submitted` actually flips,
  // same as the real integration with SvelteKit's router.
  pushState: vi.fn((url: string, state: Record<string, unknown>) =>
    pageStateHelper.pushState(url, state)
  ),
  replaceState: vi.fn()
}));

// +page.svelte's handleEditEmail calls the real, global history.back() to
// pop the confirmation screen's pushState entry (see its own comment) — in
// the real app that fires a popstate SvelteKit's router listens for and
// resolves back to $page.state {}. Nothing here plays that role for a
// jsdom render with the router entirely mocked out, so this stub does it
// directly: simulate the same resolution pageStateHelper.setState would get
// from a real popstate.
vi.spyOn(window.history, 'back').mockImplementation(() => {
  pageStateHelper.setState({});
});

// pageStateHelper is a module-level singleton (see its own comment) shared
// by every test in this file — reset it before each one so a prior test's
// pushState doesn't leak `submitted: true` into the next test's fresh
// render. Each describe block below still runs its own vi.clearAllMocks()
// beforeEach for the API mocks; this is the one shared piece of state that
// isn't a mock and so isn't covered by that.
beforeEach(() => {
  pageStateHelper.setState({});
});

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

// Icon path data (see Icon.svelte) for the success screen's copy-button
// icon swap (R5, increment 7 revision) — asserting on the rendered path's
// `d` attribute proves the actual icon changed, not just the label text.
const COPY_ICON_PATH =
  'M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z';
const CHECK_CIRCLE_ICON_PATH = 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z';

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

// Names a parent row with everything a guardian needs besides a ticket
// choice: first name, relation, phone.
async function fillGuardian(user: ReturnType<typeof userEvent.setup>, index = 0) {
  await user.type(document.getElementById(`parent-first-name-${index}`) as HTMLInputElement, 'Sam');
  await user.selectOptions(screen.getByTestId(`parent-relationship-${index}`), 'GUARDIAN');
  await user.type(document.getElementById(`parent-phone-${index}`) as HTMLInputElement, '070-123 45 67');
}

// Guardian rule (owner decision eb5d26f4, 2026-09-29): a registration with a
// child needs a named adult with a relation and a phone number, so a
// "minimal valid submit" now includes one. `guardian: false` fills only the
// contact email and the child, for the tests that build the parent row
// themselves (or assert what happens without one).
async function fillMinimalRequiredFields(
  user: ReturnType<typeof userEvent.setup>,
  { guardian = true }: { guardian?: boolean } = {}
) {
  await user.type(screen.getByTestId('register-contact-email'), 'guardian@example.com');
  if (guardian) await fillGuardian(user);
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

// Success screen (registration dev-cycle round 4, increment 7, revised
// 2026-09-29 against a gated critique — see +page.svelte's own comment on
// the `submitted` block for the full reasoning). R1: this is a pending
// step, not a finish line — no green, a `mail` icon, a primary-toned 48h
// callout right after the email chip. R2: the summary now shows what a
// guardian actually picked (extras/accommodation), not just a ticket price,
// so it visibly reconciles with the total. R3: "wrong email" moves up under
// the chip; resend becomes the quiet last action. R4: an h1, still focused
// on arrival, naming the event. R5: the copy button announces itself to
// assistive tech and degrades to a text selection on clipboard failure.
describe('Register page — success screen (increment 7)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows the success heading as a focused h1 naming the event, with a primary (not green) mail icon', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    submit.mockResolvedValue({ reference_code: 'REF1', message: 'ok', email_sent: true });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await fillMinimalRequiredFields(user);
    await user.click(screen.getByTestId('register-submit-button'));

    const heading = await screen.findByTestId('register-success-heading');
    expect(heading.tagName).toBe('H1');
    expect(heading.textContent).toContain('Confirm your email to finish');
    await waitFor(() => expect(document.activeElement).toBe(heading));

    const icon = screen.getByTestId('register-success-icon');
    expect(icon.querySelector('svg')).toBeTruthy();
    expect(icon.className).toContain('bg-primary-50');
    expect(icon.className).not.toMatch(/success/);

    // Named in the intro sentence, not just implied (ticketlessEventInfo ->
    // baseEventInfo's name).
    expect(screen.getByTestId('register-success').textContent).toContain('Sommarläger 2026');
  });

  it('has no green/success styling anywhere on the screen — a pending step, not a finish line', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    submit.mockResolvedValue({ reference_code: 'REF1', message: 'ok', email_sent: true });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await fillMinimalRequiredFields(user);
    await user.click(screen.getByTestId('register-submit-button'));

    const container = await screen.findByTestId('register-success');
    // Matches a success-colored utility class (bg-success-600, text-success-700,
    // etc.), not the literal substring "success" — several data-testid
    // values on this screen legitimately contain that word.
    expect(container.innerHTML).not.toMatch(/(?:bg|text|border|ring)-success-\d/);
  });

  it('shows a primary-toned, font-semibold 48-hour callout right after the email chip', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    submit.mockResolvedValue({ reference_code: 'REF1', message: 'ok', email_sent: true });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await fillMinimalRequiredFields(user);
    await user.click(screen.getByTestId('register-submit-button'));

    await screen.findByTestId('register-success');
    const emailChip = screen.getByTestId('register-success-email');
    const callout = screen.getByTestId('register-success-callout');
    expect(callout.className).toContain('bg-primary-50');
    expect(callout.className).toContain('font-semibold');
    expect(callout.textContent).toContain("isn't complete");
    expect(callout.textContent).toContain('48 hours');
    expect(
      emailChip.compareDocumentPosition(callout) & Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy();
  });

  it('moves the "wrong email" link up under the chip, ahead of the reference code block', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    submit.mockResolvedValueOnce({ reference_code: 'REF1', message: 'ok', email_sent: true });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await fillMinimalRequiredFields(user);
    await user.click(screen.getByTestId('register-submit-button'));
    await screen.findByTestId('register-success');

    // Unmapped in this file's i18n mock (see its top-of-file comment), so
    // the raw key renders — the point here is that the button no longer
    // uses the generic "editEmailButton" copy on this screen (increment 6's
    // pending-duplicate screen keeps that one; see its own describe block).
    expect(screen.getByText('register.wrongEmailPrompt')).toBeInTheDocument();
    expect(screen.getByText('register.fixEmailButton')).toBeInTheDocument();

    const editLink = screen.getByTestId('register-edit-email');
    const referenceBlock = screen.getByTestId('register-reference-block');
    expect(
      editLink.compareDocumentPosition(referenceBlock) & Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy();
    // >=44px tall on phone (min-h-11 = 2.75rem = 44px; only enforced below sm).
    expect(editLink.className).toContain('min-h-11');

    await user.click(editLink);
    await screen.findByTestId('register-form');
    expect(screen.queryByTestId('register-success')).not.toBeInTheDocument();
  });

  it('shows the email address it was sent to and the reference code', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    submit.mockResolvedValue({ reference_code: 'REF1', message: 'ok', email_sent: true });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await fillMinimalRequiredFields(user);
    await user.click(screen.getByTestId('register-submit-button'));

    await screen.findByTestId('register-success');
    expect(screen.getByTestId('register-success-email').textContent).toContain('guardian@example.com');
    expect(screen.getByTestId('register-reference-code').textContent?.trim()).toBe('REF1');
    // Labelled, not just a bare code — the "what's this for" line.
    expect(screen.getByText('register.referenceCodeLabel')).toBeInTheDocument();
    expect(screen.getByText('register.referenceCodeHint')).toBeInTheDocument();
    expect(screen.getByTestId('register-copy-reference')).toBeInTheDocument();
  });

  // R5 (increment 7 revision): the copy button's states — icon swap, sr-only
  // live-region announcement, and a clipboard-failure fallback that selects
  // the code's own text so the guardian's next Ctrl/Cmd+C still works.
  describe('copy reference code (R5)', () => {
    const originalClipboard = navigator.clipboard;

    afterEach(() => {
      Object.defineProperty(navigator, 'clipboard', {
        value: originalClipboard,
        configurable: true
      });
    });

    async function renderSubmitted(user: ReturnType<typeof userEvent.setup>) {
      getEvent.mockResolvedValue(ticketlessEventInfo());
      submit.mockResolvedValue({ reference_code: 'REF1', message: 'ok', email_sent: true });
      render(RegisterPage);
      await screen.findByTestId('register-form');
      await fillMinimalRequiredFields(user);
      await user.click(screen.getByTestId('register-submit-button'));
      await screen.findByTestId('register-success');
    }

    it('swaps the icon to a check, updates the label, and announces itself via the sr-only live region', async () => {
      const user = userEvent.setup();
      const writeText = vi.fn().mockResolvedValue(undefined);
      Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true });
      await renderSubmitted(user);

      const copyButton = screen.getByTestId('register-copy-reference');
      expect(copyButton.querySelector('svg path')?.getAttribute('d')).toBe(COPY_ICON_PATH);
      expect(copyButton.textContent).toContain('Copy');
      expect(copyButton.textContent).not.toContain('Copied');
      // min-w so the row doesn't shift between "Copy" and "Copied".
      expect(copyButton.className).toMatch(/min-w-\[/);

      await user.click(copyButton);

      expect(writeText).toHaveBeenCalledWith('REF1');
      await waitFor(() =>
        expect(copyButton.querySelector('svg path')?.getAttribute('d')).toBe(CHECK_CIRCLE_ICON_PATH)
      );
      expect(copyButton.textContent).toContain('Copied');
      expect(screen.getByText('Reference code copied')).toBeInTheDocument();
    });

    it('selects the reference code text when the clipboard write rejects', async () => {
      const user = userEvent.setup();
      const writeText = vi.fn().mockRejectedValue(new Error('denied'));
      Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true });
      await renderSubmitted(user);

      await user.click(screen.getByTestId('register-copy-reference'));
      await waitFor(() => expect(window.getSelection()?.toString().trim()).toBe('REF1'));
    });

    it('selects the reference code text outright when the Clipboard API is unavailable', async () => {
      const user = userEvent.setup();
      Object.defineProperty(navigator, 'clipboard', { value: undefined, configurable: true });
      await renderSubmitted(user);

      await user.click(screen.getByTestId('register-copy-reference'));
      await waitFor(() => expect(window.getSelection()?.toString().trim()).toBe('REF1'));
    });
  });

  it('shows an attendee/ticket summary with a total, so a forgotten child would stand out', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(baseEventInfo());
    submit.mockResolvedValue({ reference_code: 'REF1', message: 'ok', email_sent: true });
    render(RegisterPage);

    // Two children plus a named guardian: the adult is required now (owner
    // decision eb5d26f4). This event has no adult ticket type, so the parent
    // row renders no ticket select at all and the adult is simply ticketless.
    // Two children is enough to prove the summary lists each one with their
    // own auto-suggested ticket and sums the total correctly (100 + 150),
    // which a single-attendee case can't show — and the adult must add
    // nothing to it.
    await screen.findByTestId('register-form');
    await fillGuardian(user);
    await user.type(screen.getByTestId('register-contact-email'), 'guardian@example.com');
    await user.type(document.getElementById('child-first-name-0') as HTMLInputElement, 'Alex');
    await user.type(document.getElementById('child-last-name-0') as HTMLInputElement, 'Karlsson');
    await user.type(document.getElementById('child-birthdate-0') as HTMLInputElement, '2015-05-01');
    await user.tab();

    await user.click(screen.getByText(/Add another child/));
    await user.type(document.getElementById('child-first-name-1') as HTMLInputElement, 'Sam');
    await user.type(document.getElementById('child-last-name-1') as HTMLInputElement, 'Karlsson');
    await user.type(document.getElementById('child-birthdate-1') as HTMLInputElement, '2011-01-01');
    await user.tab();

    await user.click(screen.getByTestId('register-submit-button'));
    await screen.findByTestId('register-success');

    const summary = screen.getByTestId('register-summary');
    expect(summary.textContent).toContain('Alex');
    expect(summary.textContent).toContain('Sam');
    // Auto-suggested from each birthdate (see suggestChildTicketType).
    expect(summary.textContent).toContain('Barn (0-12 år)');
    expect(summary.textContent).toContain('Ungdom (13-17 år)');
    // The guardian-only adult is listed too, as not attending (this event
    // has only child ticket types, so the adult is guardian-only by
    // construction) rather than the "No ticket" that read as unregistered.
    expect(screen.getByTestId('register-summary-guardian-only').textContent).toContain(
      'Guardian – not attending'
    );
    expect(summary.textContent).not.toContain('No ticket');
    expect(screen.getByTestId('register-summary-total').textContent).toContain('250.00');
  });

  // R2 (increment 7 revision): the summary used to list a ticket price per
  // attendee while "Totalt" also folded in extras/accommodation — a
  // design-critique gate caught the arithmetic visibly not adding up (2 200
  // kr in rows vs 2 800 kr total). This proves the displayed pieces
  // (ticket + per-attendee extra + whole-registration extra − discount)
  // actually reconcile with the displayed total.
  function extrasReconciliationEventInfo(overrides: Partial<Record<string, unknown>> = {}) {
    return baseEventInfo({
      ticket_types: [
        {
          id: 'tt-standard',
          name: 'Standard',
          price: '200.00',
          applies_to: 'child',
          min_birthdate: null,
          max_birthdate: null,
          kind: 'event',
          requires_ticket_type_id: null,
          max_per_required: null,
          available: true
        }
      ],
      extras: [
        {
          id: 'extra-meals',
          name: 'Meals',
          price: '50.00',
          session_id: null,
          per_attendee: true,
          applies_to: 'child',
          requires_choice: false,
          required: false,
          default_selected: false,
          choices: []
        },
        {
          id: 'extra-cabin',
          name: 'Cabin',
          price: '300.00',
          session_id: null,
          per_attendee: false,
          applies_to: 'either',
          requires_choice: false,
          required: false,
          default_selected: false,
          choices: []
        }
      ],
      ...overrides
    });
  }

  it('reconciles the summary with the total once extras and a discount are involved (R2)', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(extrasReconciliationEventInfo());
    validatePromoCode.mockResolvedValue({
      valid: true,
      discount_type: 'fixed',
      discount_value: '30',
      applies_to_ticket_type_ids: [],
      unlocks_ticket_types: []
    });
    submit.mockResolvedValue({ reference_code: 'REF1', message: 'ok', email_sent: true });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await fillGuardian(user);
    await user.type(screen.getByTestId('register-contact-email'), 'guardian@example.com');
    await user.type(document.getElementById('child-first-name-0') as HTMLInputElement, 'Alex');
    await user.type(document.getElementById('child-last-name-0') as HTMLInputElement, 'Karlsson');
    await user.type(document.getElementById('child-birthdate-0') as HTMLInputElement, '2015-05-01');
    await user.tab();

    const childTicketSelect = (await screen.findByTestId('child-ticket-type-0')) as HTMLSelectElement;
    await user.selectOptions(childTicketSelect, 'tt-standard');

    await user.click(screen.getByLabelText(/Meals/));
    await user.click(screen.getByLabelText(/Cabin/));

    await user.type(screen.getByTestId('register-promo-code-input'), 'SAVE30');
    await user.click(screen.getByTestId('register-promo-code-apply'));
    await screen.findByTestId('register-promo-code-chip');

    await user.click(screen.getByTestId('register-submit-button'));
    await screen.findByTestId('register-success');

    const summary = screen.getByTestId('register-summary');
    expect(summary.textContent).toContain('Standard');
    expect(summary.textContent).toContain('Meals');

    expect(screen.getByTestId('register-summary-registration-extras').textContent).toContain('Cabin');

    const discountRow = screen.getByTestId('register-summary-discount');
    expect(discountRow.textContent).toContain('SAVE30');
    expect(discountRow.textContent).toContain('30.00');

    // Tickets (200) + per-attendee extra (50) + registration extra (300) −
    // discount (30) = 520.00 — the arithmetic the total actually reflects.
    expect(screen.getByTestId('register-summary-total').textContent).toContain('520.00');
  });

  it('resend still sends a fresh request, as a bordered ghost-styled quiet last action', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    submit.mockResolvedValue({ reference_code: 'REF1', message: 'ok', email_sent: true });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await fillMinimalRequiredFields(user);
    await user.click(screen.getByTestId('register-submit-button'));
    await screen.findByTestId('register-success');

    const resendButton = screen.getByText('register.resendButton') as HTMLButtonElement;
    expect(resendButton.className).toContain('border');

    await user.click(resendButton);
    await screen.findByTestId('register-resend-sent');
    expect(submit).toHaveBeenCalledTimes(2);
  });

  it("increment 6's pending-duplicate screen still renders instead of the success screen for its code", async () => {
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
    expect(screen.queryByTestId('register-success')).not.toBeInTheDocument();
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

// Back button from the confirmation screen (registration dev-cycle round 4,
// increment 8, 2026-09-29). Before this, a successful submit only ever
// flipped a local `submitted` boolean — it never touched the history stack,
// so the browser's own Back button skipped straight past this whole page to
// whatever was behind it (about:blank, when the registration link was
// opened in a fresh tab — confirmed live in Chrome before this fix; see the
// report). Fixed by pushing a history entry on success (see submitPayload's
// pushState call) and deriving `submitted` from $page.state, so Back always
// resolves to the form's own base entry instead. jsdom can't drive a real
// browser back-button press, so these tests exercise the two halves that
// make up the fix: pushState is called with the state a Back press needs to
// land on, and the component actually reacts when that state resolves back
// to {} (which is what a real popstate does — see pageStateHelper's own
// comment above for the stand-in this file uses).
describe('Register page — Back button from confirmation (increment 8)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    pageStateHelper.setState({});
  });

  it('pushes a history entry for the confirmation screen on a successful submit', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    submit.mockResolvedValue({ reference_code: 'REF1', message: 'ok', email_sent: true });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await fillMinimalRequiredFields(user);
    await user.click(screen.getByTestId('register-submit-button'));

    await screen.findByTestId('register-success-email');
    // '' keeps the current URL — this is a same-page view change, not a
    // route change (see submitPayload's own comment).
    expect(pushState).toHaveBeenCalledWith('', { registrationSubmitted: true });
  });

  it('returns to the still-filled form — not a blank or stale confirmation — when the pushed state resolves back to {}', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    submit.mockResolvedValue({ reference_code: 'REF1', message: 'ok', email_sent: true });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await fillMinimalRequiredFields(user);
    await user.click(screen.getByTestId('register-submit-button'));
    await screen.findByTestId('register-success-email');

    // Simulates what a real Back press resolves $page.state to (see
    // pageStateHelper's own comment) — this is the one thing a real
    // browser's popstate would do that nothing in this jsdom render
    // otherwise triggers.
    pageStateHelper.setState({});

    await screen.findByTestId('register-form');
    expect(screen.queryByTestId('register-success-email')).not.toBeInTheDocument();
    // Filled, not cleared — the same "drop back into the still-populated
    // form" behavior as the confirmation screen's own "Rätta den" link
    // (handleEditEmail), so Back and that link never disagree about what
    // the guardian sees.
    expect((document.getElementById('child-first-name-0') as HTMLInputElement).value).toBe('Alex');
    expect((screen.getByTestId('register-contact-email') as HTMLInputElement).value).toBe(
      'guardian@example.com'
    );
  });

  it('never re-submits merely from the state change a Back press causes', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    submit.mockResolvedValue({ reference_code: 'REF1', message: 'ok', email_sent: true });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await fillMinimalRequiredFields(user);
    await user.click(screen.getByTestId('register-submit-button'));
    await screen.findByTestId('register-success-email');
    expect(submit).toHaveBeenCalledTimes(1);

    pageStateHelper.setState({});
    await screen.findByTestId('register-form');
    // Forward again, as a Forward press after that Back would do.
    pageStateHelper.setState({ registrationSubmitted: true });
    await screen.findByTestId('register-success-email');

    expect(submit).toHaveBeenCalledTimes(1);
  });

  it('"Rätta den" pops the pushed entry via history.back(), same as a native Back press would resolve', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    submit.mockResolvedValue({ reference_code: 'REF1', message: 'ok', email_sent: true });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await fillMinimalRequiredFields(user);
    await user.click(screen.getByTestId('register-submit-button'));
    await screen.findByTestId('register-success-email');

    await user.click(screen.getByTestId('register-edit-email'));

    expect(window.history.back).toHaveBeenCalled();
    await screen.findByTestId('register-form');
  });
});

describe('Register page — ticket type capacity (sold out)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('disables a sold-out ticket option, keeps it in the list, and marks it', async () => {
    getEvent.mockResolvedValue(capacityEventInfo());
    render(RegisterPage);

    const select = (await screen.findByTestId('parent-ticket-type-0')) as HTMLSelectElement;
    // The trailing "no ticket, guardian only" option is not a ticket type.
    const options = Array.from(select.options).filter(
      (o) => o.value !== '' && o.value !== 'guardian-only'
    );
    // Still both ticket options present — disabled, not removed (same "don't
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
    await fillMinimalRequiredFields(user, { guardian: false });
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
    await fillMinimalRequiredFields(user, { guardian: false });
    await user.type(document.getElementById('parent-first-name-0') as HTMLInputElement, 'Kim');
    await user.type(document.getElementById('parent-phone-0') as HTMLInputElement, '070-123 45 67');

    const relationSelect = screen.getByTestId('parent-relationship-0') as HTMLSelectElement;
    await user.selectOptions(relationSelect, 'MOM');

    await user.click(screen.getByTestId('register-submit-button'));

    await waitFor(() => expect(submit).toHaveBeenCalledTimes(1));
    const payload = submit.mock.calls[0][0] as { parents: Array<{ relationship_type: string }> };
    expect(payload.parents[0].relationship_type).toBe('MOM');
  });

  it('does not ask a wholly untouched spare row for a Relation', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    submit.mockResolvedValue({ reference_code: 'REF1', message: 'ok', email_sent: true });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await fillMinimalRequiredFields(user);
    await user.click(screen.getByText(/Add parent/));
    // The second row is left entirely empty, so it is dropped and nothing
    // about it (Relation, phone) is required.
    await user.click(screen.getByTestId('register-submit-button'));

    await waitFor(() => expect(submit).toHaveBeenCalledTimes(1));
    const payload = submit.mock.calls[0][0] as { parents: unknown[] };
    expect(payload.parents).toHaveLength(1);
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

  it('R1: Förälder 1 first name is required whenever a child is present, and a blank Förälder 1 is not dropped', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    submit.mockResolvedValue({ reference_code: 'REF1', message: 'ok', email_sent: true });
    render(RegisterPage);

    await screen.findByTestId('register-form');

    // Owner decision eb5d26f4: children need a guardian, so the label
    // promises a requirement the form now enforces.
    const label = document.querySelector('label[for="parent-first-name-0"]');
    expect(label?.textContent).toContain('*');

    // Förälder 1 stays blank but a second row carries data: the blank row is
    // NOT silently dropped (that is how a registration ended up with a
    // parent at index 1 and nobody at index 0).
    await fillMinimalRequiredFields(user, { guardian: false });
    await user.click(screen.getByText(/Add parent/));
    await fillGuardian(user, 1);
    await user.click(screen.getByTestId('register-submit-button'));

    // Row 1 names a guardian, so the rule is met and the blank row 0 is
    // dropped only because it is wholly untouched.
    await waitFor(() => expect(submit).toHaveBeenCalledTimes(1));
    const payload = submit.mock.calls[0][0] as { parents: { first_name: string }[] };
    expect(payload.parents).toHaveLength(1);
    expect(payload.parents[0].first_name).toBe('Sam');
  });

  it('R1: a child with no named parent blocks submit with a line naming Förälder 1', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await fillMinimalRequiredFields(user, { guardian: false });
    await user.click(screen.getByTestId('register-submit-button'));

    expect(submit).not.toHaveBeenCalled();
    const summary = (await screen.findByText('Please fix the following before you can submit:')).parentElement as HTMLElement;
    expect(summary.textContent).toContain('Parent 1: Add an adult guardian for the children.');
    expect(screen.getByTestId('parent-first-name-problem-0')).toBeInTheDocument();
    expect(document.getElementById('parent-first-name-0')?.getAttribute('aria-invalid')).toBe('true');

    // Typing a name clears the problem.
    await user.type(document.getElementById('parent-first-name-0') as HTMLInputElement, 'Sam');
    expect(screen.queryByTestId('parent-first-name-problem-0')).not.toBeInTheDocument();
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
    await fillGuardian(user);
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

// Owner decision eb5d26f4 (2026-09-29): a guardian is required when the
// registration includes a child; an adult with no ticket still counts.
// The adult health question has no mapping in the i18n mock above, so it
// renders as its raw key — which is exactly what these tests look for.
const ADULT_HEALTH_QUESTION = 'register.adultHealthInfoQuestion';

describe('Register page — guardian-only adult', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  function requiredExtrasFamilyEvent() {
    return familyEventInfo({
      extras: [
        {
          id: 'extra-cabin',
          name: 'Boende',
          price: '500.00',
          session_id: null,
          per_attendee: true,
          applies_to: 'either',
          requires_choice: false,
          required: true,
          default_selected: false,
          choices: []
        },
        {
          id: 'extra-meals',
          name: 'Måltider hela helgen',
          price: '300.00',
          session_id: null,
          per_attendee: true,
          applies_to: 'either',
          requires_choice: false,
          required: false,
          default_selected: false,
          choices: []
        }
      ]
    });
  }

  async function fillChild(user: ReturnType<typeof userEvent.setup>) {
    await user.type(screen.getByTestId('register-contact-email'), 'guardian@example.com');
    await user.type(document.getElementById('child-first-name-0') as HTMLInputElement, 'Alex');
    await user.type(document.getElementById('child-last-name-0') as HTMLInputElement, 'Karlsson');
    await user.type(document.getElementById('child-birthdate-0') as HTMLInputElement, '2015-05-01');
    await user.tab();
    await user.selectOptions(await screen.findByTestId('child-ticket-type-0'), 'tt-solo');
  }

  it('offers "no ticket, guardian only" as an option of the parent ticket select', async () => {
    getEvent.mockResolvedValue(requiredExtrasFamilyEvent());
    render(RegisterPage);
    const select = (await screen.findByTestId('parent-ticket-type-0')) as HTMLSelectElement;
    expect(Array.from(select.options).map((o) => o.value)).toContain('guardian-only');
  });

  it('sends ticket_type null and no extras for a guardian-only row, even with a required extra, and prices it at 0', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(requiredExtrasFamilyEvent());
    submit.mockResolvedValue({ reference_code: 'REF1', message: 'ok', email_sent: true });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await fillGuardian(user);
    await user.selectOptions(screen.getByTestId('parent-ticket-type-0'), 'guardian-only');
    await fillChild(user);

    // Child: Solo 300 + required Boende 500. The adult adds nothing.
    const total = await screen.findByTestId('register-running-total');
    expect(total.textContent).toContain('800.00');

    await user.click(screen.getByTestId('register-submit-button'));
    await waitFor(() => expect(submit).toHaveBeenCalledTimes(1));
    const payload = submit.mock.calls[0][0] as {
      parents: {
        ticket_type: string | null;
        extras: unknown[];
        guardian_only?: boolean;
        health_consent_status?: string;
      }[];
      children: { ticket_type: string | null; extras: unknown[]; guardian_only?: boolean }[];
    };
    expect(payload.parents).toHaveLength(1);
    expect(payload.parents[0].ticket_type).toBeNull();
    expect(payload.parents[0].guardian_only).toBe(true);
    expect(payload.parents[0].health_consent_status).toBe('not_applicable');
    expect(payload.parents[0].extras).toEqual([]);
    // Only guardian-only adults say so; a child never does.
    expect(payload.children[0].guardian_only).toBeUndefined();
    // Children must still send a ticket type (and their own extras).
    expect(payload.children[0].ticket_type).toBe('tt-solo');
    expect(payload.children[0].extras.length).toBeGreaterThan(0);
  });

  it('hides the extras choices on a guardian-only row and brings them back when a ticket is chosen', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(requiredExtrasFamilyEvent());
    render(RegisterPage);

    await screen.findByTestId('register-form');
    const before = screen.getAllByRole('checkbox', { name: /Måltider hela helgen/ }).length;
    await user.selectOptions(screen.getByTestId('parent-ticket-type-0'), 'guardian-only');
    expect(screen.getAllByRole('checkbox', { name: /Måltider hela helgen/ }).length).toBe(before - 1);

    await user.selectOptions(screen.getByTestId('parent-ticket-type-0'), 'tt-solo');
    expect(screen.getAllByRole('checkbox', { name: /Måltider hela helgen/ }).length).toBe(before);
  });

  it('still needs a phone number on a guardian-only row', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(requiredExtrasFamilyEvent());
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await user.type(document.getElementById('parent-first-name-0') as HTMLInputElement, 'Sam');
    await user.selectOptions(screen.getByTestId('parent-relationship-0'), 'GUARDIAN');
    await user.selectOptions(screen.getByTestId('parent-ticket-type-0'), 'guardian-only');
    await fillChild(user);
    await user.click(screen.getByTestId('register-submit-button'));

    expect(submit).not.toHaveBeenCalled();
    // Once in the summary, once under the field itself (a red border with
    // no words was seen on the phone box).
    expect(await screen.findByTestId('register-error-item-parent-phone-0')).toHaveTextContent(
      /Enter a phone number for/
    );
    expect(screen.getByTestId('parent-phone-problem-0')).toHaveTextContent(/Enter a phone number for/);
  });

  it('a guardian-only row alone satisfies the guardian rule (no ticket required for the adult)', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(requiredExtrasFamilyEvent());
    submit.mockResolvedValue({ reference_code: 'REF1', message: 'ok', email_sent: true });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await fillGuardian(user);
    await user.selectOptions(screen.getByTestId('parent-ticket-type-0'), 'guardian-only');
    await fillChild(user);
    await user.click(screen.getByTestId('register-submit-button'));
    await waitFor(() => expect(submit).toHaveBeenCalledTimes(1));
  });

  it('a ticketed adult is still required to choose a ticket type', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(requiredExtrasFamilyEvent());
    render(RegisterPage);

    await screen.findByTestId('register-form');
    await fillGuardian(user);
    await fillChild(user);
    await user.click(screen.getByTestId('register-submit-button'));
    expect(submit).not.toHaveBeenCalled();
    expect(await screen.findByText(/Choose a ticket type for/)).toBeInTheDocument();
  });

  it('lets a guardian register on an event whose ticket types are all child-only, sending no ticket and no extras for them', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(
      baseEventInfo({
        extras: [
          {
            id: 'extra-cabin',
            name: 'Boende',
            price: '500.00',
            session_id: null,
            per_attendee: true,
            applies_to: 'either',
            requires_choice: false,
            required: true,
            default_selected: false,
            choices: []
          }
        ]
      })
    );
    submit.mockResolvedValue({ reference_code: 'REF1', message: 'ok', email_sent: true });
    render(RegisterPage);

    await screen.findByTestId('register-form');
    // No adult ticket type exists, so there is no select — and no option
    // to pick — but naming the guardian must not dead-end on "Choose a
    // ticket type" (found in review of the guardian rule).
    expect(screen.queryByTestId('parent-ticket-type-0')).not.toBeInTheDocument();
    await fillGuardian(user);
    await user.type(screen.getByTestId('register-contact-email'), 'guardian@example.com');
    await user.type(document.getElementById('child-first-name-0') as HTMLInputElement, 'Alex');
    await user.type(document.getElementById('child-last-name-0') as HTMLInputElement, 'Karlsson');
    await user.type(document.getElementById('child-birthdate-0') as HTMLInputElement, '2015-05-01');
    await user.tab();
    await user.click(screen.getByTestId('register-submit-button'));

    await waitFor(() => expect(submit).toHaveBeenCalledTimes(1));
    const payload = submit.mock.calls[0][0] as {
      parents: {
        ticket_type: string | null;
        extras: unknown[];
        guardian_only?: boolean;
        health_consent_status?: string;
      }[];
    };
    expect(payload.parents[0].ticket_type).toBeNull();
    // Child-only ticket types: the adult is guardian-only by construction,
    // and says so like every other guardian-only row.
    expect(payload.parents[0].guardian_only).toBe(true);
    expect(payload.parents[0].health_consent_status).toBe('not_applicable');
    expect(payload.parents[0].extras).toEqual([]);
  });

  it('asks no health question of the adult on a child-only-ticket-types event, and explains why', async () => {
    getEvent.mockResolvedValue(baseEventInfo());
    render(RegisterPage);
    await screen.findByTestId('register-form');
    expect(screen.queryByText(ADULT_HEALTH_QUESTION)).not.toBeInTheDocument();
    expect(screen.getByTestId('parent-guardian-only-hint-0')).toBeInTheDocument();
    // No checkbox either: there is nothing to choose.
    expect(screen.queryByTestId('parent-guardian-only-0')).not.toBeInTheDocument();
  });

  describe('flat-price event (no ticket types)', () => {

    it('offers a "guardian only" checkbox on the adult card instead of a ticket select', async () => {
      getEvent.mockResolvedValue(ticketlessEventInfo());
      render(RegisterPage);
      await screen.findByTestId('register-form');
      expect(screen.queryByTestId('parent-ticket-type-0')).not.toBeInTheDocument();
      const box = screen.getByRole('checkbox', {
        name: 'Guardian only – I am not attending myself'
      }) as HTMLInputElement;
      expect(box.checked).toBe(false);
    });

    it('shows the health question for an attending adult and hides it once guardian-only is ticked', async () => {
      const user = userEvent.setup();
      getEvent.mockResolvedValue(ticketlessEventInfo());
      render(RegisterPage);
      await screen.findByTestId('register-form');
      expect(screen.getByText(ADULT_HEALTH_QUESTION)).toBeInTheDocument();
      expect(screen.queryByTestId('parent-guardian-only-hint-0')).not.toBeInTheDocument();

      await user.click(screen.getByTestId('parent-guardian-only-0'));
      expect(screen.queryByText(ADULT_HEALTH_QUESTION)).not.toBeInTheDocument();
      expect(screen.getByTestId('parent-guardian-only-hint-0')).toBeInTheDocument();

      await user.click(screen.getByTestId('parent-guardian-only-0'));
      expect(screen.getByText(ADULT_HEALTH_QUESTION)).toBeInTheDocument();
    });

    it('sends guardian_only true, ticket_type null, no extras and no health data', async () => {
      const user = userEvent.setup();
      getEvent.mockResolvedValue(ticketlessEventInfo());
      submit.mockResolvedValue({ reference_code: 'REF1', message: 'ok', email_sent: true });
      render(RegisterPage);
      await screen.findByTestId('register-form');
      await fillMinimalRequiredFields(user);
      await user.click(screen.getByTestId('parent-guardian-only-0'));
      await user.click(screen.getByTestId('register-submit-button'));
      await waitFor(() => expect(submit).toHaveBeenCalledTimes(1));
      const payload = submit.mock.calls[0][0] as {
        parents: Record<string, unknown>[];
      };
      expect(payload.parents[0]).toMatchObject({
        guardian_only: true,
        ticket_type: null,
        extras: [],
        health_consent_status: 'not_applicable',
        allergies: '',
        notes: ''
      });
    });

    it('sends no guardian_only flag for an attending adult', async () => {
      const user = userEvent.setup();
      getEvent.mockResolvedValue(ticketlessEventInfo());
      submit.mockResolvedValue({ reference_code: 'REF1', message: 'ok', email_sent: true });
      render(RegisterPage);
      await screen.findByTestId('register-form');
      await fillMinimalRequiredFields(user);
      await user.click(screen.getByTestId('register-submit-button'));
      await waitFor(() => expect(submit).toHaveBeenCalledTimes(1));
      const payload = submit.mock.calls[0][0] as { parents: Record<string, unknown>[] };
      expect(payload.parents[0].guardian_only).toBeUndefined();
    });

    it('still needs name, relation and phone on a guardian-only row', async () => {
      const user = userEvent.setup();
      getEvent.mockResolvedValue(ticketlessEventInfo());
      render(RegisterPage);
      await screen.findByTestId('register-form');
      await user.type(screen.getByTestId('register-contact-email'), 'guardian@example.com');
      await user.type(document.getElementById('child-first-name-0') as HTMLInputElement, 'Alex');
      await user.type(document.getElementById('child-last-name-0') as HTMLInputElement, 'Karlsson');
      await user.type(document.getElementById('child-birthdate-0') as HTMLInputElement, '2015-05-01');
      await user.tab();
      await user.type(document.getElementById('parent-first-name-0') as HTMLInputElement, 'Sam');
      await user.click(screen.getByTestId('parent-guardian-only-0'));
      await user.click(screen.getByTestId('register-submit-button'));
      expect(submit).not.toHaveBeenCalled();
      expect(await screen.findByTestId('register-error-item-parent-phone-0')).toBeInTheDocument();
    });

    it('drops health details already typed when the adult becomes guardian-only', async () => {
      const user = userEvent.setup();
      getEvent.mockResolvedValue(ticketlessEventInfo());
      submit.mockResolvedValue({ reference_code: 'REF1', message: 'ok', email_sent: true });
      render(RegisterPage);
      await screen.findByTestId('register-form');
      await fillMinimalRequiredFields(user);
      // The question's own radio group: none / consented / declined.
      await user.click(document.getElementsByName('health-info-status-parent-0')[1]);
      await user.click(screen.getByTestId('parent-consent-attest-parent-0'));
      await user.type(
        document.getElementById('parent-allergies-parent-0') as HTMLInputElement,
        'peanuts'
      );
      await user.click(screen.getByTestId('parent-guardian-only-0'));
      await user.click(screen.getByTestId('register-submit-button'));
      await waitFor(() => expect(submit).toHaveBeenCalledTimes(1));
      const payload = submit.mock.calls[0][0] as { parents: Record<string, unknown>[] };
      expect(payload.parents[0].allergies).toBe('');
      expect(payload.parents[0].health_consent_status).toBe('not_applicable');
    });
  });
});

describe('Register page — guardian-only on an itemized event', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('hides the health question when the select says "guardian only", and brings it back for a ticket', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(familyEventInfo());
    render(RegisterPage);
    await screen.findByTestId('register-form');
    expect(screen.getByText(ADULT_HEALTH_QUESTION)).toBeInTheDocument();
    // The select option is the control here; there is no checkbox.
    expect(screen.queryByTestId('parent-guardian-only-0')).not.toBeInTheDocument();
    await user.selectOptions(screen.getByTestId('parent-ticket-type-0'), 'guardian-only');
    expect(screen.queryByText(ADULT_HEALTH_QUESTION)).not.toBeInTheDocument();
    await user.selectOptions(screen.getByTestId('parent-ticket-type-0'), 'tt-solo');
    expect(screen.getByText(ADULT_HEALTH_QUESTION)).toBeInTheDocument();
  });
});

describe('Register page — server errors about parents (guardian rule)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  async function submitAndReject(details: unknown) {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    submit.mockRejectedValueOnce({ status: 400, message: 'Bad Request', details });
    render(RegisterPage);
    await screen.findByTestId('register-form');
    await fillMinimalRequiredFields(user);
    await user.click(screen.getByTestId('register-submit-button'));
    await waitFor(() => expect(submit).toHaveBeenCalledTimes(1));
    await screen.findByText('Please fix the following before you can submit:');
    return user;
  }

  it('shape (a) {"parents": ["msg"]} lands on Förälder 1 in the summary, in the local language', async () => {
    const user = await submitAndReject({ parents: ['Children need an adult guardian.'] });
    const line = await screen.findByText('Parent 1: Add an adult guardian for the children.');
    expect(screen.queryByText('Children need an adult guardian.')).not.toBeInTheDocument();
    await user.click(line);
    expect(document.activeElement).toBe(document.getElementById('parent-first-name-0'));
  });

  it('shape (b) {"parents": [{"phone": [...]}]} lands on that row\'s phone', async () => {
    const user = await submitAndReject({ parents: [{ phone: ['This field may not be blank.'] }] });
    const line = await screen.findByTestId('register-error-item-parent-phone-0');
    expect(screen.queryByText('This field may not be blank.')).not.toBeInTheDocument();
    expect(screen.getByTestId('parent-phone-problem-0')).toHaveTextContent(/Enter a phone number for/);
    await user.click(line);
    expect(document.activeElement).toBe(document.getElementById('parent-phone-0'));
  });

  it('shape (b) {"parents": [{"health_consent_status": [...]}]} names the guardian-only row, in the local language', async () => {
    await submitAndReject({
      parents: [{ health_consent_status: ['Health data is not allowed for a guardian only.'] }]
    });
    expect(await screen.findByTestId('register-error-item-parent-guardian-only-0')).toHaveTextContent(
      /a guardian who is not attending cannot have health details/
    );
    expect(screen.queryByText(/Health data is not allowed/)).not.toBeInTheDocument();
  });

  it('a bare ["needs someone attending"] body becomes the local line when only guardian-only adults were sent', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    submit.mockRejectedValueOnce({
      status: 400,
      message: 'Bad Request',
      details: ['At least one person on the registration needs to be attending.']
    });
    render(RegisterPage);
    await screen.findByTestId('register-form');
    await fillMinimalRequiredFields(user);
    await user.click(screen.getByTestId('parent-guardian-only-0'));
    await user.click(screen.getByTestId('register-submit-button'));
    await waitFor(() => expect(submit).toHaveBeenCalledTimes(1));
    // The server's verdict arrives in the local language, as a summary line.
    expect(await screen.findByTestId('register-error-item-at-least-one-attending')).toHaveTextContent(
      'At least one person on the registration needs to be attending.'
    );
    expect(screen.getByText('Please fix the following before you can submit:')).toBeInTheDocument();
  });

  it('shape (d) {"parents": {"0": ["msg"]}} names the row with the server text', async () => {
    await submitAndReject({
      parents: { '0': ['Extras can only be added for an adult with a ticket.'] }
    });
    expect(
      await screen.findByText(/Extras can only be added for an adult with a ticket\./)
    ).toBeInTheDocument();
  });
});

// Revision round (2026-09-29): card titles, headings, DOM-ordered summary,
// and the guardian line only when no adult row has been touched.
describe('Register page — person cards and summary order', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  function bannerLines(): string[] {
    const banner = screen.getByTestId('register-error-banner');
    return Array.from(banner.querySelectorAll('[data-testid^="register-error-item-"]')).map(
      (el) => el.textContent?.trim() ?? ''
    );
  }

  it('titles every adult and child card with a heading that names its group', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    render(RegisterPage);
    await screen.findByTestId('register-form');
    await user.click(screen.getByText(/Add parent/));

    const adult = screen.getByTestId('parent-heading-1');
    expect(adult.tagName).toBe('H3');
    expect(adult).toHaveTextContent('Parent 2');
    expect(screen.getByRole('group', { name: 'Parent 2' })).toBeInTheDocument();
    expect(screen.getByRole('group', { name: 'Parent 1' })).toBeInTheDocument();

    const child = screen.getByTestId('child-heading-0');
    expect(child.tagName).toBe('H3');
    expect(screen.getByRole('group', { name: 'Child 1' })).toBeInTheDocument();
  });

  it('puts "Remove" in the title row, with the heading, not at the bottom of the card', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    render(RegisterPage);
    await screen.findByTestId('register-form');
    await user.click(screen.getByText(/Add parent/));

    const heading = screen.getByTestId('parent-heading-1');
    const removeButton = screen.getAllByText('Remove parent')[1] as HTMLElement;
    expect(removeButton.parentElement).toBe(heading.parentElement);
    expect(removeButton.querySelector('svg')).not.toBeNull();
    // It is described by its own card's title, so identical buttons differ.
    expect(removeButton.getAttribute('aria-describedby')).toBe('parent-heading-1');
  });

  it('(a) shows the guardian line only when no adult row has been touched', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    render(RegisterPage);
    await screen.findByTestId('register-form');
    await fillMinimalRequiredFields(user, { guardian: false });
    await user.click(screen.getByTestId('register-submit-button'));

    expect(submit).not.toHaveBeenCalled();
    expect(await screen.findByTestId('register-error-item-guardian-required')).toHaveTextContent(
      'Parent 1: Add an adult guardian for the children.'
    );
  });

  it('(b) does not show it when a second adult is touched but has no first name', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    render(RegisterPage);
    await screen.findByTestId('register-form');
    await fillMinimalRequiredFields(user, { guardian: false });
    await user.click(screen.getByText(/Add parent/));
    await user.type(document.getElementById('parent-phone-1') as HTMLInputElement, '070-123 45 67');
    await user.click(screen.getByTestId('register-submit-button'));

    expect(submit).not.toHaveBeenCalled();
    await screen.findByTestId('register-error-banner');
    expect(screen.queryByTestId('register-error-item-guardian-required')).not.toBeInTheDocument();
    expect(screen.getByTestId('register-error-item-parent-first-name-1')).toHaveTextContent(
      'register.parentNameRequired'
    );
  });

  it('(c) lists lines in page order, with the guardian line first among the adults', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(
      baseEventInfo({
        extras: [
          {
            id: 'extra-cabin',
            name: 'Boende',
            price: '500.00',
            session_id: null,
            per_attendee: false,
            applies_to: 'either',
            requires_choice: true,
            required: true,
            default_selected: false,
            choices: [{ id: 'c1', label: 'Stuga', price_delta: '0.00' }]
          }
        ]
      })
    );
    render(RegisterPage);
    await screen.findByTestId('register-form');
    // Email left blank; no adult named; the child is incomplete; the
    // whole-registration extra needs a choice. The child ticket select is
    // reached first in the code's own check order (children before adults),
    // so this proves the summary is re-sorted, not merely built in order.
    await user.type(document.getElementById('child-first-name-0') as HTMLInputElement, 'Alex');
    await user.click(screen.getByTestId('register-submit-button'));

    expect(submit).not.toHaveBeenCalled();
    await screen.findByTestId('register-error-banner');
    const ids = Array.from(
      screen
        .getByTestId('register-error-banner')
        .querySelectorAll('[data-testid^="register-error-item-"]')
    ).map((el) => (el.getAttribute('data-testid') ?? '').replace('register-error-item-', ''));
    expect(ids[0]).toBe('contact-email');
    expect(ids[1]).toBe('guardian-required');
    expect(ids.indexOf('child-info-0')).toBeGreaterThan(1);
    expect(ids[ids.length - 1]).toMatch(/^registration-extra-/);
    expect(bannerLines()[1]).toBe('Parent 1: Add an adult guardian for the children.');
  });
});

// Guardian-only increment 2: the confirmation summary on a flat-price event.
// Found live: every row, attending children included, read "No ticket" and
// "Total: 0.00" while the backend charged the flat price, so a parent could
// not tell whether her children were registered. The backend charges
// event.price once per registration (pricing.calculate_total) and applies a
// discount to that same base (calculate_discount); ticket types, extras and
// headcount play no part in flat mode.
describe('Register page — summary on a flat-price event', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  function flatEvent(overrides: Partial<Record<string, unknown>> = {}) {
    return ticketlessEventInfo({ is_paid: true, price: '150.00', ...overrides });
  }

  async function submitFlat(
    user: ReturnType<typeof userEvent.setup>,
    { extraChildren = 0, guardianOnly = false, promo = null }: {
      extraChildren?: number;
      guardianOnly?: boolean;
      promo?: Record<string, unknown> | null;
    } = {}
  ) {
    submit.mockResolvedValue({ reference_code: 'REF1', message: 'ok', email_sent: true });
    render(RegisterPage);
    await screen.findByTestId('register-form');
    await fillMinimalRequiredFields(user);
    for (let i = 1; i <= extraChildren; i++) {
      await user.click(screen.getByText(/Add another child/));
      await user.type(document.getElementById(`child-first-name-${i}`) as HTMLInputElement, `Kid${i}`);
      await user.type(document.getElementById(`child-last-name-${i}`) as HTMLInputElement, 'Karlsson');
      await user.type(document.getElementById(`child-birthdate-${i}`) as HTMLInputElement, '2014-03-03');
      await user.tab();
    }
    if (guardianOnly) await user.click(screen.getByTestId('parent-guardian-only-0'));
    if (promo) {
      validatePromoCode.mockResolvedValue({
        valid: true,
        applies_to_ticket_type_ids: [],
        unlocks_ticket_types: [],
        ...promo
      });
      await user.type(screen.getByTestId('register-promo-code-input'), 'CODE');
      await user.click(screen.getByTestId('register-promo-code-apply'));
      await screen.findByTestId('register-promo-code-chip');
    }
    await user.click(screen.getByTestId('register-submit-button'));
    await screen.findByTestId('register-success');
    return screen.getByTestId('register-summary');
  }

  it('labels attending people "Attending" and a guardian-only adult "Guardian – not attending", in muted text', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(flatEvent());
    const summary = await submitFlat(user, { guardianOnly: true });

    // Parent row (guardian-only) and the child row (attending).
    const guardian = screen.getByTestId('register-summary-guardian-only');
    expect(guardian.textContent?.trim()).toBe('Guardian – not attending');
    expect(guardian.className).toContain('text-neutral-500');
    expect(summary.textContent).toContain('Attending');
    expect(summary.textContent).not.toContain('No ticket');
  });

  it('labels an attending adult and the child both "Attending"', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(flatEvent());
    const summary = await submitFlat(user);
    expect(summary.textContent?.match(/Attending/g)).toHaveLength(2);
    expect(screen.queryByTestId('register-summary-guardian-only')).not.toBeInTheDocument();
    expect(summary.textContent).not.toContain('No ticket');
  });

  it('totals the flat price once for two attendees, and says it is for the whole registration', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(flatEvent());
    await submitFlat(user);
    expect(screen.getByTestId('register-summary-total').textContent).toContain('150.00');
    const priceLine = screen.getByTestId('register-summary-flat-price');
    expect(priceLine.textContent).toContain('Price for the whole registration');
    expect(priceLine.textContent).toContain('150.00 SEK');
    expect(screen.queryByTestId('register-summary-discount')).not.toBeInTheDocument();
  });

  it('does not multiply the flat price by headcount (three attendees, still one price)', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(flatEvent());
    await submitFlat(user, { extraChildren: 1 });
    expect(screen.getByTestId('register-summary-total').textContent).toContain('150.00');
    expect(screen.getByTestId('register-summary-total').textContent).not.toContain('450');
  });

  it('applies a percent code to the flat price', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(flatEvent());
    await submitFlat(user, { promo: { discount_type: 'percent', discount_value: '20' } });
    expect(screen.getByTestId('register-summary-discount').textContent).toContain('30.00');
    expect(screen.getByTestId('register-summary-total').textContent).toContain('120.00');
  });

  it('applies a fixed code to the flat price', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(flatEvent());
    await submitFlat(user, { promo: { discount_type: 'fixed', discount_value: '40' } });
    expect(screen.getByTestId('register-summary-discount').textContent).toContain('40.00');
    expect(screen.getByTestId('register-summary-total').textContent).toContain('110.00');
  });

  it('caps a fixed code larger than the price at the price (total 0, never negative)', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(flatEvent());
    await submitFlat(user, { promo: { discount_type: 'fixed', discount_value: '500' } });
    expect(screen.getByTestId('register-summary-discount').textContent).toContain('150.00');
    expect(screen.getByTestId('register-summary-total').textContent).toContain('0.00');
    expect(screen.getByTestId('register-summary-total').textContent).not.toContain('-');
  });

  it('a code scoped to ticket types discounts nothing on a flat event', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(flatEvent());
    await submitFlat(user, {
      promo: {
        discount_type: 'percent',
        discount_value: '50',
        applies_to_ticket_type_ids: ['tt-elsewhere']
      }
    });
    expect(screen.queryByTestId('register-summary-discount')).not.toBeInTheDocument();
    expect(screen.getByTestId('register-summary-total').textContent).toContain('150.00');
  });

  it('shows no total and no price line on a free flat event, still labelling rows "Attending"', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(flatEvent({ is_paid: false, price: null }));
    const summary = await submitFlat(user);
    expect(screen.queryByTestId('register-summary-total')).not.toBeInTheDocument();
    expect(screen.queryByTestId('register-summary-flat-price')).not.toBeInTheDocument();
    expect(summary.textContent).toContain('Attending');
  });

  it('decides by the price, not is_paid: a zero price shows no total even when is_paid is set', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(flatEvent({ is_paid: true, price: '0.00' }));
    await submitFlat(user);
    expect(screen.queryByTestId('register-summary-total')).not.toBeInTheDocument();
    expect(screen.queryByTestId('register-summary-flat-price')).not.toBeInTheDocument();
  });

  it('ignores extras in the flat total (the backend does too)', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(
      flatEvent({
        extras: [
          {
            id: 'extra-cabin',
            name: 'Cabin',
            price: '300.00',
            session_id: null,
            per_attendee: false,
            applies_to: 'either',
            requires_choice: false,
            required: false,
            default_selected: true,
            choices: []
          }
        ]
      })
    );
    await submitFlat(user);
    expect(screen.getByTestId('register-summary-total').textContent).toContain('150.00');
  });

  it('a hidden-ticket-types event with none visible stays on the itemized path (no flat price, "No ticket" for an attendee)', async () => {
    const user = userEvent.setup();
    // The backend itemizes as soon as any active type exists, hidden or not,
    // so event.price is never charged here: do not state it as the total.
    getEvent.mockResolvedValue(flatEvent({ has_hidden_ticket_types: true }));
    const summary = await submitFlat(user);
    expect(screen.queryByTestId('register-summary-flat-price')).not.toBeInTheDocument();
    expect(screen.getByTestId('register-summary-total').textContent).toContain('0.00');
    expect(screen.getByTestId('register-summary-total').textContent).not.toContain('150');
    expect(summary.textContent).toContain('No ticket');
    expect(summary.textContent).not.toContain('Attending');
  });
});

describe('Register page — summary rows on an itemized event', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows the ticket name for a ticketed attendee and "Guardian – not attending" for a guardian-only adult', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(familyEventInfo());
    submit.mockResolvedValue({ reference_code: 'REF1', message: 'ok', email_sent: true });
    render(RegisterPage);
    await screen.findByTestId('register-form');
    await fillGuardian(user);
    await user.type(screen.getByTestId('register-contact-email'), 'guardian@example.com');
    await user.type(document.getElementById('child-first-name-0') as HTMLInputElement, 'Alex');
    await user.type(document.getElementById('child-last-name-0') as HTMLInputElement, 'Karlsson');
    await user.type(document.getElementById('child-birthdate-0') as HTMLInputElement, '2015-05-01');
    await user.tab();
    await user.selectOptions(await screen.findByTestId('child-ticket-type-0'), 'tt-solo');
    await user.selectOptions(screen.getByTestId('parent-ticket-type-0'), 'guardian-only');
    await user.click(screen.getByTestId('register-submit-button'));
    await screen.findByTestId('register-success');

    const summary = screen.getByTestId('register-summary');
    expect(screen.getByTestId('register-summary-guardian-only').textContent?.trim()).toBe(
      'Guardian – not attending'
    );
    expect(summary.textContent).toContain('Solo');
    // "Attending" is the flat-event label only; an itemized row names its ticket.
    expect(summary.textContent).not.toContain('Attending');
    expect(summary.textContent).not.toContain('No ticket');
    // Itemized totals are unchanged: the child's ticket only, no flat price line.
    expect(screen.getByTestId('register-summary-total').textContent).toContain('300.00');
    expect(screen.queryByTestId('register-summary-flat-price')).not.toBeInTheDocument();
  });
});

describe('Register page — guardian-only hint wording per site', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // The flat checkbox hint drops the "costs nothing / no extras" claims that
  // are only true on an itemized event; the other two sites keep the old key.
  it('uses the flat-only key at the flat-price checkbox', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(ticketlessEventInfo());
    render(RegisterPage);
    await screen.findByTestId('register-form');
    await user.click(screen.getByTestId('parent-guardian-only-0'));
    expect(screen.getByTestId('parent-guardian-only-hint-0').textContent?.trim()).toBe(
      'register.guardianOnlyHintFlat'
    );
  });

  it('keeps the original key at the itemized select hint', async () => {
    const user = userEvent.setup();
    getEvent.mockResolvedValue(familyEventInfo());
    render(RegisterPage);
    await screen.findByTestId('register-form');
    await user.selectOptions(screen.getByTestId('parent-ticket-type-0'), 'guardian-only');
    expect(screen.getByTestId('parent-guardian-only-hint-0').textContent?.trim()).toBe(
      'register.guardianOnlyHint'
    );
  });

  it('keeps the original key at the child-only-types hint', async () => {
    getEvent.mockResolvedValue(baseEventInfo());
    render(RegisterPage);
    await screen.findByTestId('register-form');
    expect(screen.getByTestId('parent-guardian-only-hint-0').textContent?.trim()).toBe(
      'register.guardianOnlyHint'
    );
  });
});

describe('Register page — event instants are shown in Swedish time', () => {
  // Europe/Stockholm leaves summer time on 2026-10-25 (UTC+2 -> UTC+1), so
  // the same wall-clock close, 23:59, is a different UTC instant on either
  // side of that date. Each row is [instant, expected rendering in Sweden].
  const instants: Array<[string, RegExp]> = [
    ['2026-10-24T21:59:00Z', /24 October 2026.*23:59/], // still CEST
    ['2026-10-25T22:59:00Z', /25 October 2026.*23:59/], // CET
    ['2026-10-31T21:59:00Z', /31 October 2026.*22:59/]
  ];
  // The formatter must not depend on the zone of the browser/process: a
  // Swede abroad, or a guardian in another country, sees the event's time.
  const processZones = ['UTC', 'Pacific/Auckland', 'America/Los_Angeles', 'Europe/Stockholm'];
  let originalTZ: string | undefined;

  beforeEach(() => {
    vi.clearAllMocks();
    originalTZ = process.env.TZ;
  });

  afterEach(() => {
    if (originalTZ === undefined) delete process.env.TZ;
    else process.env.TZ = originalTZ;
  });

  for (const zone of processZones) {
    for (const [iso, expected] of instants) {
      it(`shows ${iso} as Stockholm time when the process zone is ${zone}`, async () => {
        process.env.TZ = zone;
        getEvent.mockResolvedValue(
          baseEventInfo({
            registration_window_status: 'closed',
            registration_closes_at: iso
          })
        );
        render(RegisterPage);
        const closed = await screen.findByTestId('register-closed');
        expect(closed.textContent).toMatch(expected);
      });
    }
  }
});
