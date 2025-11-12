import { describe, it, expect, beforeAll } from "vitest";
import { db } from "./db";

describe("Database Connection", () => {
  it("should connect to the database", async () => {
    // Simple connectivity test
    await expect(db.$queryRaw`SELECT 1`).resolves.toBeDefined();
  });

  it("should have access to AdminUser model", () => {
    expect(db.adminUser).toBeDefined();
    expect(typeof db.adminUser.findMany).toBe("function");
  });

  it("should have access to Family model", () => {
    expect(db.family).toBeDefined();
    expect(typeof db.family.findMany).toBe("function");
  });

  it("should have access to Child model", () => {
    expect(db.child).toBeDefined();
    expect(typeof db.child.findMany).toBe("function");
  });

  it("should have access to Session model", () => {
    expect(db.session).toBeDefined();
    expect(typeof db.session.findMany).toBe("function");
  });

  it("should have access to CheckInRecord model", () => {
    expect(db.checkInRecord).toBeDefined();
    expect(typeof db.checkInRecord.findMany).toBe("function");
  });

  it("should have access to AuditLog model", () => {
    expect(db.auditLog).toBeDefined();
    expect(typeof db.auditLog.findMany).toBe("function");
  });
});

describe("Database Models Operations", () => {
  it("should query admin users", async () => {
    const users = await db.adminUser.findMany();
    expect(Array.isArray(users)).toBe(true);
  });

  it("should query families", async () => {
    const families = await db.family.findMany();
    expect(Array.isArray(families)).toBe(true);
  });

  it("should query children", async () => {
    const children = await db.child.findMany({ take: 10 });
    expect(Array.isArray(children)).toBe(true);
  });

  it("should query sessions", async () => {
    const sessions = await db.session.findMany();
    expect(Array.isArray(sessions)).toBe(true);
  });

  it("should query check-in records", async () => {
    const records = await db.checkInRecord.findMany({ take: 10 });
    expect(Array.isArray(records)).toBe(true);
  });
});
