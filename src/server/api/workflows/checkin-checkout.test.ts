import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { appRouter } from "../root";
import { createTRPCContext } from "../trpc";
import { prisma } from "@/lib/prisma";

/**
 * Integration test for the complete check-in and check-out workflow
 * Tests the entire user flow from check-in to check-out
 */

describe("Check-In and Check-Out Workflow Integration", () => {

  // Test fixtures
  let testSession: {
    user: { id: string; name: string };
    expires: string;
  };
  let adminUserId: string;
  let eventId: string;
  let sessionId: string;
  let familyId: string;
  let childId: string;
  let checkInRecordId: string;

  beforeAll(async () => {
    // Clean up any existing test data
    await prisma.checkInRecord.deleteMany({
      where: {
        child: {
          family: {
            parents: {
              some: {
                name: "Integration Test Parent",
              },
            },
          },
        },
      },
    });

    await prisma.child.deleteMany({
      where: {
        family: {
          parents: {
            some: {
              name: "Integration Test Parent",
            },
          },
        },
      },
    });

    await prisma.parent.deleteMany({
      where: {
        name: "Integration Test Parent",
      },
    });

    await prisma.family.deleteMany({
      where: {
        parents: {
          some: {
            name: "Integration Test Parent",
          },
        },
      },
    });

    await prisma.session.deleteMany({
      where: {
        name: "Integration Test Session",
      },
    });

    await prisma.event.deleteMany({
      where: {
        name: "Integration Test Event",
      },
    });

    await prisma.adminUser.deleteMany({
      where: {
        username: "integration-test-user",
      },
    });

    // Create test admin user
    const hashedPassword = await import("bcryptjs").then((bcrypt) =>
      bcrypt.hash("password123", 10)
    );

    const adminUser = await prisma.adminUser.create({
      data: {
        username: "integration-test-user",
        name: "Integration Test User",
        passwordHash: hashedPassword,
        isActive: true,
      },
    });

    adminUserId = adminUser.id;

    testSession = {
      user: {
        id: adminUserId,
        name: "Integration Test User",
      },
      expires: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
    };

    // Create test event
    const event = await prisma.event.create({
      data: {
        name: "Integration Test Event",
        startDate: new Date(),
        endDate: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000), // 7 days from now
      },
    });

    eventId = event.id;

    // Create test session
    const session = await prisma.session.create({
      data: {
        name: "Integration Test Session",
        startTime: new Date(),
        endTime: new Date(Date.now() + 2 * 60 * 60 * 1000), // 2 hours from now
        isActive: true,
        requiresTicket: false,
        eventId: eventId,
      },
    });

    sessionId = session.id;

    // Create test family
    const family = await prisma.family.create({
      data: {
        parents: {
          create: {
            name: "Integration Test Parent",
            phone: "555-1234",
            email: "test@example.com",
            relationshipType: "Mother",
          },
        },
        children: {
          create: {
            firstName: "Integration",
            lastName: "TestChild",
            birthdate: new Date("2015-01-01"),
            allergies: "None",
            notes: "Test notes",
          },
        },
      },
      include: {
        children: true,
      },
    });

    familyId = family.id;
    childId = family.children[0]!.id;
  });

  afterAll(async () => {
    // Clean up test data
    await prisma.checkInRecord.deleteMany({
      where: { childId },
    });

    await prisma.child.deleteMany({
      where: { id: childId },
    });

    await prisma.parent.deleteMany({
      where: { familyId },
    });

    await prisma.family.deleteMany({
      where: { id: familyId },
    });

    await prisma.session.deleteMany({
      where: { id: sessionId },
    });

    await prisma.event.deleteMany({
      where: { id: eventId },
    });

    await prisma.adminUser.deleteMany({
      where: { id: adminUserId },
    });
  });

  it("should complete full check-in and check-out workflow", async () => {
    const ctx = await createTRPCContext({ headers: new Headers() });
    const caller = appRouter.createCaller({ ...ctx, session: testSession });

    // Step 1: Verify session is active
    const activeSessions = await caller.session.getActive();
    expect(activeSessions.length).toBeGreaterThan(0);
    expect(activeSessions.some((s) => s.id === sessionId)).toBe(true);

    // Step 2: Search for family
    const searchResults = await caller.family.search({
      query: "Integration",
      limit: 10,
    });
    expect(searchResults.length).toBeGreaterThan(0);
    expect(searchResults.some((f) => f.id === familyId)).toBe(true);

    // Step 3: Get family details
    const family = await caller.family.getById({ id: familyId });
    expect(family).toBeDefined();
    expect(family.children.length).toBeGreaterThan(0);

    // Step 4: Validate check-in (should be valid)
    const validation = await caller.checkIn.validate({
      childId,
      sessionId,
    });
    expect(validation.valid).toBe(true);

    // Step 5: Perform check-in
    const checkInResult = await caller.checkIn.perform({
      sessionId,
      childIds: [childId],
    });
    expect(checkInResult.count).toBe(1);
    expect(checkInResult.checkIns.length).toBe(1);
    expect(checkInResult.checkIns[0]!.childId).toBe(childId);
    expect(checkInResult.checkIns[0]!.qrToken).toBeDefined();

    checkInRecordId = checkInResult.checkIns[0]!.checkInRecord.id;

    // Step 6: Verify child is now checked in
    const currentCheckIns = await caller.checkIn.getCurrentCheckIns({});
    expect(currentCheckIns.length).toBeGreaterThan(0);
    expect(
      currentCheckIns.some(
        (ci) => ci.childId === childId && ci.checkOutTime === null
      )
    ).toBe(true);

    // Step 7: Try to check in again (should fail)
    await expect(
      caller.checkIn.perform({
        sessionId,
        childIds: [childId],
      })
    ).rejects.toThrow();

    // Step 8: Get child's current check-in
    const childCheckIn = await caller.child.getCurrentCheckIn({ childId });
    expect(childCheckIn).toBeDefined();
    expect(childCheckIn?.sessionId).toBe(sessionId);
    expect(childCheckIn?.checkOutTime).toBeNull();

    // Step 9: Perform check-out
    const checkOutResult = await caller.checkOut.perform({
      childIds: [childId],
      pickedUpBy: "Test Parent",
    });
    expect(checkOutResult.count).toBe(1);
    expect(checkOutResult.checkOuts.length).toBe(1);
    expect(checkOutResult.checkOuts[0]!.childId).toBe(childId);

    // Step 10: Verify child is no longer checked in
    const updatedCheckIns = await caller.checkIn.getCurrentCheckIns({});
    expect(
      updatedCheckIns.some(
        (ci) => ci.childId === childId && ci.checkOutTime === null
      )
    ).toBe(false);

    // Step 11: Verify check-out appears in recent check-outs
    const recentCheckOuts = await caller.checkOut.getRecent({ limit: 10 });
    expect(recentCheckOuts.length).toBeGreaterThan(0);
    expect(
      recentCheckOuts.some(
        (co) =>
          co.childId === childId && co.pickedUpBy === "Test Parent" && co.canUndo
      )
    ).toBe(true);

    // Step 12: Undo check-out
    await caller.checkOut.undo({ checkInRecordId });

    // Step 13: Verify child is checked in again
    const restoredCheckIns = await caller.checkIn.getCurrentCheckIns({});
    expect(
      restoredCheckIns.some(
        (ci) => ci.childId === childId && ci.checkOutTime === null
      )
    ).toBe(true);

    // Step 14: Check out again (final)
    await caller.checkOut.perform({
      childIds: [childId],
      pickedUpBy: "Test Parent",
    });

    // Step 15: Verify final state
    const finalCheckIns = await caller.checkIn.getCurrentCheckIns({});
    expect(
      finalCheckIns.some(
        (ci) => ci.childId === childId && ci.checkOutTime === null
      )
    ).toBe(false);

    // Step 16: Get check-in history
    const history = await caller.child.getCheckInHistory({
      childId,
      limit: 10,
    });
    expect(history.length).toBeGreaterThan(0);
    expect(history[0]!.childId).toBe(childId);
    expect(history[0]!.sessionId).toBe(sessionId);
  });

  it("should handle multiple children check-in and check-out in batch", async () => {
    const ctx = await createTRPCContext({ headers: new Headers() });
    const caller = appRouter.createCaller({ ...ctx, session: testSession });

    // Create additional test children
    const child2 = await prisma.child.create({
      data: {
        familyId,
        firstName: "Second",
        lastName: "TestChild",
        birthdate: new Date("2016-06-15"),
        allergies: null,
        notes: null,
      },
    });

    const child3 = await prisma.child.create({
      data: {
        familyId,
        firstName: "Third",
        lastName: "TestChild",
        birthdate: new Date("2018-03-20"),
        allergies: "Peanuts",
        notes: null,
      },
    });

    try {
      // Check in all three children
      const checkInResult = await caller.checkIn.perform({
        sessionId,
        childIds: [childId, child2.id, child3.id],
      });

      expect(checkInResult.count).toBe(3);
      expect(checkInResult.checkIns.length).toBe(3);

      // Verify all are checked in
      const currentCheckIns = await caller.checkIn.getCurrentCheckIns({
        sessionId,
      });
      const checkedInChildIds = currentCheckIns.map((ci) => ci.childId);

      expect(checkedInChildIds).toContain(childId);
      expect(checkedInChildIds).toContain(child2.id);
      expect(checkedInChildIds).toContain(child3.id);

      // Check out all three in batch
      const checkOutResult = await caller.checkOut.perform({
        childIds: [childId, child2.id, child3.id],
        pickedUpBy: "Batch Test Parent",
      });

      expect(checkOutResult.count).toBe(3);
      expect(checkOutResult.checkOuts.length).toBe(3);

      // Verify all are checked out
      const afterCheckOut = await caller.checkIn.getCurrentCheckIns({
        sessionId,
      });
      const stillCheckedIn = afterCheckOut.filter((ci) =>
        [childId, child2.id, child3.id].includes(ci.childId)
      );

      expect(stillCheckedIn.length).toBe(0);
    } finally {
      // Clean up
      await prisma.checkInRecord.deleteMany({
        where: { childId: { in: [child2.id, child3.id] } },
      });
      await prisma.child.deleteMany({
        where: { id: { in: [child2.id, child3.id] } },
      });
    }
  });

  it("should track session stats correctly through workflow", async () => {
    const ctx = await createTRPCContext({ headers: new Headers() });
    const caller = appRouter.createCaller({ ...ctx, session: testSession });

    // Get initial stats
    const initialStats = await caller.checkOut.getStats({ sessionId });
    const initialCheckedIn = initialStats.totalCheckIns;

    // Check in child
    await caller.checkIn.perform({
      sessionId,
      childIds: [childId],
    });

    // Verify stats increased
    const afterCheckInStats = await caller.checkOut.getStats({ sessionId });
    expect(afterCheckInStats.totalCheckIns).toBe(initialCheckedIn + 1);
    expect(afterCheckInStats.totalCheckOuts).toBe(initialStats.totalCheckOuts);
    expect(afterCheckInStats.currentlyCheckedIn).toBe(initialStats.currentlyCheckedIn + 1);

    // Check out child
    await caller.checkOut.perform({
      childIds: [childId],
      pickedUpBy: "Test Parent",
    });

    // Verify stats updated
    const afterCheckOutStats = await caller.checkOut.getStats({ sessionId });
    expect(afterCheckOutStats.totalCheckOuts).toBe(
      initialStats.totalCheckOuts + 1
    );
    expect(afterCheckOutStats.totalCheckIns).toBe(initialCheckedIn + 1);
    expect(afterCheckOutStats.currentlyCheckedIn).toBe(initialStats.currentlyCheckedIn);
  });
});
