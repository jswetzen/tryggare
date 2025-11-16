/**
 * Validation helper functions for check-in/check-out business logic
 */

import { db } from "~/server/db";

/**
 * Check if a child is currently checked in to any session
 * @param childId - The ID of the child
 * @returns The session ID if checked in, null otherwise
 */
export async function isChildCheckedIn(
  childId: string
): Promise<string | null> {
  const currentCheckIn = await db.checkInRecord.findFirst({
    where: {
      childId,
      checkOutTime: null, // Not checked out = currently checked in
    },
    select: {
      sessionId: true,
    },
  });

  return currentCheckIn?.sessionId ?? null;
}

/**
 * Get the current check-in record for a child (if any)
 * @param childId - The ID of the child
 * @returns The check-in record with session details, or null
 */
export async function getCurrentCheckIn(childId: string) {
  const currentCheckIn = await db.checkInRecord.findFirst({
    where: {
      childId,
      checkOutTime: null,
    },
    include: {
      session: {
        select: {
          id: true,
          name: true,
          startTime: true,
          endTime: true,
          requiresTicket: true,
        },
      },
    },
  });

  return currentCheckIn;
}

/**
 * Validate if a child has the required ticket/pass for a session
 * @param childId - The ID of the child
 * @param sessionId - The ID of the session
 * @returns true if validation passes, false otherwise
 */
export async function validateTicket(
  childId: string,
  sessionId: string
): Promise<{ valid: boolean; reason?: string }> {
  // Get the session to check if it requires a ticket
  const session = await db.session.findUnique({
    where: { id: sessionId },
    select: {
      requiresTicket: true,
      eventId: true,
    },
  });

  if (!session) {
    return { valid: false, reason: "Session not found" };
  }

  // If session doesn't require a ticket, always valid
  if (!session.requiresTicket) {
    return { valid: true };
  }

  // Check for tickets/passes
  const tickets = await db.ticket.findMany({
    where: {
      childId,
    },
    select: {
      id: true,
      eventId: true,
      sessionId: true,
    },
  });

  if (tickets.length === 0) {
    return {
      valid: false,
      reason: "This session requires a ticket, but child has no tickets",
    };
  }

  const eventPasses = tickets.filter((ticket) => ticket.eventId !== null);
  const sessionTickets = tickets.filter((ticket) => ticket.sessionId !== null);

  const hasMatchingEventPass = eventPasses.some(
    (ticket) => ticket.eventId === session.eventId
  );
  if (hasMatchingEventPass) {
    return { valid: true };
  }

  const hasMatchingSessionTicket = sessionTickets.some(
    (ticket) => ticket.sessionId === sessionId
  );
  if (hasMatchingSessionTicket) {
    return { valid: true };
  }

  if (eventPasses.length > 0) {
    return {
      valid: false,
      reason: "Child has event pass(es), but they are for a different event",
    };
  }

  if (sessionTickets.length > 0) {
    return {
      valid: false,
      reason: "Child has session ticket(s), but not for this session",
    };
  }

  return {
    valid: false,
    reason: "Child does not have a valid ticket or pass for this session",
  };
}

/**
 * Get the count of currently active sessions
 * @returns The number of active sessions
 */
export async function getActiveSessionCount(): Promise<number> {
  const count = await db.session.count({
    where: {
      isActive: true,
    },
  });

  return count;
}

/**
 * Get all currently active sessions
 * @returns Array of active sessions with event details and current check-in count
 */
export async function getActiveSessions() {
  const sessions = await db.session.findMany({
    where: {
      isActive: true,
    },
    include: {
      event: {
        select: {
          id: true,
          name: true,
          startDate: true,
          endDate: true,
        },
      },
      checkInRecords: {
        where: {
          checkOutTime: null, // Only get currently checked-in children
        },
        select: {
          id: true,
        },
      },
    },
    orderBy: {
      startTime: "asc",
    },
  });

  // Map to include currentCheckInCount
  return sessions.map((session) => ({
    ...session,
    currentCheckInCount: session.checkInRecords.length,
    checkInRecords: undefined, // Remove checkInRecords array from response for cleaner API
  }));
}

/**
 * Validate that a child can be checked in to a specific session
 * Performs all necessary validations
 * @param childId - The ID of the child
 * @param sessionId - The ID of the session
 * @returns Validation result with details
 */
export async function validateCheckIn(
  childId: string,
  sessionId: string
): Promise<{ valid: boolean; reason?: string; currentSession?: string }> {
  // Check if child is already checked in somewhere
  const currentCheckIn = await getCurrentCheckIn(childId);
  if (currentCheckIn) {
    return {
      valid: false,
      reason: `Child is already checked into ${currentCheckIn.session.name}`,
      currentSession: currentCheckIn.session.name,
    };
  }

  // Check if session exists and is active
  const session = await db.session.findUnique({
    where: { id: sessionId },
    select: {
      id: true,
      name: true,
      isActive: true,
    },
  });

  if (!session) {
    return { valid: false, reason: "Session not found" };
  }

  if (!session.isActive) {
    return {
      valid: false,
      reason: `Session "${session.name}" is not currently active`,
    };
  }

  // Validate ticket/pass
  const ticketValidation = await validateTicket(childId, sessionId);
  if (!ticketValidation.valid) {
    return ticketValidation;
  }

  return { valid: true };
}

/**
 * Validate that a child can be checked out
 * @param childId - The ID of the child
 * @returns Validation result
 */
export async function validateCheckOut(
  childId: string
): Promise<{ valid: boolean; reason?: string; checkInRecordId?: string }> {
  const currentCheckIn = await db.checkInRecord.findFirst({
    where: {
      childId,
      checkOutTime: null,
    },
    select: {
      id: true,
      session: {
        select: {
          name: true,
        },
      },
    },
  });

  if (!currentCheckIn) {
    return {
      valid: false,
      reason: "Child is not currently checked in",
    };
  }

  return {
    valid: true,
    checkInRecordId: currentCheckIn.id,
  };
}
