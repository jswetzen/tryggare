import { describe, it, expect } from 'vitest';
import type { Child, Family, Parent } from '$lib/checkin/types';
import { confirmationBadgeMessage, familyConfirmationState, hasBlockedPerson } from './familyConfirmation';

const child = (over: Partial<Child> = {}): Child => ({
  id: 'c',
  first_name: 'C',
  last_name: 'L',
  name: 'C L',
  ticket: 'event',
  ticket_type: 'event',
  checkedIn: false,
  family: 'f',
  ...over
});
const adult = (over: Partial<Parent> = {}): Parent => ({
  id: 'p',
  first_name: 'P',
  last_name: 'L',
  name: 'P L',
  relationship_type: 'mother',
  ticket: 'event',
  ticket_type: 'event',
  checkedIn: false,
  ...over
});
const fam = (children: Child[], parents: Parent[] = []): Family => ({
  id: 'f',
  last_name: 'L',
  display_name: 'L',
  name: 'L',
  children,
  parents
});

describe('familyConfirmationState', () => {
  it('nobody blocked', () => {
    expect(familyConfirmationState(fam([child(), child()], [adult()]))).toEqual({ blocked: 0, blockedChildren: 0, blockedAdults: 0, total: 3, all: false });
    expect(hasBlockedPerson(fam([child()]))).toBe(false);
  });

  it('some blocked', () => {
    const s = familyConfirmationState(fam([child({ registrationUnconfirmed: true }), child()]));
    expect(s).toEqual({ blocked: 1, blockedChildren: 1, blockedAdults: 0, total: 2, all: false });
  });

  it('all blocked, adults included', () => {
    const s = familyConfirmationState(
      fam([child({ registrationUnconfirmed: true })], [adult({ registrationUnconfirmed: true })])
    );
    expect(s).toEqual({ blocked: 2, blockedChildren: 1, blockedAdults: 1, total: 2, all: true });
  });

  it('an adult who is not blocked keeps the family at "some" unless the session skips adults', () => {
    const f = fam([child({ registrationUnconfirmed: true })], [adult()]);
    expect(familyConfirmationState(f, true).all).toBe(false);
    expect(familyConfirmationState(f, false)).toEqual({ blocked: 1, blockedChildren: 1, blockedAdults: 0, total: 1, all: true });
  });

  it('someone already checked in is not waiting for anything', () => {
    const f = fam([child({ registrationUnconfirmed: true, checkedIn: true }), child()]);
    expect(familyConfirmationState(f).blocked).toBe(0);
  });

  it('hasBlockedPerson sees an adult even when every child is in', () => {
    const f = fam([child({ checkedIn: true })], [adult({ registrationUnconfirmed: true })]);
    expect(hasBlockedPerson(f)).toBe(true);
  });
});

describe('confirmationBadgeMessage', () => {
  const blocked = { registrationUnconfirmed: true };
  const msg = (f: Family) => confirmationBadgeMessage(familyConfirmationState(f));

  it('is null when nobody is blocked', () => {
    expect(msg(fam([child()], [adult()]))).toBeNull();
  });

  it('everyone blocked uses the plain status text', () => {
    expect(msg(fam([child(blocked)], [adult(blocked)]))).toEqual({
      key: 'checkin.awaitingConfirmation',
      count: 2
    });
  });

  it('one blocked adult among others', () => {
    expect(msg(fam([child()], [adult(blocked), adult()]))).toEqual({
      key: 'checkin.awaitingConfirmationAdultOne',
      count: 1
    });
  });

  it('several blocked adults, no blocked child', () => {
    expect(msg(fam([child()], [adult(blocked), adult(blocked), adult()]))).toEqual({
      key: 'checkin.awaitingConfirmationAdultMany',
      count: 2
    });
  });

  it('one blocked child among others', () => {
    expect(msg(fam([child(blocked), child()], [adult()]))).toEqual({
      key: 'checkin.awaitingConfirmationChildOne',
      count: 1
    });
  });

  it('several blocked children, no blocked adult', () => {
    expect(msg(fam([child(blocked), child(blocked), child()], [adult()]))).toEqual({
      key: 'checkin.awaitingConfirmationChildMany',
      count: 2
    });
  });

  it('a blocked child and a blocked adult read as a bare count', () => {
    expect(msg(fam([child(blocked), child()], [adult(blocked), adult()]))).toEqual({
      key: 'checkin.awaitingConfirmationCount',
      count: 2
    });
  });
});
