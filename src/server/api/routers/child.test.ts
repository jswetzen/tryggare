import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { db } from "~/server/db";
import { appRouter } from "~/server/api/root";
import { createTRPCContext } from "~/server/api/trpc";
import type { Session } from "next-auth";

describe("Child Router", () => {
  let testAdminId: string;
  let testSession: Session;
  let testFamilyId: string;
  let testChildId: string;

  beforeEach(async () => {
    // Create a test admin user
    const testAdmin = await db.adminUser.create({
      data: {
        username: "test-child-admin",
        passwordHash: "test-hash",
        name: "Test Child Admin",
        isActive: true,
      },
    });
    testAdminId = testAdmin.id;

    // Create mock session
    testSession = {
      user: {
        id: testAdminId,
        username: "test-child-admin",
        name: "Test Child Admin",
        email: null,
        image: null,
        isActive: true,
      },
      expires: new Date(Date.now() + 8 * 60 * 60 * 1000).toISOString(),
    };

    // Create test family with child
    const family = await db.family.create({
      data: {
        parents: {
          create: [
            {
              name: "Test Child Parent",
              relationshipType: "MOTHER",
            },
          ],
        },
        children: {
          create: [
            {
              firstName: "Test",
              lastName: "Child",
              birthdate: new Date("2020-01-01"),
              allergies: "None",
              notes: "Test notes",
            },
          ],
        },
      },
      include: { children: true },
    });

    testFamilyId = family.id;
    testChildId = family.children[0]!.id;
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
          startsWith: "test-child-",
        },
      },
    });
  });

  describe("getById", () => {
    it("should retrieve child with family", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.child.getById({ id: testChildId });

      expect(result).toBeDefined();
      expect(result.id).toBe(testChildId);
      expect(result.firstName).toBe("Test");
      expect(result.family).toBeDefined();
      expect(result.family.parents).toBeDefined();
    });

    it("should throw error for non-existent child", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      await expect(
        caller.child.getById({ id: "non-existent-id" })
      ).rejects.toThrow("Child not found");
    });
  });

  describe("update", () => {
    it("should update child details", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.child.update({
        id: testChildId,
        firstName: "Updated",
        lastName: "Name",
        allergies: "Peanuts",
        notes: "Updated notes",
      });

      expect(result.firstName).toBe("Updated");
      expect(result.lastName).toBe("Name");
      expect(result.allergies).toBe("Peanuts");
      expect(result.notes).toBe("Updated notes");
    });

    it("should allow updating birthdate", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const newBirthdate = new Date("2021-05-15");
      const result = await caller.child.update({
        id: testChildId,
        birthdate: newBirthdate,
      });

      expect(result.birthdate.toISOString()).toBe(newBirthdate.toISOString());
    });

    it("should allow clearing allergies and notes", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.child.update({
        id: testChildId,
        allergies: null,
        notes: null,
      });

      expect(result.allergies).toBeNull();
      expect(result.notes).toBeNull();
    });

    it("should throw error for non-existent child", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      await expect(
        caller.child.update({
          id: "non-existent-id",
          firstName: "Test",
        })
      ).rejects.toThrow();
    });
  });

  describe("generateQrToken", () => {
    it("should generate QR token for child without one", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.child.generateQrToken({ childId: testChildId });

      expect(result.qrToken).toBeDefined();
      expect(result.isNew).toBe(true);
      expect(typeof result.qrToken).toBe("string");
      expect(result.qrToken).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i);
    });

    it("should return existing QR token if already generated", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Generate first time
      const first = await caller.child.generateQrToken({ childId: testChildId });

      // Generate second time
      const second = await caller.child.generateQrToken({ childId: testChildId });

      expect(second.qrToken).toBe(first.qrToken);
      expect(second.isNew).toBe(false);
    });

    it("should throw error for non-existent child", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      await expect(
        caller.child.generateQrToken({ childId: "non-existent-id" })
      ).rejects.toThrow("Child not found");
    });
  });

  describe("getByQrToken", () => {
    it("should retrieve child by QR token", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Generate QR token
      const { qrToken } = await caller.child.generateQrToken({ childId: testChildId });

      // Retrieve by QR token
      const result = await caller.child.getByQrToken({ qrToken });

      expect(result).toBeDefined();
      expect(result.id).toBe(testChildId);
      expect(result.family).toBeDefined();
      expect(result.family.parents).toBeDefined();
      expect(result.checkInRecords).toEqual([]); // Not checked in
    });

    it("should include current check-in status", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Generate QR token
      const { qrToken } = await caller.child.generateQrToken({ childId: testChildId });

      // Create event and session
      const event = await db.event.create({
        data: {
          name: "Test Event",
          startDate: new Date("2025-07-01"),
          endDate: new Date("2025-07-03"),
        },
      });

      const session = await db.session.create({
        data: {
          name: "Test Session",
          startTime: new Date("2025-07-01T09:00:00"),
          endTime: new Date("2025-07-01T11:00:00"),
          requiresTicket: false,
          isActive: true,
          eventId: event.id,
        },
      });

      // Check in child
      await db.checkInRecord.create({
        data: {
          childId: testChildId,
          sessionId: session.id,
          checkInStaffId: testAdminId,
        },
      });

      // Retrieve by QR token
      const result = await caller.child.getByQrToken({ qrToken });

      expect(result.checkInRecords).toBeDefined();
      expect(result.checkInRecords.length).toBeGreaterThan(0);
      expect(result.checkInRecords[0]?.session.name).toBe("Test Session");
    });

    it("should throw error for non-existent QR token", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      await expect(
        caller.child.getByQrToken({ qrToken: "non-existent-token" })
      ).rejects.toThrow("Child not found");
    });
  });

  describe("getCurrentCheckIn", () => {
    it("should return null if child is not checked in", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.child.getCurrentCheckIn({ childId: testChildId });

      expect(result).toBeNull();
    });

    it("should return current check-in with session details", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Create event and session
      const event = await db.event.create({
        data: {
          name: "Test Event",
          startDate: new Date("2025-07-01"),
          endDate: new Date("2025-07-03"),
        },
      });

      const session = await db.session.create({
        data: {
          name: "Test Current Session",
          startTime: new Date("2025-07-01T09:00:00"),
          endTime: new Date("2025-07-01T11:00:00"),
          requiresTicket: false,
          isActive: true,
          eventId: event.id,
        },
      });

      // Check in child
      await db.checkInRecord.create({
        data: {
          childId: testChildId,
          sessionId: session.id,
          checkInStaffId: testAdminId,
        },
      });

      const result = await caller.child.getCurrentCheckIn({ childId: testChildId });

      expect(result).toBeDefined();
      expect(result?.session.name).toBe("Test Current Session");
      expect(result?.checkOutTime).toBeNull();
    });

    it("should return null after check-out", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Create event and session
      const event = await db.event.create({
        data: {
          name: "Test Event",
          startDate: new Date("2025-07-01"),
          endDate: new Date("2025-07-03"),
        },
      });

      const session = await db.session.create({
        data: {
          name: "Test Session",
          startTime: new Date("2025-07-01T09:00:00"),
          endTime: new Date("2025-07-01T11:00:00"),
          requiresTicket: false,
          isActive: true,
          eventId: event.id,
        },
      });

      // Check in child
      const checkIn = await db.checkInRecord.create({
        data: {
          childId: testChildId,
          sessionId: session.id,
          checkInStaffId: testAdminId,
        },
      });

      // Check out child
      await db.checkInRecord.update({
        where: { id: checkIn.id },
        data: {
          checkOutTime: new Date(),
          checkOutStaffId: testAdminId,
        },
      });

      const result = await caller.child.getCurrentCheckIn({ childId: testChildId });

      expect(result).toBeNull();
    });
  });

  describe("getCheckInHistory", () => {
    it("should return check-in history ordered by most recent", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Create event and sessions
      const event = await db.event.create({
        data: {
          name: "Test Event",
          startDate: new Date("2025-07-01"),
          endDate: new Date("2025-07-03"),
        },
      });

      const session1 = await db.session.create({
        data: {
          name: "Test History Session 1",
          startTime: new Date("2025-07-01T09:00:00"),
          endTime: new Date("2025-07-01T11:00:00"),
          requiresTicket: false,
          isActive: false,
          eventId: event.id,
        },
      });

      const session2 = await db.session.create({
        data: {
          name: "Test History Session 2",
          startTime: new Date("2025-07-02T09:00:00"),
          endTime: new Date("2025-07-02T11:00:00"),
          requiresTicket: false,
          isActive: false,
          eventId: event.id,
        },
      });

      // Create check-ins
      await db.checkInRecord.create({
        data: {
          childId: testChildId,
          sessionId: session1.id,
          checkInStaffId: testAdminId,
          checkInTime: new Date("2025-07-01T09:15:00"),
          checkOutTime: new Date("2025-07-01T10:45:00"),
          checkOutStaffId: testAdminId,
        },
      });

      await db.checkInRecord.create({
        data: {
          childId: testChildId,
          sessionId: session2.id,
          checkInStaffId: testAdminId,
          checkInTime: new Date("2025-07-02T09:30:00"),
          checkOutTime: new Date("2025-07-02T11:00:00"),
          checkOutStaffId: testAdminId,
        },
      });

      const result = await caller.child.getCheckInHistory({ childId: testChildId });

      expect(result.length).toBe(2);
      expect(result[0]?.session.name).toBe("Test History Session 2"); // Most recent first
      expect(result[1]?.session.name).toBe("Test History Session 1");
      expect(result[0]?.checkInStaff.name).toBeDefined();
    });

    it("should respect limit parameter", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.child.getCheckInHistory({
        childId: testChildId,
        limit: 1
      });

      expect(result.length).toBeLessThanOrEqual(1);
    });

    it("should return empty array for child with no history", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.child.getCheckInHistory({ childId: testChildId });

      expect(result).toEqual([]);
    });
  });

  describe("delete", () => {
    it("should delete child with no check-in history", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.child.delete({ id: testChildId });

      expect(result.success).toBe(true);

      // Verify deletion
      const deletedChild = await db.child.findUnique({ where: { id: testChildId } });
      expect(deletedChild).toBeNull();
    });

    it("should prevent deletion of child with check-in history", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Create event and session
      const event = await db.event.create({
        data: {
          name: "Test Event",
          startDate: new Date("2025-07-01"),
          endDate: new Date("2025-07-03"),
        },
      });

      const session = await db.session.create({
        data: {
          name: "Test Session",
          startTime: new Date("2025-07-01T09:00:00"),
          endTime: new Date("2025-07-01T11:00:00"),
          requiresTicket: false,
          isActive: true,
          eventId: event.id,
        },
      });

      // Create check-in
      await db.checkInRecord.create({
        data: {
          childId: testChildId,
          sessionId: session.id,
          checkInStaffId: testAdminId,
        },
      });

      await expect(
        caller.child.delete({ id: testChildId })
      ).rejects.toThrow("Cannot delete child with check-in history");
    });

    it("should throw error for non-existent child", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      await expect(
        caller.child.delete({ id: "non-existent-id" })
      ).rejects.toThrow();
    });
  });
});
