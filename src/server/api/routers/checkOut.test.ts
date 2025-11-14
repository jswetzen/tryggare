import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { db } from "~/server/db";
import { appRouter } from "~/server/api/root";
import { createTRPCContext } from "~/server/api/trpc";
import type { Session } from "next-auth";

describe("CheckOut Router", () => {
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
        username: "test-checkout-admin",
        passwordHash: "test-hash",
        name: "Test CheckOut Admin",
        isActive: true,
      },
    });
    testAdminId = testAdmin.id;

    // Create mock session
    testSession = {
      user: {
        id: testAdminId,
        username: "test-checkout-admin",
        name: "Test CheckOut Admin",
        email: null,
        image: null,
        isActive: true,
      },
      expires: new Date(Date.now() + 8 * 60 * 60 * 1000).toISOString(),
    };

    // Create test event
    const event = await db.event.create({
      data: {
        name: "Test CheckOut Event",
        startDate: new Date("2025-07-01"),
        endDate: new Date("2025-07-03"),
      },
    });
    testEventId = event.id;

    // Create active session
    const session = await db.session.create({
      data: {
        name: "Test CheckOut Session",
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
              name: "Test CheckOut Parent",
              relationshipType: "MOTHER",
            },
          ],
        },
        children: {
          create: [
            {
              firstName: "Test",
              lastName: "CheckOut1",
              birthdate: new Date("2020-01-01"),
            },
            {
              firstName: "Test",
              lastName: "CheckOut2",
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
          startsWith: "test-checkout-",
        },
      },
    });
  });

  describe("perform", () => {
    beforeEach(async () => {
      // Check in test children
      await db.checkInRecord.createMany({
        data: [
          {
            childId: testChildId1,
            sessionId: testSessionId,
            checkInStaffId: testAdminId,
          },
          {
            childId: testChildId2,
            sessionId: testSessionId,
            checkInStaffId: testAdminId,
          },
        ],
      });
    });

    it("should check out a single child", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.checkOut.perform({
        childIds: [testChildId1],
      });

      expect(result.success).toBe(true);
      expect(result.count).toBe(1);
      expect(result.checkOuts).toHaveLength(1);
      expect(result.checkOuts[0]?.childId).toBe(testChildId1);
      expect(result.checkOuts[0]?.checkOutTime).toBeDefined();
    });

    it("should check out multiple children in batch", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.checkOut.perform({
        childIds: [testChildId1, testChildId2],
      });

      expect(result.success).toBe(true);
      expect(result.count).toBe(2);
      expect(result.checkOuts).toHaveLength(2);
    });

    it("should record pickup person", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.checkOut.perform({
        childIds: [testChildId1],
        pickedUpBy: "Parent Name",
      });

      expect(result.checkOuts[0]?.pickedUpBy).toBe("Parent Name");

      // Verify in database
      const checkIn = await db.checkInRecord.findFirst({
        where: { childId: testChildId1 },
      });
      expect(checkIn?.pickedUpBy).toBe("Parent Name");
    });

    it("should set checkOutStaffId", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      await caller.checkOut.perform({
        childIds: [testChildId1],
      });

      // Verify in database
      const checkIn = await db.checkInRecord.findFirst({
        where: { childId: testChildId1 },
      });
      expect(checkIn?.checkOutStaffId).toBe(testAdminId);
    });

    it("should reject check-out for child not checked in", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Create a child not checked in
      const family = await db.family.create({
        data: {
          parents: {
            create: [{ name: "Test NotCheckedIn Parent", relationshipType: "FATHER" }],
          },
          children: {
            create: [
              {
                firstName: "Test",
                lastName: "NotCheckedIn",
                birthdate: new Date("2020-01-01"),
              },
            ],
          },
        },
        include: { children: true },
      });

      const notCheckedInChildId = family.children[0]!.id;

      await expect(
        caller.checkOut.perform({
          childIds: [notCheckedInChildId],
        })
      ).rejects.toThrow("Check-out validation failed");
    });

    it("should reject check-out for already checked-out child", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Check out once
      await caller.checkOut.perform({
        childIds: [testChildId1],
      });

      // Attempt second check-out
      await expect(
        caller.checkOut.perform({
          childIds: [testChildId1],
        })
      ).rejects.toThrow("Check-out validation failed");
    });

    it("should require at least one child", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      await expect(
        caller.checkOut.perform({
          childIds: [],
        })
      ).rejects.toThrow();
    });
  });

  describe("undo", () => {
    let checkInRecordId: string;

    beforeEach(async () => {
      // Check in and immediately check out a child
      const checkIn = await db.checkInRecord.create({
        data: {
          childId: testChildId1,
          sessionId: testSessionId,
          checkInStaffId: testAdminId,
        },
      });

      checkInRecordId = checkIn.id;

      // Check out
      await db.checkInRecord.update({
        where: { id: checkInRecordId },
        data: {
          checkOutTime: new Date(),
          checkOutStaffId: testAdminId,
          pickedUpBy: "Test Parent",
        },
      });
    });

    it("should undo check-out within 5 minutes", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.checkOut.undo({
        checkInRecordId,
      });

      expect(result.success).toBe(true);

      // Verify in database
      const checkIn = await db.checkInRecord.findUnique({
        where: { id: checkInRecordId },
      });
      expect(checkIn?.checkOutTime).toBeNull();
      expect(checkIn?.checkOutStaffId).toBeNull();
      expect(checkIn?.pickedUpBy).toBeNull();
    });

    it("should reject undo for check-in not checked out", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Create new check-in without check-out
      const newCheckIn = await db.checkInRecord.create({
        data: {
          childId: testChildId2,
          sessionId: testSessionId,
          checkInStaffId: testAdminId,
        },
      });

      await expect(
        caller.checkOut.undo({ checkInRecordId: newCheckIn.id })
      ).rejects.toThrow("Child is not checked out");
    });

    it("should reject undo after 5-minute window", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Update check-out time to 6 minutes ago
      const sixMinutesAgo = new Date(Date.now() - 6 * 60 * 1000);
      await db.checkInRecord.update({
        where: { id: checkInRecordId },
        data: {
          checkOutTime: sixMinutesAgo,
        },
      });

      await expect(
        caller.checkOut.undo({ checkInRecordId })
      ).rejects.toThrow("Cannot undo check-out older than 5 minutes");
    });

    it("should throw error for non-existent record", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      await expect(
        caller.checkOut.undo({ checkInRecordId: "non-existent-id" })
      ).rejects.toThrow("Check-in record not found");
    });
  });

  describe("getRecent", () => {
    beforeEach(async () => {
      // Create check-ins and check them out
      const checkIn1 = await db.checkInRecord.create({
        data: {
          childId: testChildId1,
          sessionId: testSessionId,
          checkInStaffId: testAdminId,
          checkInTime: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 hours ago
        },
      });

      await db.checkInRecord.update({
        where: { id: checkIn1.id },
        data: {
          checkOutTime: new Date(Date.now() - 1 * 60 * 60 * 1000), // 1 hour ago
          checkOutStaffId: testAdminId,
        },
      });

      const checkIn2 = await db.checkInRecord.create({
        data: {
          childId: testChildId2,
          sessionId: testSessionId,
          checkInStaffId: testAdminId,
          checkInTime: new Date(Date.now() - 10 * 60 * 1000), // 10 minutes ago
        },
      });

      await db.checkInRecord.update({
        where: { id: checkIn2.id },
        data: {
          checkOutTime: new Date(Date.now() - 2 * 60 * 1000), // 2 minutes ago
          checkOutStaffId: testAdminId,
        },
      });
    });

    it("should return recent check-outs within 24 hours", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.checkOut.getRecent({});

      expect(result.length).toBeGreaterThanOrEqual(2);
      expect(result.some((c) => c.childId === testChildId1)).toBe(true);
      expect(result.some((c) => c.childId === testChildId2)).toBe(true);
    });

    it("should order by most recent first", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.checkOut.getRecent({});

      const child2Index = result.findIndex((c) => c.childId === testChildId2);
      const child1Index = result.findIndex((c) => c.childId === testChildId1);

      expect(child2Index).toBeLessThan(child1Index); // Child2 checked out more recently
    });

    it("should filter by session ID", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Create second session
      const session2 = await db.session.create({
        data: {
          name: "Test CheckOut Session 2",
          startTime: new Date("2025-07-01T14:00:00"),
          endTime: new Date("2025-07-01T16:00:00"),
          requiresTicket: false,
          isActive: true,
          eventId: testEventId,
        },
      });

      // Create third child in different session
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

      const checkIn3 = await db.checkInRecord.create({
        data: {
          childId: family2.children[0]!.id,
          sessionId: session2.id,
          checkInStaffId: testAdminId,
        },
      });

      await db.checkInRecord.update({
        where: { id: checkIn3.id },
        data: {
          checkOutTime: new Date(),
          checkOutStaffId: testAdminId,
        },
      });

      // Filter by first session
      const result = await caller.checkOut.getRecent({ sessionId: testSessionId });

      expect(result.every((c) => c.sessionId === testSessionId)).toBe(true);
      expect(result.some((c) => c.childId === family2.children[0]!.id)).toBe(false);
    });

    it("should include canUndo flag", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.checkOut.getRecent({});

      const recentCheckOut = result.find((c) => c.childId === testChildId2);
      const olderCheckOut = result.find((c) => c.childId === testChildId1);

      expect(recentCheckOut?.canUndo).toBe(true); // 2 minutes ago
      expect(olderCheckOut?.canUndo).toBe(false); // 1 hour ago
    });

    it("should respect limit parameter", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.checkOut.getRecent({ limit: 1 });

      expect(result.length).toBeLessThanOrEqual(1);
    });

    it("should include child, family, parent, session, and staff details", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.checkOut.getRecent({});

      const checkOut = result.find((c) => c.childId === testChildId1);
      expect(checkOut?.child).toBeDefined();
      expect(checkOut?.child.family).toBeDefined();
      expect(checkOut?.child.family.parents).toBeDefined();
      expect(checkOut?.session).toBeDefined();
      expect(checkOut?.checkOutStaff).toBeDefined();
    });
  });

  describe("getStats", () => {
    beforeEach(async () => {
      // Create check-ins (some checked out, some still in)
      const checkIn1 = await db.checkInRecord.create({
        data: {
          childId: testChildId1,
          sessionId: testSessionId,
          checkInStaffId: testAdminId,
        },
      });

      // Check out child 1
      await db.checkInRecord.update({
        where: { id: checkIn1.id },
        data: {
          checkOutTime: new Date(),
          checkOutStaffId: testAdminId,
        },
      });

      // Create check-in for child 2 (still checked in)
      await db.checkInRecord.create({
        data: {
          childId: testChildId2,
          sessionId: testSessionId,
          checkInStaffId: testAdminId,
        },
      });
    });

    it("should return accurate session statistics", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.checkOut.getStats({
        sessionId: testSessionId,
      });

      expect(result.totalCheckIns).toBe(2);
      expect(result.totalCheckOuts).toBe(1);
      expect(result.currentlyCheckedIn).toBe(1);
      expect(result.checkOutRate).toBe(50); // 1 out of 2 = 50%
    });

    it("should calculate check-out rate correctly", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Check out the remaining child
      await db.checkInRecord.updateMany({
        where: {
          childId: testChildId2,
          sessionId: testSessionId,
        },
        data: {
          checkOutTime: new Date(),
          checkOutStaffId: testAdminId,
        },
      });

      const result = await caller.checkOut.getStats({
        sessionId: testSessionId,
      });

      expect(result.totalCheckIns).toBe(2);
      expect(result.totalCheckOuts).toBe(2);
      expect(result.currentlyCheckedIn).toBe(0);
      expect(result.checkOutRate).toBe(100); // 2 out of 2 = 100%
    });

    it("should handle session with no check-ins", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Create empty session
      const emptySession = await db.session.create({
        data: {
          name: "Test Empty Session",
          startTime: new Date("2025-07-02T09:00:00"),
          endTime: new Date("2025-07-02T11:00:00"),
          requiresTicket: false,
          isActive: true,
          eventId: testEventId,
        },
      });

      const result = await caller.checkOut.getStats({
        sessionId: emptySession.id,
      });

      expect(result.totalCheckIns).toBe(0);
      expect(result.totalCheckOuts).toBe(0);
      expect(result.currentlyCheckedIn).toBe(0);
      expect(result.checkOutRate).toBe(0);
    });
  });
});
