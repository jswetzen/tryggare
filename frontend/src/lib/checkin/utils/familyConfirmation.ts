import type { Family } from '$lib/checkin/types';

/**
 * What the collapsed family row says about people the server will refuse on the session on
 * screen because their registration is not confirmed (`registrationUnconfirmed`).
 *
 * `total` is everyone the row speaks for: the children, plus the adults only when the session
 * checks adults in (otherwise an adult can never be blocked here, and counting them would make
 * a family whose every child is blocked read as "some"). `blocked` counts people who are still to
 * be checked in: someone already in has nothing left to wait for.
 */
export interface FamilyConfirmationState {
  blocked: number;
  /** Of `blocked`, how many are children and how many are adults (adults only when counted). */
  blockedChildren: number;
  blockedAdults: number;
  total: number;
  /** Everyone the row speaks for is blocked. */
  all: boolean;
}

export function familyConfirmationState(
  family: Family,
  includeAdults: boolean = true
): FamilyConfirmationState {
  const isBlocked = (p: { registrationUnconfirmed?: boolean; checkedIn: boolean }) =>
    !!p.registrationUnconfirmed && !p.checkedIn;
  const blockedChildren = family.children.filter(isBlocked).length;
  const blockedAdults = includeAdults ? family.parents.filter(isBlocked).length : 0;
  const blocked = blockedChildren + blockedAdults;
  const total = family.children.length + (includeAdults ? family.parents.length : 0);
  return { blocked, blockedChildren, blockedAdults, total, all: blocked > 0 && blocked === total };
}

/**
 * Which message the collapsed family row's confirmation badge shows, as a key plus the count to
 * interpolate, or null when nobody is blocked.
 *
 * Everyone blocked: the plain "Awaiting confirmation" (it goes in the row's status slot, where a
 * count would only repeat the count line). Some blocked: a count, naming WHO when they are all
 * adults or all children, because "1 awaiting confirmation" next to "2 children" reads as one of
 * the children when it is in fact the mother. Mixed: just the number.
 */
export function confirmationBadgeMessage(
  state: FamilyConfirmationState
): { key: string; count: number } | null {
  const { blocked, blockedChildren, blockedAdults, all } = state;
  if (blocked === 0) return null;
  if (all) return { key: 'checkin.awaitingConfirmation', count: blocked };
  if (blockedChildren === 0) {
    return {
      key: blockedAdults === 1 ? 'checkin.awaitingConfirmationAdultOne' : 'checkin.awaitingConfirmationAdultMany',
      count: blocked
    };
  }
  if (blockedAdults === 0) {
    return {
      key: blockedChildren === 1 ? 'checkin.awaitingConfirmationChildOne' : 'checkin.awaitingConfirmationChildMany',
      count: blocked
    };
  }
  return { key: 'checkin.awaitingConfirmationCount', count: blocked };
}

/** True when anyone in the family, child or adult, is blocked on the session on screen. The
 *  "all checked in" state must never show while this holds: a blocked person is not checked in. */
export function hasBlockedPerson(family: Family): boolean {
  return familyConfirmationState(family, true).blocked > 0;
}
