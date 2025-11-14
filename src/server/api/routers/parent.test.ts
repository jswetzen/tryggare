import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { db } from "~/server/db";
import { appRouter } from "~/server/api/root";
import { createTRPCContext } from "~/server/api/trpc";
import type { Session } from "next-auth";

describe("Parent Router", () => {
  let testAdminId: string;
  let testSession: Session;
  let testFamilyId: string;
  let testParentId: string;

  beforeEach(async () => {
    // Create a test admin user
    const testAdmin = await db.adminUser.create({
      data: {
        username: "test-parent-admin",
        passwordHash: "test-hash",
        name: "Test Parent Admin",
        isActive: true,
      },
    });
    testAdminId = testAdmin.id;

    // Create mock session
    testSession = {
      user: {
        id: testAdminId,
        username: "test-parent-admin",
        name: "Test Parent Admin",
        email: null,
        image: null,
        isActive: true,
      },
      expires: new Date(Date.now() + 8 * 60 * 60 * 1000).toISOString(),
    };

    // Create test family with parent
    const family = await db.family.create({
      data: {
        parents: {
          create: [
            {
              name: "Test Parent",
              relationshipType: "MOTHER",
              phone: "+1234567890",
              email: "parent@example.com",
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
      include: { parents: true },
    });

    testFamilyId = family.id;
    testParentId = family.parents[0]!.id;
  });

  afterEach(async () => {
    // Clean up test data
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
          startsWith: "test-parent-",
        },
      },
    });
  });

  describe("getById", () => {
    it("should retrieve parent with family", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.parent.getById({ id: testParentId });

      expect(result).toBeDefined();
      expect(result.id).toBe(testParentId);
      expect(result.name).toBe("Test Parent");
      expect(result.family).toBeDefined();
      expect(result.family.id).toBe(testFamilyId);
    });

    it("should throw error for non-existent parent", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      await expect(
        caller.parent.getById({ id: "non-existent-id" })
      ).rejects.toThrow("Parent not found");
    });
  });

  describe("create", () => {
    it("should add parent to existing family", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.parent.create({
        familyId: testFamilyId,
        name: "Test Father",
        relationshipType: "FATHER",
        phone: "+0987654321",
        email: "father@example.com",
      });

      expect(result).toBeDefined();
      expect(result.name).toBe("Test Father");
      expect(result.relationshipType).toBe("FATHER");
      expect(result.phone).toBe("+0987654321");
      expect(result.email).toBe("father@example.com");
      expect(result.familyId).toBe(testFamilyId);
    });

    it("should create parent without optional fields", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.parent.create({
        familyId: testFamilyId,
        name: "Test Guardian",
        relationshipType: "OTHER",
      });

      expect(result).toBeDefined();
      expect(result.name).toBe("Test Guardian");
      expect(result.phone).toBeNull();
      expect(result.email).toBeNull();
    });

    it("should throw error for non-existent family", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      await expect(
        caller.parent.create({
          familyId: "non-existent-id",
          name: "Test Parent",
          relationshipType: "MOTHER",
        })
      ).rejects.toThrow("Family not found");
    });

    it("should validate email format", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      await expect(
        caller.parent.create({
          familyId: testFamilyId,
          name: "Test Parent",
          relationshipType: "MOTHER",
          email: "invalid-email",
        })
      ).rejects.toThrow();
    });
  });

  describe("update", () => {
    it("should update parent details", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.parent.update({
        id: testParentId,
        name: "Updated Parent Name",
        phone: "+1111111111",
        email: "updated@example.com",
        relationshipType: "FATHER",
      });

      expect(result.name).toBe("Updated Parent Name");
      expect(result.phone).toBe("+1111111111");
      expect(result.email).toBe("updated@example.com");
      expect(result.relationshipType).toBe("FATHER");
    });

    it("should allow partial updates", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.parent.update({
        id: testParentId,
        name: "Only Name Updated",
      });

      expect(result.name).toBe("Only Name Updated");
      expect(result.phone).toBe("+1234567890"); // Unchanged
      expect(result.email).toBe("parent@example.com"); // Unchanged
    });

    it("should allow clearing optional fields", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.parent.update({
        id: testParentId,
        phone: null,
        email: null,
      });

      expect(result.phone).toBeNull();
      expect(result.email).toBeNull();
    });

    it("should validate email format", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      await expect(
        caller.parent.update({
          id: testParentId,
          email: "invalid-email",
        })
      ).rejects.toThrow();
    });

    it("should throw error for non-existent parent", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      await expect(
        caller.parent.update({
          id: "non-existent-id",
          name: "Test",
        })
      ).rejects.toThrow();
    });
  });

  describe("delete", () => {
    it("should delete parent when family has multiple parents", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Add a second parent
      const secondParent = await db.parent.create({
        data: {
          familyId: testFamilyId,
          name: "Test Second Parent",
          relationshipType: "FATHER",
        },
      });

      const result = await caller.parent.delete({ id: secondParent.id });

      expect(result.success).toBe(true);

      // Verify deletion
      const deletedParent = await db.parent.findUnique({
        where: { id: secondParent.id },
      });
      expect(deletedParent).toBeNull();
    });

    it("should prevent deletion of last parent in family", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      await expect(
        caller.parent.delete({ id: testParentId })
      ).rejects.toThrow("Cannot delete the last parent in a family");
    });

    it("should throw error for non-existent parent", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      await expect(
        caller.parent.delete({ id: "non-existent-id" })
      ).rejects.toThrow("Parent not found");
    });

    it("should allow deleting one of two parents", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Add second parent
      const secondParent = await db.parent.create({
        data: {
          familyId: testFamilyId,
          name: "Test Father",
          relationshipType: "FATHER",
        },
      });

      // Verify family has 2 parents
      const familyBefore = await db.family.findUnique({
        where: { id: testFamilyId },
        include: { parents: true },
      });
      expect(familyBefore?.parents.length).toBe(2);

      // Delete one parent
      await caller.parent.delete({ id: secondParent.id });

      // Verify family still has 1 parent
      const familyAfter = await db.family.findUnique({
        where: { id: testFamilyId },
        include: { parents: true },
      });
      expect(familyAfter?.parents.length).toBe(1);
      expect(familyAfter?.parents[0]?.id).toBe(testParentId);
    });
  });
});
