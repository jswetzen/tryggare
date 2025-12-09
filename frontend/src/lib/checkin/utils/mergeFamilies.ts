import type { Family, Child, FamilyApiResponse, TicketType } from '$lib/checkin/types';

/**
 * Transform API family response to frontend Family type
 * Note: Does NOT include local-only fields like checkInActionId
 */
function transformFamilyResponse(apiFamily: FamilyApiResponse): Omit<Family, 'children'> & {
  children: Omit<Child, 'checkInActionId' | 'checkInRecordId' | 'checkInTime'>[]
} {
  return {
    id: apiFamily.id,
    last_name: apiFamily.last_name,
    display_name: apiFamily.display_name,
    name: apiFamily.display_name,
    children: apiFamily.children.map((child) => ({
      id: child.id,
      first_name: child.first_name,
      last_name: child.last_name,
      name: `${child.first_name} ${child.last_name}`,
      ticket: (child.ticket_type as TicketType) || 'none',
      ticket_type: (child.ticket_type as TicketType) || 'none',
      ticket_details: child.ticket_details,
      checkedIn: child.is_checked_in || false,
      family: child.family,
      birthdate: child.birthdate,
      allergies: child.allergies,
      notes: child.notes,
      qr_token: child.qr_token,
    })),
    parents: apiFamily.parents,
    last_participation_date: apiFamily.last_participation_date,
  };
}

/**
 * Merges fresh API family data with existing local state
 *
 * Preserves local-only fields:
 * - checkInActionId: UUID linking to undo timer
 * - checkInRecordId: Backend record ID for API calls
 * - checkInTime: Formatted time string for display
 *
 * Updates from API:
 * - checkedIn status (backend is source of truth)
 * - All other child/family properties
 * - Family and child additions/removals
 *
 * @param existingFamilies - Current local state with undo timers
 * @param apiFamilies - Fresh data from backend API
 * @returns Merged families array with preserved local state
 */
export function mergeFamilies(
  existingFamilies: Family[],
  apiFamilies: FamilyApiResponse[]
): Family[] {
  // Transform API responses
  const freshFamilies = apiFamilies.map(transformFamilyResponse);

  // Create map of existing families for O(1) lookup
  const existingFamilyMap = new Map(
    existingFamilies.map(f => [f.id, f])
  );

  // Merge fresh data with existing local state
  return freshFamilies.map(freshFamily => {
    const existingFamily = existingFamilyMap.get(freshFamily.id);

    if (!existingFamily) {
      // New family - return as-is (with undefined local fields)
      return freshFamily as Family;
    }

    // Create map of existing children for O(1) lookup
    const existingChildMap = new Map(
      existingFamily.children.map(c => [c.id, c])
    );

    // Merge children, preserving local state
    const mergedChildren: Child[] = freshFamily.children.map(freshChild => {
      const existingChild = existingChildMap.get(freshChild.id);

      if (!existingChild) {
        // New child - return as-is
        return freshChild as Child;
      }

      // Merge: use fresh API data but preserve local-only fields
      return {
        ...freshChild,
        // Preserve local check-in state for undo timers
        checkInActionId: existingChild.checkInActionId,
        checkInRecordId: existingChild.checkInRecordId,
        checkInTime: existingChild.checkInTime,
      } as Child;
    });

    return {
      ...freshFamily,
      children: mergedChildren,
    } as Family;
  });
}
