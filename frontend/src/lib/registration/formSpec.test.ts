import { describe, expect, it } from 'vitest';
import fixture from './__fixtures__/form-spec.v1.json';
import type { RegistrationFormSpec } from '$lib/api/types';
import {
  applicablePersonExtras,
  applicableTicketTypes,
  fieldFor,
  isFieldRequired,
  isFieldVisible,
  omitHiddenFields,
  reconcileSelections,
  registrationExtras,
  type ExtraSelectionState,
  type PersonSelection
} from './formSpec';

const spec = () => structuredClone(fixture) as unknown as RegistrationFormSpec;

const ADULT = '00000000-0000-0000-0000-000000000014';
const CHILD = '00000000-0000-0000-0000-000000000015';
const DAY1 = '00000000-0000-0000-0000-000000000016';
const LUNCH = '00000000-0000-0000-0000-00000000001e';
const MEAT = '00000000-0000-0000-0000-00000000001f';

describe('selection helpers', () => {
  it('offers parents their own and "either" ticket types, children theirs', () => {
    expect(applicableTicketTypes(spec(), false).map((t) => t.id)).toEqual([ADULT, DAY1]);
    expect(applicableTicketTypes(spec(), true).map((t) => t.id)).toEqual([CHILD, DAY1]);
    expect(applicableTicketTypes(null, true)).toEqual([]);
  });

  it('splits extras into per-attendee (by applies_to) and per-registration', () => {
    const s = spec();
    expect(applicablePersonExtras(s, true).map((e) => e.id)).toEqual([LUNCH]);
    expect(registrationExtras(s)).toEqual([]);
    s.extras[0].per_attendee = false;
    expect(applicablePersonExtras(s, false)).toEqual([]);
    expect(registrationExtras(s).map((e) => e.id)).toEqual([LUNCH]);
    expect(registrationExtras(null)).toEqual([]);
  });
});

describe('field lookups', () => {
  it('finds a field by group and key', () => {
    expect(fieldFor(spec(), 'child', 'birthdate')).toEqual({
      key: 'birthdate',
      visible: true,
      required: true
    });
    expect(fieldFor(spec(), 'parent', 'birthdate')).toBeUndefined();
  });

  it('reads required from the spec (child last name and birthdate are form-required)', () => {
    const s = spec();
    expect(isFieldRequired(s, 'child', 'last_name')).toBe(true);
    expect(isFieldRequired(s, 'parent', 'last_name')).toBe(false);
    expect(isFieldRequired(s, 'parent', 'phone')).toBe(true);
  });

  it('treats a hidden or unlisted field as not asked and not required', () => {
    const s = spec();
    s.fields.parent.find((f) => f.key === 'phone')!.visible = false;
    expect(isFieldVisible(s, 'parent', 'phone')).toBe(false);
    expect(isFieldRequired(s, 'parent', 'phone')).toBe(false);
    expect(isFieldVisible(s, 'parent', 'nope')).toBe(false);
    expect(isFieldVisible(null, 'parent', 'phone')).toBe(false);
  });
});

describe('reconcileSelections', () => {
  const picked: ExtraSelectionState = { selected: true, choiceId: MEAT, quantity: 1 };
  const person = (ticketTypeId: string, extras = {}): PersonSelection => ({
    ticketTypeId,
    extraSelections: extras
  });

  it('keeps everything the new spec still offers', () => {
    const s = spec();
    const result = reconcileSelections(
      {
        spec: s,
        parents: [person(ADULT)],
        children: [person(CHILD, { [LUNCH]: picked })],
        registrationExtraSelections: {}
      },
      spec()
    );
    expect(result.cleared).toEqual([]);
    expect(result.parents[0].ticketTypeId).toBe(ADULT);
    expect(result.children[0].ticketTypeId).toBe(CHILD);
    expect(result.children[0].extraSelections[LUNCH]).toEqual(picked);
  });

  it('clears a ticket type that was deleted, by its old name, once', () => {
    const next = spec();
    next.ticket_types = next.ticket_types.filter((t) => t.id !== CHILD);
    const result = reconcileSelections(
      {
        spec: spec(),
        parents: [],
        children: [person(CHILD), person(CHILD)],
        registrationExtraSelections: {}
      },
      next
    );
    expect(result.children.map((c) => c.ticketTypeId)).toEqual(['', '']);
    expect(result.cleared).toEqual([{ kind: 'ticketType', name: 'Child 0-12' }]);
  });

  it('clears a ticket type that no longer applies to that kind of attendee', () => {
    const next = spec();
    next.ticket_types.find((t) => t.id === ADULT)!.applies_to = 'child';
    const result = reconcileSelections(
      {
        spec: spec(),
        parents: [person(ADULT)],
        children: [],
        registrationExtraSelections: {}
      },
      next
    );
    expect(result.parents[0].ticketTypeId).toBe('');
    expect(result.cleared).toEqual([{ kind: 'ticketType', name: 'Adult' }]);
  });

  it('clears a deleted extra, but not an untouched entry for it', () => {
    const next = spec();
    next.extras = [];
    const untouched: ExtraSelectionState = { selected: false, choiceId: '', quantity: 1 };
    const result = reconcileSelections(
      {
        spec: spec(),
        parents: [person('', { [LUNCH]: untouched })],
        children: [person('', { [LUNCH]: picked })],
        registrationExtraSelections: {}
      },
      next
    );
    expect(result.parents[0].extraSelections).toEqual({});
    expect(result.children[0].extraSelections).toEqual({});
    expect(result.cleared).toEqual([{ kind: 'extra', name: 'Lunch' }]);
  });

  it('clears only the choice when the extra stays but the choice is gone', () => {
    const next = spec();
    next.extras[0].choices = next.extras[0].choices.filter((c) => c.id !== MEAT);
    const result = reconcileSelections(
      {
        spec: spec(),
        parents: [],
        children: [person('', { [LUNCH]: picked })],
        registrationExtraSelections: {}
      },
      next
    );
    expect(result.children[0].extraSelections[LUNCH]).toEqual({ ...picked, choiceId: '' });
    expect(result.cleared).toEqual([{ kind: 'extraChoice', name: 'Lunch – Meat' }]);
  });

  it('reconciles per-registration extras that were turned per-attendee', () => {
    const old = spec();
    old.extras[0].per_attendee = false;
    const result = reconcileSelections(
      {
        spec: old,
        parents: [],
        children: [],
        registrationExtraSelections: { [LUNCH]: picked }
      },
      spec()
    );
    expect(result.registrationExtraSelections).toEqual({});
    expect(result.cleared).toEqual([{ kind: 'extra', name: 'Lunch' }]);
  });

  it('does not mutate its input', () => {
    const next = spec();
    next.ticket_types = [];
    const parents = [person(ADULT)];
    reconcileSelections(
      { spec: spec(), parents, children: [], registrationExtraSelections: {} },
      next
    );
    expect(parents[0].ticketTypeId).toBe(ADULT);
  });
});

describe('reconcileSelections and required extras', () => {
  const unticked: ExtraSelectionState = { selected: false, choiceId: '', quantity: 1 };

  it('selects an extra that is now required and lists it', () => {
    const next = spec();
    next.extras[0].required = true;
    const old = spec();
    old.extras[0].required = false;
    const result = reconcileSelections(
      {
        spec: old,
        parents: [],
        children: [{ ticketTypeId: '', extraSelections: { [LUNCH]: unticked } }],
        registrationExtraSelections: {}
      },
      next
    );
    expect(result.children[0].extraSelections[LUNCH].selected).toBe(true);
    expect(result.nowRequired).toEqual([{ kind: 'extra', name: 'Lunch' }]);
  });

  it('lists a newly added required extra, not one that was already required', () => {
    const old = spec();
    const next = spec();
    next.extras.push({ ...next.extras[0], id: 'new-extra', name: 'Bus', required: true });
    const result = reconcileSelections(
      { spec: old, parents: [], children: [], registrationExtraSelections: {} },
      next
    );
    expect(result.nowRequired).toEqual([{ kind: 'extra', name: 'Bus' }]);
  });
});

describe('omitHiddenFields', () => {
  it('drops hidden keys only', () => {
    const s = spec();
    s.fields.parent.find((f) => f.key === 'email')!.visible = false;
    expect(omitHiddenFields(s, 'parent', { first_name: 'A', email: 'x', ticket_type: null })).toEqual({
      first_name: 'A',
      ticket_type: null
    });
  });
});
