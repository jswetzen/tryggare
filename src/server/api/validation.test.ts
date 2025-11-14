import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { db } from "~/server/db";
import {
  isChildCheckedIn,
  getCurrentCheckIn,
  validateTicket,
  getActiveSessionCount,
  getActiveSessions,
  validateCheckIn,
  validateCheckOut,
} from "./validation";

describe("Validation Helper Functions", () => {
  let testAdminId: string;
  let testEventId: string;
  let testSessionId: string;
  let testChildId: string;
  let testFamilyId: string;

  beforeEach(async () => {
    // Create test admin
    const admin = await db.adminUser.create({
      data: {
        username: "test-validation-admin",
        passwordHash: "hash",
        name: "Test Validation Admin",
        isActive: true,
      },
    });
    testAdminId = admin.id;

    // Create test event
    const event = await db.event.create({
      data: {
        name: "Test Validation Event",
        startDate: new Date("2025-07-01"),
        endDate: new Date("2025-07-03"),
      },
    });
    testEventId = event.id;

    // Create test session
    const session = await db.session.create({
      data: {
        name: "Test Validation Session",
        startTime: new Date("2025-07-01T09:00:00"),
        endTime: new Date("2025-07-01T11:00:00"),
        requiresTicket: false,
        isActive: true,
        eventId: testEventId,
      },
    });
    testSessionId = session.id;

    // Create test family and child
    const family = await db.family.create({
      data: {
        children: {
          create: {
            firstName: "Test",
            lastName: "ValidationChild",
            birthdate: new Date("2020-01-01"),
          },
        },
      },
      include: {
        children: true,
      },
    });
    testFamilyId = family.id;
    testChildId = family.children[0]!.id;
  });

  afterEach(async () => {
    // Clean up - order matters due to foreign key constraints
    // Delete check-in records first (references child, session, admin)
    await db.checkInRecord.deleteMany({
      where: { childId: testChildId },
    });

    // Delete tickets (references child and session)
    await db.ticket.deleteMany({
      where: { childId: testChildId },
    });

    // Delete children (references family)
    await db.child.deleteMany({
      where: { familyId: testFamilyId },
    });

    // Delete family
    await db.family.deleteMany({
      where: { id: testFamilyId },
    });

    // Delete sessions (references event)
    await db.session.deleteMany({
      where: { eventId: testEventId },
    });

    // Delete event
    await db.event.deleteMany({
      where: { id: testEventId },
    });

    // Delete admin user last
    await db.adminUser.deleteMany({
      where: { id: testAdminId },
    });
  });

  describe("isChildCheckedIn", () => {
    it("should return null when child is not checked in", async () => {
      const result = await isChildCheckedIn(testChildId);
      expect(result).toBeNull();
    });

    it("should return session ID when child is checked in", async () => {
      // Check in the child
      await db.checkInRecord.create({
        data: {
          childId: testChildId,
          sessionId: testSessionId,
          checkInStaffId: testAdminId,
        },
      });

      const result = await isChildCheckedIn(testChildId);
      expect(result).toBe(testSessionId);
    });

    it("should return null when child was checked in but already checked out", async () => {
      // Check in and check out
      await db.checkInRecord.create({
        data: {
          childId: testChildId,
          sessionId: testSessionId,
          checkInStaffId: testAdminId,
          checkOutTime: new Date(),
          checkOutStaffId: testAdminId,
        },
      });

      const result = await isChildCheckedIn(testChildId);
      expect(result).toBeNull();
    });
  });

  describe("getCurrentCheckIn", () => {
    it("should return null when child is not checked in", async () => {
      const result = await getCurrentCheckIn(testChildId);
      expect(result).toBeNull();
    });

    it("should return check-in record with session when child is checked in", async () => {
      await db.checkInRecord.create({
        data: {
          childId: testChildId,
          sessionId: testSessionId,
          checkInStaffId: testAdminId,
        },
      });

      const result = await getCurrentCheckIn(testChildId);

      expect(result).toBeDefined();
      expect(result?.childId).toBe(testChildId);
      expect(result?.sessionId).toBe(testSessionId);
      expect(result?.session).toBeDefined();
      expect(result?.session.name).toBe("Test Validation Session");
    });
  });

  describe("validateTicket", () => {
    it("should return valid for sessions that don't require tickets", async () => {
      const result = await validateTicket(testChildId, testSessionId);

      expect(result.valid).toBe(true);
    });

    it("should return invalid for non-existent session", async () => {
      const result = await validateTicket(testChildId, "non-existent-session");

      expect(result.valid).toBe(false);
      expect(result.reason).toContain("Session not found");
    });

    it("should return invalid when session requires ticket but child has none", async () => {
      // Create session that requires ticket
      const ticketedSession = await db.session.create({
        data: {
          name: "Ticketed Session",
          startTime: new Date("2025-07-01T14:00:00"),
          endTime: new Date("2025-07-01T16:00:00"),
          requiresTicket: true,
          isActive: true,
          eventId: testEventId,
        },
      });

      const result = await validateTicket(testChildId, ticketedSession.id);

      expect(result.valid).toBe(false);
      expect(result.reason).toContain("no tickets");
    });

    it("should return valid when child has event pass", async () => {
      // Create ticketed session
      const ticketedSession = await db.session.create({
        data: {
          name: "Ticketed Session 2",
          startTime: new Date("2025-07-01T14:00:00"),
          endTime: new Date("2025-07-01T16:00:00"),
          requiresTicket: true,
          isActive: true,
          eventId: testEventId,
        },
      });

      // Give child an event pass (sessionId is null)
      await db.ticket.create({
        data: {
          type: "EVENT_PASS",
          childId: testChildId,
          sessionId: null,
        },
      });

      const result = await validateTicket(testChildId, ticketedSession.id);

      expect(result.valid).toBe(true);
    });

    it("should return valid when child has specific session ticket", async () => {
      // Create ticketed session
      const ticketedSession = await db.session.create({
        data: {
          name: "Ticketed Session 3",
          startTime: new Date("2025-07-01T14:00:00"),
          endTime: new Date("2025-07-01T16:00:00"),
          requiresTicket: true,
          isActive: true,
          eventId: testEventId,
        },
      });

      // Give child a specific session ticket
      await db.ticket.create({
        data: {
          type: "SESSION_TICKET",
          childId: testChildId,
          sessionId: ticketedSession.id,
        },
      });

      const result = await validateTicket(testChildId, ticketedSession.id);

      expect(result.valid).toBe(true);
    });
  });

  describe("getActiveSessionCount", () => {
    it("should return count of active sessions", async () => {
      const initialCount = await getActiveSessionCount();

      // Create another active session
      await db.session.create({
        data: {
          name: "Another Active Session",
          startTime: new Date("2025-07-01T14:00:00"),
          endTime: new Date("2025-07-01T16:00:00"),
          requiresTicket: false,
          isActive: true,
          eventId: testEventId,
        },
      });

      const finalCount = await getActiveSessionCount();

      expect(finalCount).toBe(initialCount + 1);
    });

    it("should not count inactive sessions", async () => {
      const initialCount = await getActiveSessionCount();

      // Create inactive session
      await db.session.create({
        data: {
          name: "Inactive Session",
          startTime: new Date("2025-07-01T19:00:00"),
          endTime: new Date("2025-07-01T21:00:00"),
          requiresTicket: false,
          isActive: false,
          eventId: testEventId,
        },
      });

      const finalCount = await getActiveSessionCount();

      expect(finalCount).toBe(initialCount);
    });
  });

  describe("getActiveSessions", () => {
    it("should return all active sessions with event details", async () => {
      const result = await getActiveSessions();

      expect(Array.isArray(result)).toBe(true);
      expect(result.length).toBeGreaterThan(0);

      const testSession = result.find((s) => s.name === "Test Validation Session");
      expect(testSession).toBeDefined();
      expect(testSession?.event).toBeDefined();
      expect(testSession?.event.name).toBe("Test Validation Event");
    });
  });

  describe("validateCheckIn", () => {
    it("should return valid for valid check-in", async () => {
      const result = await validateCheckIn(testChildId, testSessionId);

      expect(result.valid).toBe(true);
    });

    it("should return invalid when child is already checked in", async () => {
      // Check in the child
      await db.checkInRecord.create({
        data: {
          childId: testChildId,
          sessionId: testSessionId,
          checkInStaffId: testAdminId,
        },
      });

      // Try to check in again to a different session
      const anotherSession = await db.session.create({
        data: {
          name: "Another Session",
          startTime: new Date("2025-07-01T14:00:00"),
          endTime: new Date("2025-07-01T16:00:00"),
          requiresTicket: false,
          isActive: true,
          eventId: testEventId,
        },
      });

      const result = await validateCheckIn(testChildId, anotherSession.id);

      expect(result.valid).toBe(false);
      expect(result.reason).toContain("already checked into");
      expect(result.currentSession).toBe("Test Validation Session");
    });

    it("should return invalid for non-existent session", async () => {
      const result = await validateCheckIn(testChildId, "non-existent-session");

      expect(result.valid).toBe(false);
      expect(result.reason).toContain("Session not found");
    });

    it("should return invalid for inactive session", async () => {
      const inactiveSession = await db.session.create({
        data: {
          name: "Inactive Check-in Session",
          startTime: new Date("2025-07-01T14:00:00"),
          endTime: new Date("2025-07-01T16:00:00"),
          requiresTicket: false,
          isActive: false,
          eventId: testEventId,
        },
      });

      const result = await validateCheckIn(testChildId, inactiveSession.id);

      expect(result.valid).toBe(false);
      expect(result.reason).toContain("not currently active");
    });
  });

  describe("validateCheckOut", () => {
    it("should return invalid when child is not checked in", async () => {
      const result = await validateCheckOut(testChildId);

      expect(result.valid).toBe(false);
      expect(result.reason).toContain("not currently checked in");
    });

    it("should return valid with check-in record ID when child is checked in", async () => {
      const checkIn = await db.checkInRecord.create({
        data: {
          childId: testChildId,
          sessionId: testSessionId,
          checkInStaffId: testAdminId,
        },
      });

      const result = await validateCheckOut(testChildId);

      expect(result.valid).toBe(true);
      expect(result.checkInRecordId).toBe(checkIn.id);
    });
  });
});
