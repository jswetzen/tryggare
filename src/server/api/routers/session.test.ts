import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { db } from "~/server/db";
import { appRouter } from "~/server/api/root";
import { createTRPCContext } from "~/server/api/trpc";
import type { Session } from "next-auth";

describe("Session Router", () => {
  let testAdminId: string;
  let testEventId: string;
  let testSession: Session;

  beforeEach(async () => {
    // Create a test admin user
    const testAdmin = await db.adminUser.create({
      data: {
        username: "test-session-admin",
        passwordHash: "test-hash",
        name: "Test Session Admin",
        isActive: true,
      },
    });
    testAdminId = testAdmin.id;

    // Create a test event
    const testEvent = await db.event.create({
      data: {
        name: "Test Event",
        startDate: new Date("2025-07-01"),
        endDate: new Date("2025-07-03"),
      },
    });
    testEventId = testEvent.id;

    // Create mock session
    testSession = {
      user: {
        id: testAdminId,
        username: "test-session-admin",
        name: "Test Session Admin",
        email: null,
        image: null,
        isActive: true,
      },
      expires: new Date(Date.now() + 8 * 60 * 60 * 1000).toISOString(),
    };
  });

  afterEach(async () => {
    // Clean up test data
    await db.checkInRecord.deleteMany({
      where: {
        session: {
          name: {
            startsWith: "Test ",
          },
        },
      },
    });

    await db.session.deleteMany({
      where: {
        name: {
          startsWith: "Test ",
        },
      },
    });

    await db.event.deleteMany({
      where: {
        name: {
          startsWith: "Test ",
        },
      },
    });

    await db.adminUser.deleteMany({
      where: {
        username: {
          startsWith: "test-session-",
        },
      },
    });
  });

  describe("create", () => {
    it("should create a new session", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const startTime = new Date("2025-07-01T09:00:00");
      const endTime = new Date("2025-07-01T11:00:00");

      const result = await caller.session.create({
        name: "Test Morning Session",
        startTime,
        endTime,
        requiresTicket: false,
        eventId: testEventId,
      });

      expect(result).toBeDefined();
      expect(result.name).toBe("Test Morning Session");
      expect(result.isActive).toBe(false); // Default is inactive
      expect(result.requiresTicket).toBe(false);
      expect(result.event.id).toBe(testEventId);
    });

    it("should reject session with end time before start time", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const startTime = new Date("2025-07-01T11:00:00");
      const endTime = new Date("2025-07-01T09:00:00");

      await expect(
        caller.session.create({
          name: "Test Invalid Session",
          startTime,
          endTime,
          requiresTicket: false,
          eventId: testEventId,
        })
      ).rejects.toThrow("End time must be after start time");
    });

    it("should reject session with non-existent event", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      await expect(
        caller.session.create({
          name: "Test Invalid Event Session",
          startTime: new Date("2025-07-01T09:00:00"),
          endTime: new Date("2025-07-01T11:00:00"),
          requiresTicket: false,
          eventId: "non-existent-event-id",
        })
      ).rejects.toThrow("Event not found");
    });
  });

  describe("list", () => {
    it("should list all sessions", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Create test sessions
      await db.session.createMany({
        data: [
          {
            name: "Test Session 1",
            startTime: new Date("2025-07-01T09:00:00"),
            endTime: new Date("2025-07-01T11:00:00"),
            requiresTicket: false,
            isActive: true,
            eventId: testEventId,
          },
          {
            name: "Test Session 2",
            startTime: new Date("2025-07-01T14:00:00"),
            endTime: new Date("2025-07-01T16:00:00"),
            requiresTicket: true,
            isActive: false,
            eventId: testEventId,
          },
        ],
      });

      const result = await caller.session.list();

      expect(result.length).toBeGreaterThanOrEqual(2);
      expect(result.find((s) => s.name === "Test Session 1")).toBeDefined();
      expect(result.find((s) => s.name === "Test Session 2")).toBeDefined();
    });

    it("should filter sessions by event ID", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Create another event
      const otherEvent = await db.event.create({
        data: {
          name: "Test Other Event",
          startDate: new Date("2025-08-01"),
          endDate: new Date("2025-08-02"),
        },
      });

      await db.session.create({
        data: {
          name: "Test Session in Other Event",
          startTime: new Date("2025-08-01T09:00:00"),
          endTime: new Date("2025-08-01T11:00:00"),
          requiresTicket: false,
          isActive: false,
          eventId: otherEvent.id,
        },
      });

      const result = await caller.session.list({ eventId: testEventId });

      expect(result.every((s) => s.eventId === testEventId)).toBe(true);
      expect(result.find((s) => s.name === "Test Session in Other Event")).toBeUndefined();
    });

    it("should filter sessions by active status", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      await db.session.createMany({
        data: [
          {
            name: "Test Active Session",
            startTime: new Date("2025-07-01T09:00:00"),
            endTime: new Date("2025-07-01T11:00:00"),
            requiresTicket: false,
            isActive: true,
            eventId: testEventId,
          },
          {
            name: "Test Inactive Session",
            startTime: new Date("2025-07-01T14:00:00"),
            endTime: new Date("2025-07-01T16:00:00"),
            requiresTicket: false,
            isActive: false,
            eventId: testEventId,
          },
        ],
      });

      const result = await caller.session.list({ isActive: true });

      expect(result.every((s) => s.isActive === true)).toBe(true);
      expect(result.find((s) => s.name === "Test Inactive Session")).toBeUndefined();
    });
  });

  describe("getActive", () => {
    it("should return only active sessions", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      await db.session.createMany({
        data: [
          {
            name: "Test Active 1",
            startTime: new Date("2025-07-01T09:00:00"),
            endTime: new Date("2025-07-01T11:00:00"),
            requiresTicket: false,
            isActive: true,
            eventId: testEventId,
          },
          {
            name: "Test Active 2",
            startTime: new Date("2025-07-01T14:00:00"),
            endTime: new Date("2025-07-01T16:00:00"),
            requiresTicket: false,
            isActive: true,
            eventId: testEventId,
          },
          {
            name: "Test Inactive",
            startTime: new Date("2025-07-01T19:00:00"),
            endTime: new Date("2025-07-01T21:00:00"),
            requiresTicket: false,
            isActive: false,
            eventId: testEventId,
          },
        ],
      });

      const result = await caller.session.getActive();

      expect(result.length).toBeGreaterThanOrEqual(2);
      expect(result.every((s) => s.isActive === true)).toBe(true);
      expect(result.find((s) => s.name === "Test Active 1")).toBeDefined();
      expect(result.find((s) => s.name === "Test Inactive")).toBeUndefined();
    });
  });

  describe("getActiveCount", () => {
    it("should return count of active sessions", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Get initial count
      const initialCount = await caller.session.getActiveCount();

      // Create active sessions
      await db.session.createMany({
        data: [
          {
            name: "Test Count Active 1",
            startTime: new Date("2025-07-01T09:00:00"),
            endTime: new Date("2025-07-01T11:00:00"),
            requiresTicket: false,
            isActive: true,
            eventId: testEventId,
          },
          {
            name: "Test Count Active 2",
            startTime: new Date("2025-07-01T14:00:00"),
            endTime: new Date("2025-07-01T16:00:00"),
            requiresTicket: false,
            isActive: true,
            eventId: testEventId,
          },
        ],
      });

      const finalCount = await caller.session.getActiveCount();

      expect(finalCount).toBe(initialCount + 2);
    });
  });

  describe("activate and deactivate", () => {
    it("should activate a session", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const session = await db.session.create({
        data: {
          name: "Test Activate Session",
          startTime: new Date("2025-07-01T09:00:00"),
          endTime: new Date("2025-07-01T11:00:00"),
          requiresTicket: false,
          isActive: false,
          eventId: testEventId,
        },
      });

      const result = await caller.session.activate({ id: session.id });

      expect(result.isActive).toBe(true);
    });

    it("should deactivate a session", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const session = await db.session.create({
        data: {
          name: "Test Deactivate Session",
          startTime: new Date("2025-07-01T09:00:00"),
          endTime: new Date("2025-07-01T11:00:00"),
          requiresTicket: false,
          isActive: true,
          eventId: testEventId,
        },
      });

      const result = await caller.session.deactivate({ id: session.id });

      expect(result.isActive).toBe(false);
    });
  });

  describe("update", () => {
    it("should update session details", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const session = await db.session.create({
        data: {
          name: "Test Update Session",
          startTime: new Date("2025-07-01T09:00:00"),
          endTime: new Date("2025-07-01T11:00:00"),
          requiresTicket: false,
          isActive: false,
          eventId: testEventId,
        },
      });

      const result = await caller.session.update({
        id: session.id,
        name: "Updated Session Name",
        requiresTicket: true,
      });

      expect(result.name).toBe("Updated Session Name");
      expect(result.requiresTicket).toBe(true);
    });

    it("should reject invalid time updates", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const session = await db.session.create({
        data: {
          name: "Test Invalid Update Session",
          startTime: new Date("2025-07-01T09:00:00"),
          endTime: new Date("2025-07-01T11:00:00"),
          requiresTicket: false,
          isActive: false,
          eventId: testEventId,
        },
      });

      await expect(
        caller.session.update({
          id: session.id,
          startTime: new Date("2025-07-01T11:00:00"),
          endTime: new Date("2025-07-01T09:00:00"),
        })
      ).rejects.toThrow("End time must be after start time");
    });
  });

  describe("delete", () => {
    it("should delete session with no check-ins", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const session = await db.session.create({
        data: {
          name: "Test Delete Session",
          startTime: new Date("2025-07-01T09:00:00"),
          endTime: new Date("2025-07-01T11:00:00"),
          requiresTicket: false,
          isActive: false,
          eventId: testEventId,
        },
      });

      const result = await caller.session.delete({ id: session.id });

      expect(result.success).toBe(true);

      // Verify deletion
      const deletedSession = await db.session.findUnique({
        where: { id: session.id },
      });
      expect(deletedSession).toBeNull();
    });

    it("should prevent deletion of session with check-ins", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Create session with a check-in
      const session = await db.session.create({
        data: {
          name: "Test Session With Check-ins",
          startTime: new Date("2025-07-01T09:00:00"),
          endTime: new Date("2025-07-01T11:00:00"),
          requiresTicket: false,
          isActive: false,
          eventId: testEventId,
        },
      });

      // Create a family and child
      const family = await db.family.create({
        data: {
          children: {
            create: {
              firstName: "Test",
              lastName: "Child",
              birthdate: new Date("2020-01-01"),
            },
          },
        },
        include: {
          children: true,
        },
      });

      // Create check-in
      await db.checkInRecord.create({
        data: {
          childId: family.children[0]!.id,
          sessionId: session.id,
          checkInStaffId: testAdminId,
        },
      });

      await expect(
        caller.session.delete({ id: session.id })
      ).rejects.toThrow("Cannot delete session with");
    });
  });
});
