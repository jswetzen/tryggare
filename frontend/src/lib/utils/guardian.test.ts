import { describe, expect, it } from 'vitest';
import {
  GUARDIAN_ONLY_VALUE,
  guardianLineNeeded,
  guardianMissing,
  parentRowTouched,
  sortProblemsByDomOrder,
  submittedParentEntries,
  type ParentDraft
} from './guardian';

function row(overrides: Partial<ParentDraft> = {}): ParentDraft {
  return {
    first_name: '',
    last_name: '',
    phone: '',
    email: '',
    relationship_type: '',
    allergies: '',
    notes: '',
    healthInfoStatus: 'none',
    ticketTypeId: '',
    guardianOnly: false,
    extraSelections: {},
    ...overrides
  };
}

describe('parentRowTouched', () => {
  it('is false only for a wholly untouched row', () => {
    expect(parentRowTouched(row())).toBe(false);
    expect(parentRowTouched(row({ first_name: '   ', phone: ' ' }))).toBe(false);
  });

  it.each([
    ['first name', { first_name: 'Sam' }],
    ['last name', { last_name: 'K' }],
    ['phone', { phone: '070' }],
    ['email', { email: 'a@b.se' }],
    ['relationship', { relationship_type: 'MOM' }],
    ['allergies', { allergies: 'nuts' }],
    ['notes', { notes: 'x' }],
    ['health status', { healthInfoStatus: 'declined' }],
    ['ticket type', { ticketTypeId: 'tt-1' }],
    ['guardian-only choice', { guardianOnly: true }],
    ['an extra click', { extraSelections: { 'extra-1': { selected: true } } }]
  ])('is true once %s has been touched', (_label, overrides) => {
    expect(parentRowTouched(row(overrides as Partial<ParentDraft>))).toBe(true);
  });
});

describe('submittedParentEntries', () => {
  it('keeps touched rows in order with their position in the full array', () => {
    const parents = [row(), row({ first_name: 'A' }), row(), row({ phone: '070' })];
    const entries = submittedParentEntries(parents);
    expect(entries.map((e) => e.index)).toEqual([1, 3]);
    expect(entries[0].p).toBe(parents[1]);
  });

  it('does not drop a blank Förälder 1 that other rows lean on the data of', () => {
    // Row 0 has only a phone: it is in play (and will be asked for a name),
    // not silently dropped so that the second row becomes payload index 0.
    const entries = submittedParentEntries([row({ phone: '070' }), row({ first_name: 'B' })]);
    expect(entries.map((e) => e.index)).toEqual([0, 1]);
  });
});

describe('guardianMissing', () => {
  it('is true when children exist and no row is named', () => {
    expect(guardianMissing([row()], 1)).toBe(true);
    expect(guardianMissing([row({ phone: '070' })], 2)).toBe(true);
  });

  it('is false once any adult row is named, wherever it sits', () => {
    expect(guardianMissing([row(), row({ first_name: 'B' })], 1)).toBe(false);
  });

  it('is false for a guardian-only adult (no ticket needed)', () => {
    expect(guardianMissing([row({ first_name: 'B', guardianOnly: true })], 1)).toBe(false);
  });

  it('is false when there are no children to guard', () => {
    expect(guardianMissing([row()], 0)).toBe(false);
  });
});

describe('GUARDIAN_ONLY_VALUE', () => {
  it('is not shaped like a ticket-type id', () => {
    expect(GUARDIAN_ONLY_VALUE).toBe('guardian-only');
  });
});

describe('guardianLineNeeded', () => {
  it('is true only when children exist and no adult row has been touched', () => {
    expect(guardianLineNeeded([row()], 1)).toBe(true);
    expect(guardianLineNeeded([row(), row()], 2)).toBe(true);
  });

  it('is false as soon as any adult row holds data, even unnamed', () => {
    expect(guardianLineNeeded([row(), row({ phone: '070' })], 1)).toBe(false);
    expect(guardianLineNeeded([row({ relationship_type: 'MOM' })], 1)).toBe(false);
  });

  it('is false when a guardian is named or there are no children', () => {
    expect(guardianLineNeeded([row({ first_name: 'B' })], 1)).toBe(false);
    expect(guardianLineNeeded([row()], 0)).toBe(false);
  });
});

describe('sortProblemsByDomOrder', () => {
  const ids = (list: { id: string }[]) => list.map((p) => p.id);

  it('orders email, adults (guardian line first), children, registration extras, promo', () => {
    const shuffled = [
      { id: 'promo-code' },
      { id: 'registration-extra-x' },
      { id: 'child-ticket-type-0' },
      { id: 'child-info-1' },
      { id: 'parent-phone-1' },
      { id: 'parent-first-name-1' },
      { id: 'guardian-required' },
      { id: 'contact-email' }
    ];
    expect(ids(sortProblemsByDomOrder(shuffled))).toEqual([
      'contact-email',
      'guardian-required',
      'parent-first-name-1',
      'parent-phone-1',
      'child-ticket-type-0',
      'child-info-1',
      'registration-extra-x',
      'promo-code'
    ]);
  });

  it('orders one adult by the card fields and adults by row, with dashes in extra ids', () => {
    const list = [
      { id: 'parent-consent-0' },
      { id: 'parent-extra-ab-cd-0' },
      { id: 'parent-ticket-type-0' },
      { id: 'parent-phone-0' },
      { id: 'parent-relationship-0' },
      { id: 'parent-first-name-0' },
      { id: 'parent-first-name-2' },
      { id: 'parent-phone-1' }
    ];
    expect(ids(sortProblemsByDomOrder(list))).toEqual([
      'parent-first-name-0',
      'parent-relationship-0',
      'parent-phone-0',
      'parent-ticket-type-0',
      'parent-extra-ab-cd-0',
      'parent-consent-0',
      'parent-phone-1',
      'parent-first-name-2'
    ]);
  });

  it('puts the guardian-only line after the consent line and the nobody-attending line with the guardian line', () => {
    const list = [
      { id: 'parent-guardian-only-0' },
      { id: 'parent-consent-0' },
      { id: 'server-parent-0' },
      { id: 'parent-first-name-0' },
      { id: 'at-least-one-attending' },
      { id: 'contact-email' }
    ];
    expect(ids(sortProblemsByDomOrder(list))).toEqual([
      'contact-email',
      'at-least-one-attending',
      'parent-first-name-0',
      'parent-consent-0',
      'parent-guardian-only-0',
      'server-parent-0'
    ]);
  });

  it('is stable for ids of the same rank', () => {
    const list = [{ id: 'mystery-b' }, { id: 'mystery-a' }];
    expect(ids(sortProblemsByDomOrder(list))).toEqual(['mystery-b', 'mystery-a']);
  });
});
