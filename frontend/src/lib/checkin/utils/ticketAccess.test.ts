import { describe, it, expect } from 'vitest';
import type { Session, TicketRule } from '$lib/checkin/types';
import {
  childTicketAccess,
  parentTicketAccess,
  effectiveTicketType,
  effectiveParentTicketType,
  ticketRuleOf,
  adultsNotCheckedIn,
} from './mergeFamilies';

/**
 * The check-in screen must decide exactly what the server decides
 * (backend checkins/eligibility.py, matrix verified in
 * backend/tests/unit/test_ticket_rule.py). `ticket === 'none'` is the red
 * "No ticket" state, i.e. the server would refuse.
 */

const EVENT = 'event-1';
const SESSION = 'session-1';

const session = (rule: TicketRule, adultsNotHere = false): Session => ({
  id: SESSION,
  event: EVENT,
  name: 'Morning',
  start_time: '09:00',
  is_active: true,
  event_name: 'Conference',
  effective_ticket_rule: rule,
  adults_not_checked_in: adultsNotHere,
});

const eventTicket = (event = EVENT) => ({
  event_tickets: [{ id: 'et', event, event_name: 'E' }],
  session_tickets: [],
});
const sessionTicket = (sess = SESSION) => ({
  event_tickets: [],
  session_tickets: [{ id: 'st', session: sess, session_name: 'S' }],
});

const ticketedChild = { ticket_type: 'event', ticket_details: eventTicket() };
const ticketlessChild = { ticket_type: 'none', ticket_details: null };
const ticketedAdult = { ticket_type: 'event', ticket_details: eventTicket() };
const ticketlessAdult = { ticket_type: null, ticket_details: null };
const confirmedGuardian = {
  ticket_type: null,
  ticket_details: null,
  guardian_only_event_ids: [EVENT],
};

const allowed = (ticket: string) => ticket !== 'none';

describe('ticket matrix, adults_not_checked_in off', () => {
  // [person, open, children, all] -> would the server let them in?
  const cases: [string, 'child' | 'adult', object, boolean, boolean, boolean][] = [
    ['child with ticket', 'child', ticketedChild, true, true, true],
    ['child without ticket', 'child', ticketlessChild, true, false, false],
    ['ticketed adult', 'adult', ticketedAdult, true, true, true],
    ['ticketless non-guardian adult', 'adult', ticketlessAdult, true, true, false],
    ['confirmed guardian-only adult', 'adult', confirmedGuardian, true, true, true],
  ];

  for (const [label, kind, person, open, children, all] of cases) {
    for (const [rule, expected] of [
      ['open', open],
      ['children', children],
      ['all', all],
    ] as [TicketRule, boolean][]) {
      it(`${label} on '${rule}': ${expected ? 'allowed' : 'blocked'}`, () => {
        const s = session(rule);
        const access =
          kind === 'child' ? childTicketAccess(person, s) : parentTicketAccess(person, s);
        expect(allowed(access.ticket)).toBe(expected);
      });
    }
  }
});

describe('ticket matrix, adults_not_checked_in on', () => {
  for (const rule of ['open', 'children', 'all'] as TicketRule[]) {
    for (const [label, adult] of [
      ['ticketed adult', ticketedAdult],
      ['ticketless adult', ticketlessAdult],
      ['confirmed guardian-only adult', confirmedGuardian],
    ] as [string, object][]) {
      it(`${label} on '${rule}' is blocked, and flagged as not checked in here (not as missing a ticket)`, () => {
        const access = parentTicketAccess(adult, session(rule, true));
        expect(access.ticket).toBe('none');
        expect(access.notCheckedInHere).toBe(true);
        expect(access.exemption).toBeUndefined();
      });
    }

    it(`children are unaffected by the checkbox on '${rule}'`, () => {
      const s = session(rule, true);
      expect(allowed(childTicketAccess(ticketedChild, s).ticket)).toBe(true);
      expect(allowed(childTicketAccess(ticketlessChild, s).ticket)).toBe(rule === 'open');
    });
  }
});

describe('ticket scoping (Attendee.has_ticket_for)', () => {
  it('a ticket for another event does not satisfy the rule, for a child', () => {
    const child = { ticket_type: 'event', ticket_details: eventTicket('other-event') };
    expect(childTicketAccess(child, session('children')).ticket).toBe('none');
  });

  it('a session ticket for another session does not satisfy the rule, for an adult', () => {
    const adult = { ticket_type: 'session', ticket_details: sessionTicket('other-session') };
    expect(parentTicketAccess(adult, session('all')).ticket).toBe('none');
  });

  it('a session ticket for this very session counts', () => {
    expect(childTicketAccess({ ticket_details: sessionTicket() }, session('children')).ticket).toBe(
      'session'
    );
    expect(parentTicketAccess({ ticket_details: sessionTicket() }, session('all')).ticket).toBe(
      'session'
    );
  });

  it('a guardian-only marker for another event does not exempt', () => {
    const adult = { ticket_type: null, ticket_details: null, guardian_only_event_ids: ['other'] };
    expect(parentTicketAccess(adult, session('all')).ticket).toBe('none');
  });

  it('the guardian exemption is reported as such, not as a held ticket', () => {
    expect(parentTicketAccess(confirmedGuardian, session('all'))).toEqual({
      ticket: 'event',
      exemption: 'guardian_only',
    });
  });

  it('where no ticket is asked for, the exemption is "not_required"; a held ticket is shown as held', () => {
    expect(childTicketAccess(ticketlessChild, session('open'))).toEqual({
      ticket: 'event',
      exemption: 'not_required',
    });
    expect(childTicketAccess(ticketedChild, session('open'))).toEqual({ ticket: 'event' });
  });

  it('with no active session, falls back to the API ticket_type', () => {
    expect(effectiveTicketType({ ticket_type: 'session' }, null)).toBe('session');
    expect(effectiveParentTicketType({ ticket_type: null }, null)).toBe('none');
  });
});

describe('rule resolution', () => {
  it('reads effective_ticket_rule and adults_not_checked_in', () => {
    expect(ticketRuleOf(session('all'))).toBe('all');
    expect(adultsNotCheckedIn(session('open', true))).toBe(true);
    expect(adultsNotCheckedIn(null)).toBe(false);
  });

  it('treats a payload without the new fields as open, adults checked in', () => {
    const bare = {
      id: SESSION,
      event: EVENT,
      name: 'S',
      start_time: '09:00',
      is_active: true,
      event_name: 'E',
    } as Session;
    expect(ticketRuleOf(bare)).toBe('open');
    expect(adultsNotCheckedIn(bare)).toBe(false);
  });
});
