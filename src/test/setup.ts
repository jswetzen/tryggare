import "@testing-library/jest-dom/vitest";
import { beforeAll, afterEach, afterAll, vi } from "vitest";
import { cleanup } from "@testing-library/react";

// Mock next-auth to avoid server module import issues
vi.mock("~/lib/auth", () => ({
  auth: vi.fn().mockResolvedValue(null),
  signIn: vi.fn(),
  signOut: vi.fn(),
  getCurrentUser: vi.fn().mockResolvedValue(null),
  requireAuth: vi.fn().mockRejectedValue(new Error("Unauthorized")),
}));

// Cleanup after each test case (e.g. clearing jsdom)
afterEach(() => {
  cleanup();
});

// Global test setup
beforeAll(() => {
  // Setup code that runs before all tests
  console.log("Setting up tests...");
});

afterAll(() => {
  // Cleanup code that runs after all tests
  console.log("Tearing down tests...");
});
