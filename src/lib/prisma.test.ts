import { describe, it, expect, beforeEach } from "vitest";
import { setAuditUserId, clearAuditUserId } from "./prisma";

describe("Audit Context", () => {
  beforeEach(() => {
    // Clean up audit context before each test
    clearAuditUserId();
  });

  it("should set audit user ID", () => {
    const testUserId = "test-user-123";
    setAuditUserId(testUserId);

    // The audit context is internal, but we can verify it doesn't throw
    expect(() => setAuditUserId(testUserId)).not.toThrow();
  });

  it("should clear audit user ID", () => {
    const testUserId = "test-user-123";
    setAuditUserId(testUserId);
    clearAuditUserId();

    // Verify clearing doesn't throw
    expect(() => clearAuditUserId()).not.toThrow();
  });

  it("should allow setting audit user ID multiple times", () => {
    setAuditUserId("user-1");
    setAuditUserId("user-2");
    setAuditUserId("user-3");

    // Should not throw when setting multiple times
    expect(() => setAuditUserId("user-4")).not.toThrow();
  });
});
