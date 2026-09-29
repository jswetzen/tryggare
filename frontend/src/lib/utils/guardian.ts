/**
 * Guardian rules for the public registration form (owner decision eb5d26f4,
 * 2026-09-29): a guardian is required only when the registration includes at
 * least one child; any adult parent row counts as a guardian of every child;
 * a guardian need not hold a ticket; and there is no legitimate no-guardian
 * path on the public form.
 *
 * Kept out of the page component so the "is this row in play at all?" rule
 * has one definition that handleSubmit, the server-error mapping and the unit
 * tests all share — the payload's `parents` array is exactly the touched rows
 * in order, and the server reports per-row errors by position in that array,
 * so a second, slightly different filter anywhere would attribute a 400 to
 * the wrong person.
 */

/**
 * The value the parent ticket <select> uses for its "no ticket, guardian
 * only" option. Deliberately not a ticket-type id shape (those are UUIDs) and
 * never stored on the row: choosing it sets `guardianOnly` instead, so the
 * sentinel cannot leak into the payload or the ticket-composition counts.
 */
export const GUARDIAN_ONLY_VALUE = 'guardian-only';

/** The subset of the page's ParentRow this module reads. */
export interface ParentDraft {
  first_name: string;
  last_name: string;
  phone: string;
  email: string;
  relationship_type: string;
  allergies: string;
  notes: string;
  healthInfoStatus: string;
  ticketTypeId: string;
  guardianOnly: boolean;
  extraSelections: Record<string, unknown>;
}

/**
 * True when the guardian has done anything at all to this row. Only a row
 * that is wholly untouched (the blank spare row the form always renders) is
 * dropped from the submission; a row with, say, only a phone number typed is
 * *not* dropped — it is in play, so it gets validated (and asked for its
 * name) instead of silently vanishing along with the data.
 *
 * `extraSelections` is only ever written by an explicit click (required
 * extras default to selected via extraState's fallback, not via this
 * record), so a non-empty record means the guardian touched an extra.
 */
export function parentRowTouched(p: ParentDraft): boolean {
  return (
    p.first_name.trim() !== '' ||
    p.last_name.trim() !== '' ||
    p.phone.trim() !== '' ||
    p.email.trim() !== '' ||
    p.relationship_type !== '' ||
    p.allergies.trim() !== '' ||
    p.notes.trim() !== '' ||
    p.healthInfoStatus !== 'none' ||
    p.ticketTypeId !== '' ||
    p.guardianOnly ||
    Object.keys(p.extraSelections).length > 0
  );
}

/**
 * The rows that will be submitted, with their position in the full `parents`
 * state array. Their order is the payload's `parents` order, i.e. the index
 * space the server's per-row errors use.
 */
export function submittedParentEntries<T extends ParentDraft>(
  parents: T[]
): { p: T; index: number }[] {
  return parents.map((p, index) => ({ p, index })).filter(({ p }) => parentRowTouched(p));
}

/**
 * True when the registration has children but no named adult to be their
 * guardian. Adults-only is fine (no children, nothing to guard); the caller
 * separately rejects a registration with neither.
 */
export function guardianMissing(parents: ParentDraft[], childCount: number): boolean {
  return childCount > 0 && !parents.some((p) => p.first_name.trim() !== '');
}

/**
 * True when the generic "add a guardian for the children" line should be
 * shown: there are children, no adult is named, AND no adult row has been
 * touched at all. Once any adult row holds data, that row's own named errors
 * (missing first name, relation, phone) already say what to fix, and a
 * second, generic line on top of them reads as a contradiction.
 */
export function guardianLineNeeded(parents: ParentDraft[], childCount: number): boolean {
  return guardianMissing(parents, childCount) && !parents.some(parentRowTouched);
}

/**
 * Where an error-summary line sits in the page, so the summary can list
 * problems in the order the fields appear: contact email, then adults
 * (Förälder 1 first — the generic guardian line takes Förälder 1's place),
 * then children, then whole-registration items, then the promo code. Within
 * a person, in the order of that card's fields. Keyed off the line's id
 * (`<kind>-<field...>-<row index>`), the only thing the lines share.
 */
export function problemDomRank(id: string): [number, number, number] {
  const row = Number(/-(\d+)$/.exec(id)?.[1] ?? 0);
  if (id === 'contact-email') return [0, 0, 0];
  if (id === 'guardian-required' || id === 'at-least-one-member') return [1, -1, 0];
  const parentFields = [
    'parent-first-name-',
    'parent-relationship-',
    'parent-phone-',
    'parent-ticket-type-',
    'parent-extra-',
    'parent-consent-',
    'server-parent-'
  ];
  const parentField = parentFields.findIndex((prefix) => id.startsWith(prefix));
  if (parentField >= 0) return [1, row, parentField];
  const childFields = [
    'child-info-',
    'child-ticket-type-',
    'child-extra-',
    'child-consent-',
    'server-child-'
  ];
  const childField = childFields.findIndex((prefix) => id.startsWith(prefix));
  if (childField >= 0) return [2, row, childField];
  if (id.startsWith('registration-extra-')) return [3, 0, 0];
  if (id === 'promo-code') return [4, 0, 0];
  return [5, 0, 0];
}

/** Stable sort of summary lines into page order (see problemDomRank). */
export function sortProblemsByDomOrder<T extends { id: string }>(problems: T[]): T[] {
  return problems
    .map((problem, position) => ({ problem, position, rank: problemDomRank(problem.id) }))
    .sort(
      (a, b) =>
        a.rank[0] - b.rank[0] ||
        a.rank[1] - b.rank[1] ||
        a.rank[2] - b.rank[2] ||
        a.position - b.position
    )
    .map(({ problem }) => problem);
}
