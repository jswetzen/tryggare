import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { db } from "~/server/db";
import { appRouter } from "~/server/api/root";
import { createTRPCContext } from "~/server/api/trpc";
import type { Session } from "next-auth";

describe("CheckIn Router", () => {
  let testAdminId: string;
  let testSession: Session;
  let testEventId: string;
  let testSessionId: string;
  let testChildId1: string;
  let testChildId2: string;

  beforeEach(async () => {
    // Create a test admin user
    const testAdmin = await db.adminUser.create({
      data: {
        username: "test-checkin-admin",
        passwordHash: "test-hash",
        name: "Test CheckIn Admin",
        isActive: true,
      },
    });
    testAdminId = testAdmin.id;

    // Create mock session
    testSession = {
      user: {
        id: testAdminId,
        username: "test-checkin-admin",
        name: "Test CheckIn Admin",
        email: null,
        image: null,
        isActive: true,
      },
      expires: new Date(Date.now() + 8 * 60 * 60 * 1000).toISOString(),
    };

    // Create test event
    const event = await db.event.create({
      data: {
        name: "Test CheckIn Event",
        startDate: new Date("2025-07-01"),
        endDate: new Date("2025-07-03"),
      },
    });
    testEventId = event.id;

    // Create active session
    const session = await db.session.create({
      data: {
        name: "Test CheckIn Session",
        startTime: new Date("2025-07-01T09:00:00"),
        endTime: new Date("2025-07-01T11:00:00"),
        requiresTicket: false,
        isActive: true,
        eventId: testEventId,
      },
    });
    testSessionId = session.id;

    // Create test family with children
    const family = await db.family.create({
      data: {
        parents: {
          create: [
            {
              name: "Test CheckIn Parent",
              relationshipType: "MOTHER",
            },
          ],
        },
        children: {
          create: [
            {
              firstName: "Test",
              lastName: "Child1",
              birthdate: new Date("2020-01-01"),
            },
            {
              firstName: "Test",
              lastName: "Child2",
              birthdate: new Date("2021-05-15"),
            },
          ],
        },
      },
      include: { children: true },
    });

    testChildId1 = family.children[0]!.id;
    testChildId2 = family.children[1]!.id;
  });

  afterEach(async () => {
    // Clean up test data
    await db.checkInRecord.deleteMany({
      where: {
        child: {
          family: {
            parents: {
              some: {
                name: {
                  startsWith: "Test ",
                },
              },
            },
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

    await db.child.deleteMany({
      where: {
        family: {
          parents: {
            some: {
              name: {
                startsWith: "Test ",
              },
            },
          },
        },
      },
    });

    await db.parent.deleteMany({
      where: {
        name: {
          startsWith: "Test ",
        },
      },
    });

    await db.family.deleteMany({
      where: {
        parents: {
          none: {},
        },
      },
    });

    await db.adminUser.deleteMany({
      where: {
        username: {
          startsWith: "test-checkin-",
        },
      },
    });
  });

  describe("perform", () => {
    it("should check in a single child", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.checkIn.perform({
        childIds: [testChildId1],
        sessionId: testSessionId,
      });

      expect(result.success).toBe(true);
      expect(result.count).toBe(1);
      expect(result.checkIns).toHaveLength(1);
      expect(result.checkIns[0]?.childId).toBe(testChildId1);
      expect(result.checkIns[0]?.qrToken).toBeDefined();
    });

    it("should check in multiple children in batch", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.checkIn.perform({
        childIds: [testChildId1, testChildId2],
        sessionId: testSessionId,
      });

      expect(result.success).toBe(true);
      expect(result.count).toBe(2);
      expect(result.checkIns).toHaveLength(2);
    });

    it("should generate QR token on first check-in", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Verify child has no QR token
      const childBefore = await db.child.findUnique({ where: { id: testChildId1 } });
      expect(childBefore?.qrToken).toBeNull();

      const result = await caller.checkIn.perform({
        childIds: [testChildId1],
        sessionId: testSessionId,
      });

      // Verify QR token was generated
      expect(result.checkIns[0]?.qrToken).toBeDefined();
      expect(result.checkIns[0]?.qrToken).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i);

      // Verify in database
      const childAfter = await db.child.findUnique({ where: { id: testChildId1 } });
      expect(childAfter?.qrToken).toBe(result.checkIns[0]?.qrToken);
    });

    it("should return existing QR token if already generated", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Generate QR token first
      const { qrToken } = await caller.child.generateQrToken({ childId: testChildId1 });

      // Check in child
      const result = await caller.checkIn.perform({
        childIds: [testChildId1],
        sessionId: testSessionId,
      });

      expect(result.checkIns[0]?.qrToken).toBe(qrToken);
    });

    it("should prevent duplicate check-in to same session", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // First check-in
      await caller.checkIn.perform({
        childIds: [testChildId1],
        sessionId: testSessionId,
      });

      // Attempt duplicate check-in
      await expect(
        caller.checkIn.perform({
          childIds: [testChildId1],
          sessionId: testSessionId,
        })
      ).rejects.toThrow("Check-in validation failed");
    });

    it("should prevent check-in to different session when already checked in", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Create second session
      const session2 = await db.session.create({
        data: {
          name: "Test CheckIn Session 2",
          startTime: new Date("2025-07-01T14:00:00"),
          endTime: new Date("2025-07-01T16:00:00"),
          requiresTicket: false,
          isActive: true,
          eventId: testEventId,
        },
      });

      // Check in to first session
      await caller.checkIn.perform({
        childIds: [testChildId1],
        sessionId: testSessionId,
      });

      // Attempt check-in to second session
      await expect(
        caller.checkIn.perform({
          childIds: [testChildId1],
          sessionId: session2.id,
        })
      ).rejects.toThrow("Check-in validation failed");
    });

    it("should reject check-in to inactive session", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Create inactive session
      const inactiveSession = await db.session.create({
        data: {
          name: "Test Inactive Session",
          startTime: new Date("2025-07-02T09:00:00"),
          endTime: new Date("2025-07-02T11:00:00"),
          requiresTicket: false,
          isActive: false,
          eventId: testEventId,
        },
      });

      await expect(
        caller.checkIn.perform({
          childIds: [testChildId1],
          sessionId: inactiveSession.id,
        })
      ).rejects.toThrow("Cannot check in to an inactive session");
    });

    it("should reject check-in for non-existent child", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      await expect(
        caller.checkIn.perform({
          childIds: ["non-existent-child-id"],
          sessionId: testSessionId,
        })
      ).rejects.toThrow("Check-in validation failed");
    });

    it("should reject check-in for non-existent session", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      await expect(
        caller.checkIn.perform({
          childIds: [testChildId1],
          sessionId: "non-existent-session-id",
        })
      ).rejects.toThrow("Session not found");
    });

    it("should require at least one child", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      await expect(
        caller.checkIn.perform({
          childIds: [],
          sessionId: testSessionId,
        })
      ).rejects.toThrow();
    });

    it("should update lastParticipationDate on check-in", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Get child with family before check-in
      const childBefore = await db.child.findUnique({
        where: { id: testChildId1 },
        include: { family: { include: { parents: true } } },
      });

      expect(childBefore?.lastParticipationDate).toBeNull();
      expect(childBefore?.family.lastParticipationDate).toBeNull();

      // Check in
      await caller.checkIn.perform({
        childIds: [testChildId1],
        sessionId: testSessionId,
      });

      // Verify dates updated
      const childAfter = await db.child.findUnique({
        where: { id: testChildId1 },
        include: { family: { include: { parents: true } } },
      });

      expect(childAfter?.lastParticipationDate).toBeDefined();
      expect(childAfter?.family.lastParticipationDate).toBeDefined();
      expect(childAfter?.family.parents[0]?.lastParticipationDate).toBeDefined();
    });
  });

  describe("validate", () => {
    it("should validate successful check-in without performing it", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.checkIn.validate({
        childId: testChildId1,
        sessionId: testSessionId,
      });

      expect(result.valid).toBe(true);
      expect(result.reason).toBeUndefined();

      // Verify child was not actually checked in
      const checkIn = await db.checkInRecord.findFirst({
        where: { childId: testChildId1 },
      });
      expect(checkIn).toBeNull();
    });

    it("should validate and report when child already checked in", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Check in child
      await caller.checkIn.perform({
        childIds: [testChildId1],
        sessionId: testSessionId,
      });

      // Validate
      const result = await caller.checkIn.validate({
        childId: testChildId1,
        sessionId: testSessionId,
      });

      expect(result.valid).toBe(false);
      expect(result.reason).toContain("Already checked into");
    });

    it("should validate and report inactive session", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Create inactive session
      const inactiveSession = await db.session.create({
        data: {
          name: "Test Validate Inactive",
          startTime: new Date("2025-07-02T09:00:00"),
          endTime: new Date("2025-07-02T11:00:00"),
          requiresTicket: false,
          isActive: false,
          eventId: testEventId,
        },
      });

      const result = await caller.checkIn.validate({
        childId: testChildId1,
        sessionId: inactiveSession.id,
      });

      expect(result.valid).toBe(false);
      expect(result.reason).toContain("Session is not active");
    });

    it("should validate and report non-existent child", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.checkIn.validate({
        childId: "non-existent-id",
        sessionId: testSessionId,
      });

      expect(result.valid).toBe(false);
      expect(result.reason).toContain("not found");
    });
  });

  describe("getCurrentCheckIns", () => {
    beforeEach(async () => {
      // Check in test children
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      await caller.checkIn.perform({
        childIds: [testChildId1, testChildId2],
        sessionId: testSessionId,
      });
    });

    it("should return all currently checked-in children", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.checkIn.getCurrentCheckIns({});

      expect(result.length).toBeGreaterThanOrEqual(2);
      expect(result.some((c) => c.childId === testChildId1)).toBe(true);
      expect(result.some((c) => c.childId === testChildId2)).toBe(true);
    });

    it("should filter by session ID", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Create second session and check in another child
      const session2 = await db.session.create({
        data: {
          name: "Test CheckIn Session 2",
          startTime: new Date("2025-07-01T14:00:00"),
          endTime: new Date("2025-07-01T16:00:00"),
          requiresTicket: false,
          isActive: true,
          eventId: testEventId,
        },
      });

      // Create third child
      const family2 = await db.family.create({
        data: {
          parents: {
            create: [{ name: "Test Parent 2", relationshipType: "FATHER" }],
          },
          children: {
            create: [
              {
                firstName: "Test",
                lastName: "Child3",
                birthdate: new Date("2022-01-01"),
              },
            ],
          },
        },
        include: { children: true },
      });

      await db.checkInRecord.create({
        data: {
          childId: family2.children[0]!.id,
          sessionId: session2.id,
          checkInStaffId: testAdminId,
        },
      });

      // Filter by first session
      const result = await caller.checkIn.getCurrentCheckIns({
        sessionId: testSessionId,
      });

      expect(result.every((c) => c.sessionId === testSessionId)).toBe(true);
      expect(result.some((c) => c.childId === family2.children[0]!.id)).toBe(false);
    });

    it("should include child, family, and parent details", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.checkIn.getCurrentCheckIns({});

      const checkIn = result.find((c) => c.childId === testChildId1);
      expect(checkIn).toBeDefined();
      expect(checkIn?.child).toBeDefined();
      expect(checkIn?.child.family).toBeDefined();
      expect(checkIn?.child.family.parents).toBeDefined();
    });

    it("should include session and staff details", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.checkIn.getCurrentCheckIns({});

      const checkIn = result.find((c) => c.childId === testChildId1);
      expect(checkIn?.session).toBeDefined();
      expect(checkIn?.session.name).toBe("Test CheckIn Session");
      expect(checkIn?.checkInStaff).toBeDefined();
      expect(checkIn?.checkInStaff.name).toBe("Test CheckIn Admin");
    });

    it("should not include checked-out children", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Check out one child
      await caller.checkOut.perform({
        childIds: [testChildId1],
      });

      const result = await caller.checkIn.getCurrentCheckIns({});

      expect(result.some((c) => c.childId === testChildId1)).toBe(false);
      expect(result.some((c) => c.childId === testChildId2)).toBe(true);
    });
  });
});
