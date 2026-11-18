import { describe, it, expect } from 'vitest';
import type { FamilyApiResponse, Session } from '$lib/checkin/types';
import { sessionTicketName, sessionRowLabel, withGrantedTicket } from './sessionTicketLabel';
import { isRegistrationCancelled, isCancelledAtDoor, transformFamily } from './mergeFamilies';

const tickets = [
  { session: 's-morning', session_name: 'Morning Session' },
  { session: 's-verkstad', session_name: 'Barnverkstaden' },
];

describe('sessionTicketName (which session ticket a row names)', () => {
  it('names the ticket for the active session, not the first one', () => {
    expect(sessionTicketName(tickets, 's-verkstad')).toBe('Barnverkstaden');
  });
  it('falls back to the first ticket when none matches', () => {
    expect(sessionTicketName(tickets, 's-other')).toBe('Morning Session');
  });
  it('falls back to the first ticket with no active session', () => {
    expect(sessionTicketName(tickets, null)).toBe('Morning Session');
  });
  it('is undefined with no tickets', () => {
    expect(sessionTicketName([], 's-verkstad')).toBeUndefined();
  });
});

const session: Session = {
  id: 's-verkstad',
  event: 'ev-1',
  name: 'Barnverkstaden',
  start_time: '09:00',
  is_active: true,
  event_name: 'Conference',
  effective_ticket_rule: 'children',
  adults_not_checked_in: false,
};

describe('registrationCancelled flag', () => {
  it('is set only when the desk event is in registration_cancelled_event_ids', () => {
    expect(isRegistrationCancelled({ registration_cancelled_event_ids: ['ev-1'] }, session)).toBe(true);
    expect(isRegistrationCancelled({ registration_cancelled_event_ids: ['ev-2'] }, session)).toBe(false);
    expect(isRegistrationCancelled({}, session)).toBe(false);
    expect(isRegistrationCancelled({ registration_cancelled_event_ids: ['ev-1'] }, null)).toBe(false);
  });

  it('is carried onto the transformed child and parent', () => {
    const api: FamilyApiResponse = {
      id: 'f',
      last_name: 'Eriksson',
      display_name: 'Eriksson',
      children: [
        { id: 'c', first_name: 'Felix', last_name: 'Eriksson', ticket_type: 'none', family: 'f', registration_cancelled_event_ids: ['ev-1'] },
      ],
      parents: [
        { id: 'p', first_name: 'Pia', last_name: 'Eriksson', relationship_type: 'mother', ticket_type: null, family: 'f', registration_cancelled_event_ids: ['ev-1'] },
      ],
    } as FamilyApiResponse;
    const fam = transformFamily(api, session);
    expect(fam.children[0].registrationCancelled).toBe(true);
    expect(fam.parents[0].registrationCancelled).toBe(true);
    expect(transformFamily(api, null).children[0].registrationCancelled).toBe(false);
  });
});

describe('post-grant row (F1: stale older ticket named after a door grant)', () => {
  const api = {
    id: 'f',
    last_name: 'Hansen',
    display_name: 'Hansen',
    children: [
      {
        id: 'astrid', first_name: 'Astrid', last_name: 'Hansen', ticket_type: 'session', family: 'f',
        ticket_details: { event_tickets: [], session_tickets: [{ id: 't1', session: 's-morning', session_name: 'Morning Session' }] },
      },
    ],
    parents: [],
  } as unknown as FamilyApiResponse;

  it('before the grant the row has no ticket for the active session', () => {
    expect(transformFamily(api, session).children[0].ticket).toBe('none');
  });

  it('after the page local update the row is a session ticket named for the active session', () => {
    const child = transformFamily(api, session).children[0];
    const after = withGrantedTicket(child, 'session');
    expect(after.ticket).toBe('session');
    // ticket_details still holds only the older ticket, exactly as in the page
    expect(after.ticket_details?.session_tickets.map((t) => t.session)).toEqual(['s-morning']);
    expect(sessionRowLabel(after.ticket_details?.session_tickets, session.id, session.name)).toBe('Barnverkstaden');
  });

  it('a Fullt evenemangspass grant flips the type to event', () => {
    const child = transformFamily(api, session).children[0];
    expect(withGrantedTicket(child, 'event').ticket).toBe('event');
  });

  it('with no active session it falls back to the first ticket', () => {
    expect(sessionRowLabel(tickets, null, null)).toBe('Morning Session');
  });
});

describe('isCancelledAtDoor (only who would have been offered the grant)', () => {
  it('true for a ticketless cancelled person', () => {
    expect(isCancelledAtDoor({ ticket: 'none', registrationCancelled: true })).toBe(true);
  });
  it('false for an adult admitted without a ticket (ticket event, exemption)', () => {
    expect(isCancelledAtDoor({ ticket: 'event', registrationCancelled: true })).toBe(false);
  });
  it('false when unconfirmed wins or not cancelled', () => {
    expect(isCancelledAtDoor({ ticket: 'none', registrationCancelled: true, registrationUnconfirmed: true })).toBe(false);
    expect(isCancelledAtDoor({ ticket: 'none' })).toBe(false);
  });
});
