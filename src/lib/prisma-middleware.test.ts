import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { setAuditUserId, clearAuditUserId } from "./prisma";
import { db } from "~/server/db";

describe("Prisma Middleware - Audit Logging", () => {
  let testAdminId: string;
  let testFamilyId: string;

  beforeEach(async () => {
    // Create test admin for audit logging
    const testAdmin = await db.adminUser.create({
      data: {
        username: "test-audit-admin",
        passwordHash: "test-hash",
        name: "Test Audit Admin",
        isActive: true,
      },
    });
    testAdminId = testAdmin.id;

    // Set audit user context
    setAuditUserId(testAdminId);

    // Clean up old audit logs
    await db.auditLog.deleteMany({
      where: { userId: testAdminId },
    });
  });

  afterEach(async () => {
    // Clean up
    clearAuditUserId();

    if (testFamilyId) {
      await db.child.deleteMany({ where: { familyId: testFamilyId } });
      await db.parent.deleteMany({ where: { familyId: testFamilyId } });
      await db.family.delete({ where: { id: testFamilyId } }).catch(() => {});
    }

    await db.auditLog.deleteMany({ where: { userId: testAdminId } });
    await db.adminUser.delete({ where: { id: testAdminId } });
  });

  describe("CREATE operations", () => {
    it("should log family creation", async () => {
      const family = await db.family.create({
        data: {},
      });
      testFamilyId = family.id;

      const auditLog = await db.auditLog.findFirst({
        where: {
          userId: testAdminId,
          action: "CREATE_FAMILY",
          entityId: family.id,
        },
      });

      expect(auditLog).toBeDefined();
      expect(auditLog?.entityType).toBe("Family");
      expect(auditLog?.action).toBe("CREATE_FAMILY");
      expect(auditLog?.userId).toBe(testAdminId);
    });

    it("should log parent creation", async () => {
      const family = await db.family.create({ data: {} });
      testFamilyId = family.id;

      const parent = await db.parent.create({
        data: {
          name: "Test Parent",
          familyId: family.id,
          relationshipType: "Mom",
        },
      });

      const auditLog = await db.auditLog.findFirst({
        where: {
          userId: testAdminId,
          action: "CREATE_PARENT",
          entityId: parent.id,
        },
      });

      expect(auditLog).toBeDefined();
      expect(auditLog?.entityType).toBe("Parent");
    });

    it("should log child creation", async () => {
      const family = await db.family.create({ data: {} });
      testFamilyId = family.id;

      const child = await db.child.create({
        data: {
          firstName: "Test",
          lastName: "Child",
          birthdate: new Date("2020-01-01"),
          familyId: family.id,
        },
      });

      const auditLog = await db.auditLog.findFirst({
        where: {
          userId: testAdminId,
          action: "CREATE_CHILD",
          entityId: child.id,
        },
      });

      expect(auditLog).toBeDefined();
      expect(auditLog?.entityType).toBe("Child");
    });

    it("should not log when userId is not set", async () => {
      clearAuditUserId();

      const family = await db.family.create({ data: {} });
      testFamilyId = family.id;

      const auditLog = await db.auditLog.findFirst({
        where: {
          entityType: "Family",
          entityId: family.id,
        },
      });

      expect(auditLog).toBeNull();
    });
  });

  describe("UPDATE operations", () => {
    it("should log family updates", async () => {
      const family = await db.family.create({ data: {} });
      testFamilyId = family.id;

      // Clear old logs
      await db.auditLog.deleteMany({ where: { userId: testAdminId } });

      await db.family.update({
        where: { id: family.id },
        data: { lastParticipationDate: new Date() },
      });

      const auditLog = await db.auditLog.findFirst({
        where: {
          userId: testAdminId,
          action: "UPDATE_FAMILY",
          entityId: family.id,
        },
      });

      expect(auditLog).toBeDefined();
      expect(auditLog?.action).toBe("UPDATE_FAMILY");
    });

    it("should log updateMany operations", async () => {
      const family = await db.family.create({ data: {} });
      testFamilyId = family.id;

      await db.parent.createMany({
        data: [
          {
            name: "Parent 1",
            familyId: family.id,
            relationshipType: "Mom",
          },
          {
            name: "Parent 2",
            familyId: family.id,
            relationshipType: "Dad",
          },
        ],
      });

      // Clear old logs
      await db.auditLog.deleteMany({ where: { userId: testAdminId } });

      await db.parent.updateMany({
        where: { familyId: family.id },
        data: { lastParticipationDate: new Date() },
      });

      const auditLog = await db.auditLog.findFirst({
        where: {
          userId: testAdminId,
          action: "UPDATE_PARENT",
          entityId: "multiple",
        },
      });

      expect(auditLog).toBeDefined();
    });
  });

  describe("DELETE operations", () => {
    it("should log delete operations", async () => {
      const family = await db.family.create({ data: {} });
      testFamilyId = family.id;

      // Clear old logs
      await db.auditLog.deleteMany({ where: { userId: testAdminId } });

      await db.family.delete({ where: { id: family.id } });

      const auditLog = await db.auditLog.findFirst({
        where: {
          userId: testAdminId,
          action: "DELETE_FAMILY",
          entityId: family.id,
        },
      });

      expect(auditLog).toBeDefined();
      expect(auditLog?.action).toBe("DELETE_FAMILY");

      testFamilyId = ""; // Already deleted
    });
  });

  describe("Audit log details", () => {
    it("should store operation details in JSON", async () => {
      const family = await db.family.create({ data: {} });
      testFamilyId = family.id;

      const auditLog = await db.auditLog.findFirst({
        where: {
          userId: testAdminId,
          entityId: family.id,
        },
      });

      expect(auditLog?.details).toBeDefined();
      expect(typeof auditLog?.details).toBe("object");
    });

    it("should include timestamp in details", async () => {
      const family = await db.family.create({ data: {} });
      testFamilyId = family.id;

      const auditLog = await db.auditLog.findFirst({
        where: {
          userId: testAdminId,
          entityId: family.id,
        },
      });

      const details = auditLog?.details as any;
      expect(details?.timestamp).toBeDefined();
    });
  });
});

describe("Prisma Middleware - Participation Date Updates", () => {
  let testAdminId: string;
  let testEventId: string;
  let testSessionId: string;
  let testFamilyId: string;
  let testChildId: string;

  beforeEach(async () => {
    // Create test data
    const testAdmin = await db.adminUser.create({
      data: {
        username: "test-participation-admin",
        passwordHash: "test-hash",
        name: "Test Participation Admin",
        isActive: true,
      },
    });
    testAdminId = testAdmin.id;

    const event = await db.event.create({
      data: {
        name: "Test Event",
        startDate: new Date("2025-07-01"),
        endDate: new Date("2025-07-03"),
      },
    });
    testEventId = event.id;

    const session = await db.session.create({
      data: {
        name: "Test Session",
        startTime: new Date("2025-07-01T09:00:00"),
        endTime: new Date("2025-07-01T12:00:00"),
        isActive: true,
        eventId: event.id,
      },
    });
    testSessionId = session.id;

    const family = await db.family.create({ data: {} });
    testFamilyId = family.id;

    await db.parent.create({
      data: {
        name: "Test Parent",
        familyId: family.id,
        relationshipType: "Mom",
      },
    });

    const child = await db.child.create({
      data: {
        firstName: "Test",
        lastName: "Child",
        birthdate: new Date("2020-01-01"),
        familyId: family.id,
      },
    });
    testChildId = child.id;
  });

  afterEach(async () => {
    // Clean up
    await db.checkInRecord.deleteMany({ where: { childId: testChildId } });
    await db.child.deleteMany({ where: { familyId: testFamilyId } });
    await db.parent.deleteMany({ where: { familyId: testFamilyId } });
    await db.family.delete({ where: { id: testFamilyId } });
    await db.session.delete({ where: { id: testSessionId } });
    await db.event.delete({ where: { id: testEventId } });
    await db.adminUser.delete({ where: { id: testAdminId } });
  });

  it("should update child lastParticipationDate on check-in", async () => {
    const beforeCheckIn = await db.child.findUnique({
      where: { id: testChildId },
    });
    expect(beforeCheckIn?.lastParticipationDate).toBeNull();

    await db.checkInRecord.create({
      data: {
        childId: testChildId,
        sessionId: testSessionId,
        checkInStaffId: testAdminId,
      },
    });

    const afterCheckIn = await db.child.findUnique({
      where: { id: testChildId },
    });
    expect(afterCheckIn?.lastParticipationDate).toBeDefined();
    expect(afterCheckIn?.lastParticipationDate).toBeInstanceOf(Date);
  });

  it("should update family lastParticipationDate on check-in", async () => {
    const beforeCheckIn = await db.family.findUnique({
      where: { id: testFamilyId },
    });
    expect(beforeCheckIn?.lastParticipationDate).toBeNull();

    await db.checkInRecord.create({
      data: {
        childId: testChildId,
        sessionId: testSessionId,
        checkInStaffId: testAdminId,
      },
    });

    const afterCheckIn = await db.family.findUnique({
      where: { id: testFamilyId },
    });
    expect(afterCheckIn?.lastParticipationDate).toBeDefined();
    expect(afterCheckIn?.lastParticipationDate).toBeInstanceOf(Date);
  });

  it("should update all parents lastParticipationDate on check-in", async () => {
    const parentsBefore = await db.parent.findMany({
      where: { familyId: testFamilyId },
    });
    expect(parentsBefore.every((p) => p.lastParticipationDate === null)).toBe(
      true
    );

    await db.checkInRecord.create({
      data: {
        childId: testChildId,
        sessionId: testSessionId,
        checkInStaffId: testAdminId,
      },
    });

    const parentsAfter = await db.parent.findMany({
      where: { familyId: testFamilyId },
    });
    expect(
      parentsAfter.every((p) => p.lastParticipationDate !== null)
    ).toBe(true);
  });

  it("should update dates for multiple check-ins", async () => {
    // First check-in
    await db.checkInRecord.create({
      data: {
        childId: testChildId,
        sessionId: testSessionId,
        checkInStaffId: testAdminId,
      },
    });

    const firstDate = (
      await db.child.findUnique({ where: { id: testChildId } })
    )?.lastParticipationDate;

    // Wait a bit
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Check out
    const checkIn = await db.checkInRecord.findFirst({
      where: { childId: testChildId, checkOutTime: null },
    });
    await db.checkInRecord.update({
      where: { id: checkIn!.id },
      data: { checkOutTime: new Date(), checkOutStaffId: testAdminId },
    });

    // Second check-in
    await db.checkInRecord.create({
      data: {
        childId: testChildId,
        sessionId: testSessionId,
        checkInStaffId: testAdminId,
      },
    });

    const secondDate = (
      await db.child.findUnique({ where: { id: testChildId } })
    )?.lastParticipationDate;

    expect(firstDate).toBeDefined();
    expect(secondDate).toBeDefined();
    expect(secondDate!.getTime()).toBeGreaterThan(firstDate!.getTime());
  });
});
