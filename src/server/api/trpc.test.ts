import { describe, it, expect } from "vitest";
import { createTRPCContext, createCallerFactory, publicProcedure } from "./trpc";
import { db } from "~/server/db";

describe("tRPC Context", () => {
  it("should create tRPC context with database", async () => {
    const headers = new Headers();
    const ctx = await createTRPCContext({ headers });

    expect(ctx).toBeDefined();
    expect(ctx.db).toBeDefined();
    expect(ctx.db).toBe(db);
  });

  it("should create tRPC context with headers", async () => {
    const headers = new Headers();
    headers.set("user-agent", "test");

    const ctx = await createTRPCContext({ headers });

    expect(ctx).toBeDefined();
    expect(ctx.headers).toBe(headers);
    expect(ctx.headers.get("user-agent")).toBe("test");
  });
});

describe("tRPC Procedures", () => {
  it("should have publicProcedure defined", () => {
    expect(publicProcedure).toBeDefined();
  });

  it("should create caller factory", () => {
    expect(createCallerFactory).toBeDefined();
    expect(typeof createCallerFactory).toBe("function");
  });
});

describe("tRPC Integration", () => {
  it("should be able to create procedures with publicProcedure", () => {
    // Create a simple test procedure
    const testProcedure = publicProcedure.query(() => {
      return { message: "Hello from test!" };
    });

    // Verify the procedure is defined properly
    expect(testProcedure).toBeDefined();
    expect(testProcedure._def).toBeDefined();
    expect(testProcedure._def.procedure).toBe(true);
  });

  it("should be able to create mutation procedures", () => {
    // Create a test mutation
    const testMutation = publicProcedure.mutation(() => {
      return { success: true };
    });

    // Verify the mutation is defined properly
    expect(testMutation).toBeDefined();
    expect(testMutation._def).toBeDefined();
    expect(testMutation._def.procedure).toBe(true);
  });
});
