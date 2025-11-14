import { z } from "zod";
import { createTRPCRouter, protectedProcedure } from "~/server/api/trpc";
import { TRPCError } from "@trpc/server";

export const parentRouter = createTRPCRouter({
  /**
   * Get parent by ID
   */
  getById: protectedProcedure
    .input(z.object({ id: z.string() }))
    .query(async ({ ctx, input }) => {
      const parent = await ctx.db.parent.findUnique({
        where: { id: input.id },
        include: {
          family: {
            include: {
              children: true,
            },
          },
        },
      });

      if (!parent) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Parent not found",
        });
      }

      return parent;
    }),

  /**
   * Update parent details
   */
  update: protectedProcedure
    .input(
      z.object({
        id: z.string(),
        name: z.string().min(1).optional(),
        phone: z.string().optional().nullable(),
        email: z.string().email().optional().or(z.literal("")).nullable(),
        relationshipType: z.string().min(1).optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      const { id, email, ...updateData } = input;

      const parent = await ctx.db.parent.update({
        where: { id },
        data: {
          ...updateData,
          email: email === "" ? null : email,
        },
        include: {
          family: {
            include: {
              children: true,
            },
          },
        },
      });

      return parent;
    }),

  /**
   * Add a parent to an existing family
   */
  create: protectedProcedure
    .input(
      z.object({
        familyId: z.string(),
        name: z.string().min(1, "Name is required"),
        phone: z.string().optional(),
        email: z.string().email().optional().or(z.literal("")),
        relationshipType: z.string().min(1, "Relationship type is required"),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Verify family exists
      const family = await ctx.db.family.findUnique({
        where: { id: input.familyId },
      });

      if (!family) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Family not found",
        });
      }

      const parent = await ctx.db.parent.create({
        data: {
          name: input.name,
          phone: input.phone,
          email: input.email || null,
          relationshipType: input.relationshipType,
          familyId: input.familyId,
        },
        include: {
          family: true,
        },
      });

      return parent;
    }),

  /**
   * Delete a parent
   */
  delete: protectedProcedure
    .input(z.object({ id: z.string() }))
    .mutation(async ({ ctx, input }) => {
      // Check if this is the last parent in the family
      const parent = await ctx.db.parent.findUnique({
        where: { id: input.id },
        include: {
          family: {
            include: {
              parents: true,
            },
          },
        },
      });

      if (!parent) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Parent not found",
        });
      }

      if (parent.family.parents.length <= 1) {
        throw new TRPCError({
          code: "PRECONDITION_FAILED",
          message:
            "Cannot delete the last parent in a family. Delete the entire family instead.",
        });
      }

      await ctx.db.parent.delete({
        where: { id: input.id },
      });

      return { success: true };
    }),
});
