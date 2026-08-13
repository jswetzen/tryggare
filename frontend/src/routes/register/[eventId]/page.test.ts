import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { readable } from 'svelte/store';
import RegisterPage from './+page.svelte';

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
    'checkin.childFirstName': 'First name',
    'checkin.childLastName': 'Last name',
    'checkin.childBirthdate': 'Birthdate',
    'checkin.children': 'Children',
    'checkin.addAnotherChild': 'Add another child',
    'checkin.parentInfo': 'Parent info',
    'checkin.addParent': 'Add parent',
    'checkin.familyName': 'Family name',
    'register.contactEmail': 'Contact email',
    'register.introText': '',
    'register.heading': 'Register for {event}',
    'register.privacyNotice': '',
    'register.privacyLink': 'Privacy notice',
    'register.submitButton': 'Submit registration'
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

vi.mock('$lib/api/registrationService', () => ({
  registrationApi: {
    getEvent: (...args: unknown[]) => getEvent(...args),
    submit: vi.fn(),
    validatePromoCode: vi.fn()
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
        max_per_required: null
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
        max_per_required: null
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
