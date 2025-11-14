import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { db } from "~/server/db";
import { appRouter } from "~/server/api/root";
import { createTRPCContext } from "~/server/api/trpc";
import type { Session } from "next-auth";

describe("Family Router", () => {
  let testAdminId: string;
  let testSession: Session;

  beforeEach(async () => {
    // Create a test admin user
    const testAdmin = await db.adminUser.create({
      data: {
        username: "test-family-admin",
        passwordHash: "test-hash",
        name: "Test Family Admin",
        isActive: true,
      },
    });
    testAdminId = testAdmin.id;

    // Create mock session
    testSession = {
      user: {
        id: testAdminId,
        username: "test-family-admin",
        name: "Test Family Admin",
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
        checkInStaff: {
          username: {
            startsWith: "test-family-",
          },
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
          startsWith: "test-family-",
        },
      },
    });
  });

  describe("create", () => {
    it("should create a family with parents and children", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.family.create({
        parents: [
          {
            name: "Test Parent 1",
            relationshipType: "MOTHER",
            phone: "+1234567890",
            email: "parent1@example.com",
          },
        ],
        children: [
          {
            firstName: "Test",
            lastName: "Child",
            birthdate: new Date("2020-01-01"),
            allergies: "None",
            notes: "Test notes",
          },
        ],
      });

      expect(result).toBeDefined();
      expect(result.parents).toHaveLength(1);
      expect(result.children).toHaveLength(1);
      expect(result.parents[0]?.name).toBe("Test Parent 1");
      expect(result.children[0]?.firstName).toBe("Test");
    });

    it("should require at least one parent", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      await expect(
        caller.family.create({
          parents: [],
          children: [
            {
              firstName: "Test",
              lastName: "Child",
              birthdate: new Date("2020-01-01"),
            },
          ],
        })
      ).rejects.toThrow();
    });

    it("should require at least one child", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      await expect(
        caller.family.create({
          parents: [
            {
              name: "Test Parent",
              relationshipType: "FATHER",
            },
          ],
          children: [],
        })
      ).rejects.toThrow();
    });

    it("should validate email format", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      await expect(
        caller.family.create({
          parents: [
            {
              name: "Test Parent",
              relationshipType: "MOTHER",
              email: "invalid-email",
            },
          ],
          children: [
            {
              firstName: "Test",
              lastName: "Child",
              birthdate: new Date("2020-01-01"),
            },
          ],
        })
      ).rejects.toThrow();
    });
  });

  describe("search", () => {
    beforeEach(async () => {
      // Create test families
      await db.family.create({
        data: {
          parents: {
            create: [
              {
                name: "Test Smith",
                relationshipType: "MOTHER",
                phone: "+1234567890",
              },
            ],
          },
          children: {
            create: [
              {
                firstName: "Alice",
                lastName: "Smith",
                birthdate: new Date("2018-05-15"),
              },
            ],
          },
        },
      });

      await db.family.create({
        data: {
          parents: {
            create: [
              {
                name: "Test Johnson",
                relationshipType: "FATHER",
                phone: "+0987654321",
              },
            ],
          },
          children: {
            create: [
              {
                firstName: "Bob",
                lastName: "Johnson",
                birthdate: new Date("2019-08-20"),
              },
            ],
          },
        },
      });
    });

    it("should search families by child last name", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.family.search({ query: "Smith" });

      expect(result.length).toBeGreaterThanOrEqual(1);
      expect(result.some((f) => f.children.some((c) => c.lastName === "Smith"))).toBe(true);
    });

    it("should search families by child first name", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.family.search({ query: "Alice" });

      expect(result.length).toBeGreaterThanOrEqual(1);
      expect(result.some((f) => f.children.some((c) => c.firstName === "Alice"))).toBe(true);
    });

    it("should search families by parent name", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.family.search({ query: "Johnson" });

      expect(result.length).toBeGreaterThanOrEqual(1);
      expect(result.some((f) => f.parents.some((p) => p.name.includes("Johnson")))).toBe(true);
    });

    it("should search families by phone number", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.family.search({ query: "1234567890" });

      expect(result.length).toBeGreaterThanOrEqual(1);
      expect(result.some((f) => f.parents.some((p) => p.phone?.includes("1234567890")))).toBe(true);
    });

    it("should be case insensitive", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.family.search({ query: "sMiTh" });

      expect(result.length).toBeGreaterThanOrEqual(1);
    });

    it("should respect limit parameter", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.family.search({ query: "Test", limit: 1 });

      expect(result.length).toBeLessThanOrEqual(1);
    });
  });

  describe("getById", () => {
    it("should retrieve family with all relations", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Create a family
      const family = await db.family.create({
        data: {
          parents: {
            create: [
              {
                name: "Test Parent",
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
              },
            ],
          },
        },
      });

      const result = await caller.family.getById({ id: family.id });

      expect(result).toBeDefined();
      expect(result.parents).toBeDefined();
      expect(result.children).toBeDefined();
      expect(result.parents.length).toBeGreaterThan(0);
      expect(result.children.length).toBeGreaterThan(0);
    });

    it("should throw error for non-existent family", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      await expect(
        caller.family.getById({ id: "non-existent-id" })
      ).rejects.toThrow("Family not found");
    });
  });

  describe("getByLastParticipation", () => {
    it("should find families by last participation date", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Create family with old participation date
      await db.family.create({
        data: {
          lastParticipationDate: new Date("2020-01-01"),
          parents: {
            create: [
              {
                name: "Test Old Parent",
                relationshipType: "MOTHER",
              },
            ],
          },
          children: {
            create: [
              {
                firstName: "Test",
                lastName: "Old",
                birthdate: new Date("2018-01-01"),
              },
            ],
          },
        },
      });

      const result = await caller.family.getByLastParticipation({
        beforeDate: new Date("2021-01-01"),
      });

      expect(result.length).toBeGreaterThan(0);
      expect(result.some((f) => f.children.some((c) => c.lastName === "Old"))).toBe(true);
    });

    it("should include families with null participation date", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Create family without participation date
      await db.family.create({
        data: {
          parents: {
            create: [
              {
                name: "Test Never Parent",
                relationshipType: "FATHER",
              },
            ],
          },
          children: {
            create: [
              {
                firstName: "Test",
                lastName: "Never",
                birthdate: new Date("2020-01-01"),
              },
            ],
          },
        },
      });

      const result = await caller.family.getByLastParticipation({
        beforeDate: new Date("2021-01-01"),
      });

      expect(result.some((f) => f.children.some((c) => c.lastName === "Never"))).toBe(true);
    });

    it("should respect limit parameter", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.family.getByLastParticipation({
        beforeDate: new Date(),
        limit: 1,
      });

      expect(result.length).toBeLessThanOrEqual(1);
    });
  });

  describe("list", () => {
    it("should return paginated families with total count", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Create test families
      await db.family.create({
        data: {
          parents: {
            create: [{ name: "Test List Parent 1", relationshipType: "MOTHER" }],
          },
          children: {
            create: [
              {
                firstName: "Test",
                lastName: "List1",
                birthdate: new Date("2020-01-01"),
              },
            ],
          },
        },
      });

      const result = await caller.family.list({ offset: 0, limit: 10 });

      expect(result).toBeDefined();
      expect(result.families).toBeDefined();
      expect(result.total).toBeGreaterThan(0);
      expect(Array.isArray(result.families)).toBe(true);
    });

    it("should handle offset parameter", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const firstPage = await caller.family.list({ offset: 0, limit: 1 });
      const secondPage = await caller.family.list({ offset: 1, limit: 1 });

      if (firstPage.total > 1) {
        expect(firstPage.families[0]?.id).not.toBe(secondPage.families[0]?.id);
      }
    });
  });

  describe("update", () => {
    it("should update family lastParticipationDate", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const family = await db.family.create({
        data: {
          parents: {
            create: [{ name: "Test Update Parent", relationshipType: "MOTHER" }],
          },
          children: {
            create: [
              {
                firstName: "Test",
                lastName: "Update",
                birthdate: new Date("2020-01-01"),
              },
            ],
          },
        },
      });

      const newDate = new Date("2025-01-15");
      const result = await caller.family.update({
        id: family.id,
        lastParticipationDate: newDate,
      });

      expect(result.lastParticipationDate?.toISOString()).toBe(newDate.toISOString());
    });

    it("should throw error for non-existent family", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      await expect(
        caller.family.update({
          id: "non-existent-id",
          lastParticipationDate: new Date(),
        })
      ).rejects.toThrow();
    });
  });

  describe("delete", () => {
    it("should delete family with no check-in history", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const family = await db.family.create({
        data: {
          parents: {
            create: [{ name: "Test Delete Parent", relationshipType: "FATHER" }],
          },
          children: {
            create: [
              {
                firstName: "Test",
                lastName: "Delete",
                birthdate: new Date("2020-01-01"),
              },
            ],
          },
        },
      });

      const result = await caller.family.delete({ id: family.id });

      expect(result.success).toBe(true);

      // Verify deletion
      const deletedFamily = await db.family.findUnique({ where: { id: family.id } });
      expect(deletedFamily).toBeNull();
    });

    it("should prevent deletion of family with check-in history", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Create family with child
      const family = await db.family.create({
        data: {
          parents: {
            create: [{ name: "Test Protected Parent", relationshipType: "MOTHER" }],
          },
          children: {
            create: [
              {
                firstName: "Test",
                lastName: "Protected",
                birthdate: new Date("2020-01-01"),
              },
            ],
          },
        },
        include: { children: true },
      });

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
          childId: family.children[0]!.id,
          sessionId: session.id,
          checkInStaffId: testAdminId,
        },
      });

      await expect(
        caller.family.delete({ id: family.id })
      ).rejects.toThrow("Cannot delete family");
    });
  });
});
