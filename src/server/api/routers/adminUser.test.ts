import { describe, it, expect, beforeAll, beforeEach, afterEach } from "vitest";
import { db } from "~/server/db";
import { appRouter } from "~/server/api/root";
import { createTRPCContext } from "~/server/api/trpc";
import type { Session } from "next-auth";

describe("Admin User Router", () => {
  let testAdminId: string;
  let testSession: Session;

  beforeAll(async () => {
    // Clean up any leftover test data from previous runs
    await db.checkInRecord.deleteMany({
      where: {
        checkInStaff: {
          username: {
            startsWith: "test-",
          },
        },
      },
    });

    await db.adminUser.deleteMany({
      where: {
        username: {
          startsWith: "test-",
        },
      },
    });
  });

  beforeEach(async () => {
    // Create a test admin user for authentication
    const testAdmin = await db.adminUser.create({
      data: {
        username: "test-admin",
        passwordHash: "test-hash",
        name: "Test Admin",
        isActive: true,
      },
    });
    testAdminId = testAdmin.id;

    // Create a mock session
    testSession = {
      user: {
        id: testAdminId,
        username: "test-admin",
        name: "Test Admin",
        email: null,
        image: null,
      },
      expires: new Date(Date.now() + 8 * 60 * 60 * 1000).toISOString(),
    };
  });

  afterEach(async () => {
    // Clean up test data - need to delete check-in records first due to foreign key constraints
    await db.checkInRecord.deleteMany({
      where: {
        checkInStaff: {
          username: {
            startsWith: "test-",
          },
        },
      },
    });

    await db.adminUser.deleteMany({
      where: {
        username: {
          startsWith: "test-",
        },
      },
    });
  });

  describe("create", () => {
    it("should create a new admin user", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.adminUser.create({
        username: "test-new-admin",
        password: "testpassword123",
        name: "New Test Admin",
      });

      expect(result).toBeDefined();
      expect(result.username).toBe("test-new-admin");
      expect(result.name).toBe("New Test Admin");
      expect(result.isActive).toBe(true);
      expect(result.id).toBeDefined();

      // Verify the user was created in the database
      const dbUser = await db.adminUser.findUnique({
        where: { username: "test-new-admin" },
      });
      expect(dbUser).toBeDefined();
      expect(dbUser?.passwordHash).not.toBe("testpassword123"); // Should be hashed
    });

    it("should reject duplicate usernames", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Create first user
      await caller.adminUser.create({
        username: "test-duplicate",
        password: "password123",
        name: "First User",
      });

      // Attempt to create duplicate
      await expect(
        caller.adminUser.create({
          username: "test-duplicate",
          password: "password123",
          name: "Second User",
        })
      ).rejects.toThrow("Username already exists");
    });

    it("should reject short passwords", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      await expect(
        caller.adminUser.create({
          username: "test-short-pw",
          password: "short",
          name: "Test User",
        })
      ).rejects.toThrow();
    });

    it("should require authentication", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: null });

      await expect(
        caller.adminUser.create({
          username: "test-unauth",
          password: "password123",
          name: "Test User",
        })
      ).rejects.toThrow("You must be logged in to access this resource");
    });
  });

  describe("list", () => {
    it("should list all active admin users by default", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Create active and inactive users
      await db.adminUser.create({
        data: {
          username: "test-active",
          passwordHash: "hash",
          name: "Active User",
          isActive: true,
        },
      });

      await db.adminUser.create({
        data: {
          username: "test-inactive",
          passwordHash: "hash",
          name: "Inactive User",
          isActive: false,
        },
      });

      const result = await caller.adminUser.list();

      expect(result.length).toBeGreaterThanOrEqual(2); // At least test-admin and test-active
      expect(result.every((user) => user.isActive)).toBe(true);
      expect(result.find((u) => u.username === "test-inactive")).toBeUndefined();
    });

    it("should list all users including inactive when requested", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      await db.adminUser.create({
        data: {
          username: "test-inactive-2",
          passwordHash: "hash",
          name: "Inactive User 2",
          isActive: false,
        },
      });

      const result = await caller.adminUser.list({ includeInactive: true });

      expect(result.find((u) => u.username === "test-inactive-2")).toBeDefined();
    });
  });

  describe("getById", () => {
    it("should retrieve an admin user by ID", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const result = await caller.adminUser.getById({ id: testAdminId });

      expect(result).toBeDefined();
      expect(result.id).toBe(testAdminId);
      expect(result.username).toBe("test-admin");
    });

    it("should throw error for non-existent user", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      await expect(
        caller.adminUser.getById({ id: "non-existent-id" })
      ).rejects.toThrow("Admin user not found");
    });
  });

  describe("deactivate", () => {
    it("should deactivate an admin user", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Create user to deactivate
      const targetUser = await db.adminUser.create({
        data: {
          username: "test-to-deactivate",
          passwordHash: "hash",
          name: "User To Deactivate",
          isActive: true,
        },
      });

      const result = await caller.adminUser.deactivate({ id: targetUser.id });

      expect(result.isActive).toBe(false);

      // Verify in database
      const dbUser = await db.adminUser.findUnique({
        where: { id: targetUser.id },
      });
      expect(dbUser?.isActive).toBe(false);
    });

    it("should prevent deactivating yourself", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      await expect(
        caller.adminUser.deactivate({ id: testAdminId })
      ).rejects.toThrow("cannot deactivate your own account");
    });
  });

  describe("reactivate", () => {
    it("should reactivate an inactive admin user", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      // Create inactive user
      const targetUser = await db.adminUser.create({
        data: {
          username: "test-to-reactivate",
          passwordHash: "hash",
          name: "User To Reactivate",
          isActive: false,
        },
      });

      const result = await caller.adminUser.reactivate({ id: targetUser.id });

      expect(result.isActive).toBe(true);

      // Verify in database
      const dbUser = await db.adminUser.findUnique({
        where: { id: targetUser.id },
      });
      expect(dbUser?.isActive).toBe(true);
    });
  });

  describe("updateLastLogin", () => {
    it("should update last login timestamp", async () => {
      const ctx = await createTRPCContext({ headers: new Headers() });
      const caller = appRouter.createCaller({ ...ctx, session: testSession });

      const beforeTime = new Date();
      await new Promise((resolve) => setTimeout(resolve, 10)); // Small delay

      const result = await caller.adminUser.updateLastLogin({ id: testAdminId });

      expect(result.lastLogin).toBeDefined();
      expect(result.lastLogin!.getTime()).toBeGreaterThanOrEqual(beforeTime.getTime());

      // Verify in database
      const dbUser = await db.adminUser.findUnique({
        where: { id: testAdminId },
      });
      expect(dbUser?.lastLogin).toBeDefined();
    });
  });
});
