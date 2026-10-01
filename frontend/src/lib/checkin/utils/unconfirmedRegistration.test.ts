import { describe, it, expect } from 'vitest';
import type { FamilyApiResponse, Session, UnconfirmedRegistration } from '$lib/checkin/types';
import { isRegistrationUnconfirmed, mergeFamilies, transformFamily } from './mergeFamilies';

/**
 * The server refuses a person with "Registration is not yet confirmed" on every session of an
 * event in unconfirmed_registration.event_ids and on the sessions in .session_ids
 * (backend checkins/eligibility.py). The desk marks exactly those people for the session on
 * screen, so a Check In button or a ticket-grant offer is never shown to someone the door will
 * turn away.
 */

const EVENT = 'event-1';
const SESSION = 'session-1';
const OTHER_SESSION = 'session-2';

const session = (over: Partial<Session> = {}): Session => ({
  id: SESSION,
  event: EVENT,
  name: 'Morning',
  start_time: '09:00',
  is_active: true,
  event_name: 'Conference',
  requires_ticket: true,
  effective_ticket_rule: 'children',
  adults_not_checked_in: false,
  ...over,
});

const none: UnconfirmedRegistration = { event_ids: [], session_ids: [] };

const family = (
  childMarker: UnconfirmedRegistration | undefined,
  parentMarker: UnconfirmedRegistration | undefined = undefined
): FamilyApiResponse => ({
  id: 'fam-1',
  last_name: 'Lindgren',
  display_name: 'Lindgren',
  children: [
    {
      id: 'child-1',
      first_name: 'Nils',
      last_name: 'Lindgren',
      // Ticketless on a 'children' rule: this is the person who would otherwise be offered a grant.
      ticket_type: 'none',
      family: 'fam-1',
      unconfirmed_registration: childMarker,
    },
  ],
  parents: [
    {
      id: 'parent-1',
      first_name: 'Ola',
      last_name: 'Lindgren',
      name: 'Ola Lindgren',
      relationship_type: 'father',
      ticket_type: null,
      family: 'fam-1',
      unconfirmed_registration: parentMarker,
    },
  ],
});

describe('isRegistrationUnconfirmed', () => {
  it('is blocked when the session\'s event is in event_ids', () => {
    expect(
      isRegistrationUnconfirmed({ unconfirmed_registration: { event_ids: [EVENT], session_ids: [] } }, session())
    ).toBe(true);
  });

  it('is blocked when the session id is in session_ids', () => {
    expect(
      isRegistrationUnconfirmed({ unconfirmed_registration: { event_ids: [], session_ids: [SESSION] } }, session())
    ).toBe(true);
  });

  it('is not blocked on another session when only one session is listed', () => {
    const marker = { event_ids: [], session_ids: [OTHER_SESSION] };
    expect(isRegistrationUnconfirmed({ unconfirmed_registration: marker }, session())).toBe(false);
    expect(isRegistrationUnconfirmed({ unconfirmed_registration: marker }, session({ id: OTHER_SESSION }))).toBe(true);
  });

  it('is not blocked on another event', () => {
    expect(
      isRegistrationUnconfirmed(
        { unconfirmed_registration: { event_ids: ['event-9'], session_ids: [] } },
        session()
      )
    ).toBe(false);
  });

  it('tolerates a missing, null or empty marker, and a missing session', () => {
    expect(isRegistrationUnconfirmed({}, session())).toBe(false);
    expect(isRegistrationUnconfirmed({ unconfirmed_registration: null }, session())).toBe(false);
    expect(isRegistrationUnconfirmed({ unconfirmed_registration: none }, session())).toBe(false);
    expect(
      isRegistrationUnconfirmed({ unconfirmed_registration: { event_ids: [EVENT], session_ids: [] } }, null)
    ).toBe(false);
  });
});

describe('transformFamily / mergeFamilies', () => {
  it('marks a child blocked by event id', () => {
    const f = transformFamily(family({ event_ids: [EVENT], session_ids: [] }), session());
    expect(f.children[0].registrationUnconfirmed).toBe(true);
  });

  it('marks an adult blocked by session id', () => {
    const f = transformFamily(family(none, { event_ids: [], session_ids: [SESSION] }), session());
    expect(f.parents[0].registrationUnconfirmed).toBe(true);
    expect(f.children[0].registrationUnconfirmed).toBe(false);
  });

  it('does not mark anyone on a session the marker does not cover', () => {
    const api = family(
      { event_ids: [], session_ids: [OTHER_SESSION] },
      { event_ids: ['event-9'], session_ids: [] }
    );
    const f = transformFamily(api, session());
    expect(f.children[0].registrationUnconfirmed).toBe(false);
    expect(f.parents[0].registrationUnconfirmed).toBe(false);
  });

  it('tolerates an undefined marker (fixtures, older server)', () => {
    const f = transformFamily(family(undefined, undefined), session());
    expect(f.children[0].registrationUnconfirmed).toBe(false);
    expect(f.parents[0].registrationUnconfirmed).toBe(false);
  });

  it('marks nobody while no session is on screen', () => {
    const f = transformFamily(family({ event_ids: [EVENT], session_ids: [] }), null);
    expect(f.children[0].registrationUnconfirmed).toBe(false);
  });

  it('wins over the ticket-grant offer: the child is flagged even though ticketless', () => {
    // ticket stays 'none' (it is true: they hold no ticket) but the desk reads the flag first,
    // so the "No Ticket" chip and its grant panel are not offered. See the component tests.
    const f = transformFamily(family({ event_ids: [EVENT], session_ids: [] }), session());
    expect(f.children[0].ticket).toBe('none');
    expect(f.children[0].registrationUnconfirmed).toBe(true);
  });

  it('does not flag an adult on a session that never checks adults in', () => {
    const f = transformFamily(
      family(none, { event_ids: [EVENT], session_ids: [] }),
      session({ adults_not_checked_in: true })
    );
    expect(f.parents[0].notCheckedInHere).toBe(true);
    expect(f.parents[0].registrationUnconfirmed).toBe(false);
  });

  it('recomputes the flag when the same family is merged for another session', () => {
    const api = family({ event_ids: [], session_ids: [SESSION] });
    const first = mergeFamilies([], [api], session());
    expect(first[0].children[0].registrationUnconfirmed).toBe(true);
    const second = mergeFamilies(first, [api], session({ id: OTHER_SESSION }));
    expect(second[0].children[0].registrationUnconfirmed).toBe(false);
  });
});
