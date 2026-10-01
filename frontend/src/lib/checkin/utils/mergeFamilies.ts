import type {
  Family,
  Child,
  Session,
  FamilyApiResponse,
  TicketType,
  TicketRule,
  TicketExemption
} from '$lib/checkin/types';

type TicketableApiItem = {
  ticket_type?: string | null;
  ticket_details?: {
    event_tickets: { event: string }[];
    session_tickets: { session: string }[];
  } | null;
  /** Parents only: events where this adult is a guardian-only adult on a CONFIRMED registration. */
  guardian_only_event_ids?: string[] | null;
};

export type TicketAccess = {
  /** 'none' means the server would refuse; anything else means it would accept. */
  ticket: TicketType;
  /** Why the person is allowed without holding a ticket (undefined when they hold one, or are blocked). */
  exemption?: TicketExemption;
  /** Adults only: the session never checks adults in (Session.adults_not_checked_in). */
  notCheckedInHere?: boolean;
};

// The rule the server enforces (checkins/eligibility.py): Session.effective_ticket_rule,
// i.e. the session's own rule or the event default. An older server only sends the
// derived requires_ticket / effective_parent_checkin_policy, so fall back to those.
export function ticketRuleOf(session: Session): TicketRule {
  if (session.effective_ticket_rule) return session.effective_ticket_rule;
  if (session.effective_parent_checkin_policy === 'ticket_required') return 'all';
  return session.requires_ticket ? 'children' : 'open';
}

export function adultsNotCheckedIn(session: Session | null): boolean {
  if (!session) return false;
  return (
    session.adults_not_checked_in ?? session.effective_parent_checkin_policy === 'disabled'
  );
}

// The ticket the person actually holds that covers THIS session: an EventTicket for the
// session's event or a SessionTicket for that very session (Attendee.has_ticket_for).
// A ticket for another event or session does not count, whatever ticket_type says.
function heldTicketFor(item: TicketableApiItem, session: Session): TicketType {
  const details = item.ticket_details;
  if (!details) return 'none';
  if (details.event_tickets.some((t) => t.event === session.event)) return 'event';
  if (details.session_tickets.some((t) => t.session === session.id)) return 'session';
  return 'none';
}

export function childTicketAccess(child: TicketableApiItem, session: Session | null): TicketAccess {
  if (!session) return { ticket: (child.ticket_type as TicketType) || 'none' };

  const held = heldTicketFor(child, session);
  if (held !== 'none') return { ticket: held };

  // Children need a ticket on 'children' and 'all'; 'open' lets everyone in.
  if (ticketRuleOf(session) === 'open') return { ticket: 'event', exemption: 'not_required' };
  return { ticket: 'none' };
}

// Adults, in the server's order (parent_checkin_gate_error):
// 1. adults_not_checked_in beats everything, guardian-only adults included. The screen
//    shows this as a calm note, not as an error; 'none' only keeps the check-in button off.
// 2. Only rule 'all' asks adults for a ticket.
// 3. Under 'all', a guardian-only adult on a CONFIRMED registration for this event is exempt.
//    The server sends only confirmed ones in guardian_only_event_ids.
export function parentTicketAccess(
  parent: TicketableApiItem,
  session: Session | null
): TicketAccess {
  if (!session) return { ticket: (parent.ticket_type as TicketType) || 'none' };

  if (adultsNotCheckedIn(session)) return { ticket: 'none', notCheckedInHere: true };

  const held = heldTicketFor(parent, session);
  if (held !== 'none') return { ticket: held };

  if (ticketRuleOf(session) !== 'all') return { ticket: 'event', exemption: 'not_required' };
  if (parent.guardian_only_event_ids?.includes(session.event)) {
    return { ticket: 'event', exemption: 'guardian_only' };
  }
  return { ticket: 'none' };
}

export const effectiveTicketType = (child: TicketableApiItem, session: Session | null): TicketType =>
  childTicketAccess(child, session).ticket;

export const effectiveParentTicketType = (
  parent: TicketableApiItem,
  session: Session | null
): TicketType => parentTicketAccess(parent, session).ticket;

export function transformFamily(apiFamily: FamilyApiResponse, session: Session | null): Family {
  return {
    id: apiFamily.id,
    last_name: apiFamily.last_name,
    display_name: apiFamily.display_name,
    name: apiFamily.display_name,
    children: apiFamily.children.map((child) => {
      const access = childTicketAccess(child, session);
      const ticketType = access.ticket;
      return {
        id: child.id,
        first_name: child.first_name,
        last_name: child.last_name,
        name: `${child.first_name} ${child.last_name}`,
        ticket: ticketType,
        ticket_type: ticketType,
        ticketExemption: access.exemption,
        ticket_details: child.ticket_details,
        checkedIn: child.is_checked_in || false,
        family: child.family,
        birthdate: child.birthdate,
        allergies: child.allergies,
        notes: child.notes,
        has_safety_info: child.has_safety_info ?? false,
        health_consent_status: child.health_consent_status,
        qr_token: child.qr_token,
      };
    }),
    parents: apiFamily.parents.map((parent) => {
      const access = parentTicketAccess(parent, session);
      const ticketType = access.ticket;
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
        ticketExemption: access.exemption,
        notCheckedInHere: access.notCheckedInHere,
        ticket_details: parent.ticket_details ?? undefined,
        checkedIn: parent.is_checked_in || false,
        checkInRecordId: parent.active_checkin_id ?? undefined,
        family: parent.family,
        is_parent: true,
        allergies: parent.allergies,
        notes: parent.notes,
        has_safety_info: parent.has_safety_info ?? false,
        health_consent_status: parent.health_consent_status,
      };
    }),
    last_participation_date: apiFamily.last_participation_date,
    pending_payment: apiFamily.pending_payment ?? null,
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
