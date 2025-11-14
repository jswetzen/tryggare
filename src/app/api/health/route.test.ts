import { describe, it, expect } from "vitest";
import { GET } from "./route";

describe("Health API Route", () => {
  it("should return 200 status with ok status", async () => {
    const response = await GET();
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data).toMatchObject({
      status: "ok",
      service: "conference-child-mgmt",
    });
    expect(data.timestamp).toBeDefined();
    expect(new Date(data.timestamp).toString()).not.toBe("Invalid Date");
  });

  it("should return ISO 8601 formatted timestamp", async () => {
    const response = await GET();
    const data = await response.json();

    // Verify timestamp is valid ISO 8601 format
    const timestamp = new Date(data.timestamp);
    expect(timestamp.toISOString()).toBe(data.timestamp);
  });

  it("should return response within reasonable time", async () => {
    const startTime = Date.now();
    await GET();
    const endTime = Date.now();
    const duration = endTime - startTime;

    // Health check should respond in less than 100ms
    expect(duration).toBeLessThan(100);
  });
});
