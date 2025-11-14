import { z } from "zod";
import { hash } from "bcryptjs";
import { TRPCError } from "@trpc/server";

import { createTRPCRouter, protectedProcedure } from "~/server/api/trpc";

export const adminUserRouter = createTRPCRouter({
  /**
   * Create a new admin user
   * Requires authentication
   */
  create: protectedProcedure
    .input(
      z.object({
        username: z.string().min(3).max(50),
        password: z.string().min(8),
        name: z.string().min(1).max(100),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Check if username already exists
      const existing = await ctx.db.adminUser.findUnique({
        where: { username: input.username },
      });

      if (existing) {
        throw new TRPCError({
          code: "CONFLICT",
          message: "Username already exists",
        });
      }

      // Hash the password
      const passwordHash = await hash(input.password, 10);

      // Create the admin user
      const adminUser = await ctx.db.adminUser.create({
        data: {
          username: input.username,
          passwordHash,
          name: input.name,
          isActive: true,
        },
        select: {
          id: true,
          username: true,
          name: true,
          isActive: true,
          createdAt: true,
          lastLogin: true,
        },
      });

      return adminUser;
    }),

  /**
   * List all admin users
   * Requires authentication
   */
  list: protectedProcedure
    .input(
      z
        .object({
          includeInactive: z.boolean().optional().default(false),
        })
        .optional()
    )
    .query(async ({ ctx, input }) => {
      const adminUsers = await ctx.db.adminUser.findMany({
        where: input?.includeInactive ? undefined : { isActive: true },
        select: {
          id: true,
          username: true,
          name: true,
          isActive: true,
          createdAt: true,
          lastLogin: true,
        },
        orderBy: {
          createdAt: "desc",
        },
      });

      return adminUsers;
    }),

  /**
   * Get a single admin user by ID
   * Requires authentication
   */
  getById: protectedProcedure
    .input(z.object({ id: z.string() }))
    .query(async ({ ctx, input }) => {
      const adminUser = await ctx.db.adminUser.findUnique({
        where: { id: input.id },
        select: {
          id: true,
          username: true,
          name: true,
          isActive: true,
          createdAt: true,
          lastLogin: true,
        },
      });

      if (!adminUser) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Admin user not found",
        });
      }

      return adminUser;
    }),

  /**
   * Deactivate an admin user (soft delete)
   * Requires authentication
   */
  deactivate: protectedProcedure
    .input(z.object({ id: z.string() }))
    .mutation(async ({ ctx, input }) => {
      // Prevent deactivating yourself
      if (input.id === ctx.session.user.id) {
        throw new TRPCError({
          code: "BAD_REQUEST",
          message: "You cannot deactivate your own account",
        });
      }

      const adminUser = await ctx.db.adminUser.update({
        where: { id: input.id },
        data: { isActive: false },
        select: {
          id: true,
          username: true,
          name: true,
          isActive: true,
        },
      });

      return adminUser;
    }),

  /**
   * Reactivate an admin user
   * Requires authentication
   */
  reactivate: protectedProcedure
    .input(z.object({ id: z.string() }))
    .mutation(async ({ ctx, input }) => {
      const adminUser = await ctx.db.adminUser.update({
        where: { id: input.id },
        data: { isActive: true },
        select: {
          id: true,
          username: true,
          name: true,
          isActive: true,
        },
      });

      return adminUser;
    }),

  /**
   * Update last login timestamp
   * This is called automatically during authentication
   * Requires authentication
   */
  updateLastLogin: protectedProcedure
    .input(z.object({ id: z.string() }))
    .mutation(async ({ ctx, input }) => {
      const adminUser = await ctx.db.adminUser.update({
        where: { id: input.id },
        data: { lastLogin: new Date() },
        select: {
          id: true,
          lastLogin: true,
        },
      });

      return adminUser;
    }),
});
