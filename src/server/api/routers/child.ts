import { z } from "zod";
import { createTRPCRouter, protectedProcedure } from "~/server/api/trpc";
import { TRPCError } from "@trpc/server";

export const childRouter = createTRPCRouter({
  /**
   * Get child by QR token (for QR code page lookups)
   */
  getByQrToken: protectedProcedure
    .input(z.object({ qrToken: z.string() }))
    .query(async ({ ctx, input }) => {
      const child = await ctx.db.child.findUnique({
        where: { qrToken: input.qrToken },
        include: {
          family: {
            include: {
              parents: {
                select: {
                  id: true,
                  name: true,
                  phone: true,
                  relationshipType: true,
                },
              },
            },
          },
          checkInRecords: {
            where: {
              checkOutTime: null, // Currently checked in
            },
            include: {
              session: {
                select: {
                  id: true,
                  name: true,
                  startTime: true,
                  endTime: true,
                },
              },
            },
            orderBy: {
              checkInTime: "desc",
            },
            take: 1,
          },
        },
      });

      if (!child) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Child not found with this QR token",
        });
      }

      return child;
    }),

  /**
   * Get child by ID
   */
  getById: protectedProcedure
    .input(z.object({ id: z.string() }))
    .query(async ({ ctx, input }) => {
      const child = await ctx.db.child.findUnique({
        where: { id: input.id },
        include: {
          family: {
            include: {
              parents: true,
            },
          },
        },
      });

      if (!child) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Child not found",
        });
      }

      return child;
    }),

  /**
   * Update child details
   */
  update: protectedProcedure
    .input(
      z.object({
        id: z.string(),
        firstName: z.string().min(1).optional(),
        lastName: z.string().min(1).optional(),
        birthdate: z.date().optional(),
        allergies: z.string().optional().nullable(),
        notes: z.string().optional().nullable(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      const { id, ...updateData } = input;

      const child = await ctx.db.child.update({
        where: { id },
        data: updateData,
        include: {
          family: {
            include: {
              parents: true,
            },
          },
        },
      });

      return child;
    }),

  /**
   * Generate QR token for a child (if not already set)
   * Returns the token (new or existing)
   */
  generateQrToken: protectedProcedure
    .input(z.object({ childId: z.string() }))
    .mutation(async ({ ctx, input }) => {
      const child = await ctx.db.child.findUnique({
        where: { id: input.childId },
      });

      if (!child) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Child not found",
        });
      }

      // If already has a token, return it
      if (child.qrToken) {
        return { qrToken: child.qrToken, isNew: false };
      }

      // Generate new UUID token
      const crypto = await import("crypto");
      const qrToken = crypto.randomUUID();

      await ctx.db.child.update({
        where: { id: input.childId },
        data: { qrToken },
      });

      return { qrToken, isNew: true };
    }),

  /**
   * Get check-in history for a child
   */
  getCheckInHistory: protectedProcedure
    .input(
      z.object({
        childId: z.string(),
        limit: z.number().min(1).max(100).default(20),
      })
    )
    .query(async ({ ctx, input }) => {
      const checkIns = await ctx.db.checkInRecord.findMany({
        where: { childId: input.childId },
        include: {
          session: {
            select: {
              name: true,
              startTime: true,
              endTime: true,
            },
          },
          checkInStaff: {
            select: {
              name: true,
            },
          },
          checkOutStaff: {
            select: {
              name: true,
            },
          },
        },
        orderBy: {
          checkInTime: "desc",
        },
        take: input.limit,
      });

      return checkIns;
    }),

  /**
   * Check if child is currently checked in
   * Returns the session they're checked into, or null
   */
  getCurrentCheckIn: protectedProcedure
    .input(z.object({ childId: z.string() }))
    .query(async ({ ctx, input }) => {
      const currentCheckIn = await ctx.db.checkInRecord.findFirst({
        where: {
          childId: input.childId,
          checkOutTime: null,
        },
        include: {
          session: {
            select: {
              id: true,
              name: true,
              startTime: true,
              endTime: true,
            },
          },
        },
        orderBy: {
          checkInTime: "desc",
        },
      });

      return currentCheckIn;
    }),

  /**
   * Delete a child (soft delete - only if no check-in history)
   */
  delete: protectedProcedure
    .input(z.object({ id: z.string() }))
    .mutation(async ({ ctx, input }) => {
      // Check if child has check-in records
      const hasCheckIns = await ctx.db.checkInRecord.findFirst({
        where: { childId: input.id },
      });

      if (hasCheckIns) {
        throw new TRPCError({
          code: "PRECONDITION_FAILED",
          message:
            "Cannot delete child with check-in history. Consider archiving instead.",
        });
      }

      await ctx.db.child.delete({
        where: { id: input.id },
      });

      return { success: true };
    }),
});
