import type { Family, Child, Session, FamilyApiResponse, TicketType } from '$lib/checkin/types';

type TicketableApiItem = {
  ticket_type?: string | null;
  ticket_details?: {
    event_tickets: { event: string }[];
    session_tickets: { session: string }[];
  } | null;
};

function effectiveTicketType(
  child: TicketableApiItem,
  session: Session | null
): TicketType {
  if (!session) return (child.ticket_type as TicketType) || 'none';

  // Session doesn't require a ticket — everyone can check in
  if (!session.requires_ticket) return 'event';

  const details = child.ticket_details;
  if (!details) return 'none';

  // EventTicket covers all sessions of the event
  if (details.event_tickets.some((t) => t.event === session.event)) return 'event';

  // SessionTicket must match the active session exactly
  if (details.session_tickets.some((t) => t.session === session.id)) return 'session';

  return 'none';
}

// Whether/how a parent can check in is governed by the session's
// effective_parent_checkin_policy (see checkins/eligibility.py
// parent_checkin_gate_error, the backend's single source of truth):
// - 'disabled': parent check-in isn't offered at all for this session — the
//   Guardians section won't even render (see CheckinExpandableTable's
//   parentCheckinEnabled prop), but return 'none' defensively.
// - 'open': no ticket needed, same shortcut children get when
//   session.requires_ticket is false.
// - 'ticket_required': same real ticket lookup children use.
function effectiveParentTicketType(
  parent: TicketableApiItem,
  session: Session | null
): TicketType {
  if (!session) return (parent.ticket_type as TicketType) || 'none';

  const policy = session.effective_parent_checkin_policy;
  if (policy === 'disabled') return 'none';
  if (policy === 'open') return 'event';

  const details = parent.ticket_details;
  if (!details) return 'none';

  if (details.event_tickets.some((t) => t.event === session.event)) return 'event';
  if (details.session_tickets.some((t) => t.session === session.id)) return 'session';

  return 'none';
}

export function transformFamily(apiFamily: FamilyApiResponse, session: Session | null): Family {
  return {
    id: apiFamily.id,
    last_name: apiFamily.last_name,
    display_name: apiFamily.display_name,
    name: apiFamily.display_name,
    children: apiFamily.children.map((child) => {
      const ticketType = effectiveTicketType(child, session);
      return {
        id: child.id,
        first_name: child.first_name,
        last_name: child.last_name,
        name: `${child.first_name} ${child.last_name}`,
        ticket: ticketType,
        ticket_type: ticketType,
        ticket_details: child.ticket_details,
        checkedIn: child.is_checked_in || false,
        family: child.family,
        birthdate: child.birthdate,
        allergies: child.allergies,
        notes: child.notes,
        qr_token: child.qr_token,
      };
    }),
    parents: apiFamily.parents.map((parent) => {
      const ticketType = effectiveParentTicketType(parent, session);
      return {
        id: parent.id,
        first_name: parent.first_name,
        last_name: parent.last_name,
        name: parent.name || `${parent.first_name} ${parent.last_name}`.trim(),
        phone: parent.phone,
        email: parent.email,
        relationship_type: parent.relationship_type,
        ticket: ticketType,
        ticket_type: ticketType,
        ticket_details: parent.ticket_details ?? undefined,
        checkedIn: parent.is_checked_in || false,
        checkInRecordId: parent.active_checkin_id ?? undefined,
        family: parent.family,
        is_parent: true,
      };
    }),
    last_participation_date: apiFamily.last_participation_date,
  } as Family;
}

/**
 * Merges fresh API family data with existing local state.
 *
 * Preserves local-only fields: checkInActionId, checkInRecordId, checkInTime.
 * Updates checkedIn status and all other properties from the API.
 */
export function mergeFamilies(
  existingFamilies: Family[],
  apiFamilies: FamilyApiResponse[],
  session: Session | null = null
): Family[] {
  const existingFamilyMap = new Map(existingFamilies.map(f => [f.id, f]));

  return apiFamilies.map((apiFamily) => {
    const fresh = transformFamily(apiFamily, session);
    const existing = existingFamilyMap.get(fresh.id);

    if (!existing) return fresh;

    const existingChildMap = new Map(existing.children.map(c => [c.id, c]));
    const existingParentMap = new Map(existing.parents.map(p => [p.id, p]));

    return {
      ...fresh,
      children: fresh.children.map((freshChild) => {
        const existingChild = existingChildMap.get(freshChild.id);
        if (!existingChild) return freshChild;
        return {
          ...freshChild,
          checkInActionId: existingChild.checkInActionId,
          checkInRecordId: existingChild.checkInRecordId,
          checkInTime: existingChild.checkInTime,
        };
      }),
      parents: fresh.parents.map((freshParent) => {
        const existingParent = existingParentMap.get(freshParent.id);
        if (!existingParent) return freshParent;
        return {
          ...freshParent,
          checkInActionId: existingParent.checkInActionId,
          checkInRecordId: existingParent.checkInRecordId,
          checkInTime: existingParent.checkInTime,
        };
      }),
    };
  });
}
