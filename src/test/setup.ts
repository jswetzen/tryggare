import "@testing-library/jest-dom/vitest";
import { beforeAll, afterEach, afterAll } from "vitest";
import { cleanup } from "@testing-library/react";

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
