// A person can hold several session tickets (an older one, plus one granted at the door).
// The row names the one for the session the desk is working: that is the one the door
// volunteer just granted or is about to rely on. With no active session, or no ticket
// for it, fall back to the first so the row still says something.
export type SessionTicketRef = { session: string; session_name: string };

export function sessionTicketName(
  sessionTickets: SessionTicketRef[] | undefined | null,
  activeSessionId: string | null | undefined
): string | undefined {
  if (!sessionTickets?.length) return undefined;
  const match = activeSessionId
    ? sessionTickets.find((t) => t.session === activeSessionId)
    : undefined;
  return (match ?? sessionTickets[0]).session_name;
}

// A row whose ticket type is 'session' holds a ticket for the desk's session (mergeFamilies), or
// was just granted one (the page's local update does not add it to ticket_details), so it names
// the active session. Only with no active session does it fall back to the first ticket.
export function sessionRowLabel(
  sessionTickets: SessionTicketRef[] | undefined | null,
  activeSessionId: string | null | undefined,
  activeSessionName: string | null | undefined
): string | undefined {
  if (activeSessionId && activeSessionName) return activeSessionName;
  return sessionTicketName(sessionTickets, activeSessionId);
}

// The page's local update after a successful door grant: flips the row's ticket type.
export function withGrantedTicket<T extends object>(person: T, ticketType: 'event' | 'session'): T {
  return { ...person, ticket: ticketType, ticket_type: ticketType, ticketExemption: undefined };
}
