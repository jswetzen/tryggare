import { z } from "zod";
import { createTRPCRouter, protectedProcedure } from "~/server/api/trpc";
import { TRPCError } from "@trpc/server";

export const checkOutRouter = createTRPCRouter({
  /**
   * Perform check-out for one or more children
   * Records who picked up the child (optional)
   */
  perform: protectedProcedure
    .input(
      z.object({
        childIds: z.array(z.string()).min(1, "At least one child is required"),
        pickedUpBy: z.string().optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      const { childIds, pickedUpBy } = input;
      const staffId = ctx.session.user.id;

      // Validate each child is checked in
      const validationResults = [];
      for (const childId of childIds) {
        const currentCheckIn = await ctx.db.checkInRecord.findFirst({
          where: {
            childId,
            checkOutTime: null,
          },
          include: {
            child: true,
            session: {
              select: {
                name: true,
              },
            },
          },
        });

        if (!currentCheckIn) {
          const child = await ctx.db.child.findUnique({
            where: { id: childId },
          });

          validationResults.push({
            childId,
            success: false,
            error: child
              ? `${child.firstName} ${child.lastName} is not currently checked in`
              : "Child not found",
          });
          continue;
        }

        validationResults.push({
          childId,
          checkInRecord: currentCheckIn,
          success: true,
        });
      }

      // If any validation failed, return errors
      const failures = validationResults.filter((r) => !r.success);
      if (failures.length > 0) {
        throw new TRPCError({
          code: "PRECONDITION_FAILED",
          message: `Check-out validation failed for ${failures.length} child(ren)`,
          cause: failures,
        });
      }

      // Perform check-outs
      const checkOutResults = [];
      for (const result of validationResults) {
        if (!result.success || !result.checkInRecord) continue;

        const checkInRecord = result.checkInRecord;

        // Update check-in record with check-out info
        const updated = await ctx.db.checkInRecord.update({
          where: { id: checkInRecord.id },
          data: {
            checkOutTime: new Date(),
            pickedUpBy: pickedUpBy || null,
            checkOutStaffId: staffId,
          },
          include: {
            child: true,
            session: {
              select: {
                name: true,
              },
            },
          },
        });

        checkOutResults.push({
          childId: checkInRecord.child.id,
          childName: `${checkInRecord.child.firstName} ${checkInRecord.child.lastName}`,
          checkOutTime: updated.checkOutTime,
          pickedUpBy: updated.pickedUpBy,
          sessionName: updated.session.name,
          success: true,
        });
      }

      return {
        success: true,
        checkOuts: checkOutResults,
        count: checkOutResults.length,
      };
    }),

  /**
   * Undo a recent check-out (within last 5 minutes)
   * Useful for accidental check-outs
   */
  undo: protectedProcedure
    .input(
      z.object({
        checkInRecordId: z.string(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      const checkInRecord = await ctx.db.checkInRecord.findUnique({
        where: { id: input.checkInRecordId },
        include: {
          child: true,
        },
      });

      if (!checkInRecord) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Check-in record not found",
        });
      }

      if (!checkInRecord.checkOutTime) {
        throw new TRPCError({
          code: "PRECONDITION_FAILED",
          message: "Child is not checked out",
        });
      }

      // Check if check-out was recent (within 5 minutes)
      const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);
      if (checkInRecord.checkOutTime < fiveMinutesAgo) {
        throw new TRPCError({
          code: "PRECONDITION_FAILED",
          message:
            "Cannot undo check-out older than 5 minutes. Please check in again instead.",
        });
      }

      // Undo check-out
      const updated = await ctx.db.checkInRecord.update({
        where: { id: input.checkInRecordId },
        data: {
          checkOutTime: null,
          pickedUpBy: null,
          checkOutStaffId: null,
        },
        include: {
          child: true,
          session: {
            select: {
              name: true,
            },
          },
        },
      });

      return {
        success: true,
        childName: `${updated.child.firstName} ${updated.child.lastName}`,
        sessionName: updated.session.name,
        message: "Check-out has been undone successfully",
      };
    }),

  /**
   * Get recent check-outs (last 24 hours)
   * Used for displaying recent activity and allowing undo
   */
  getRecent: protectedProcedure
    .input(
      z
        .object({
          sessionId: z.string().optional(),
          limit: z.number().min(1).max(100).default(50),
        })
        .optional()
    )
    .query(async ({ ctx, input }) => {
      const { sessionId, limit = 50 } = input ?? {};

      const twentyFourHoursAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);

      const where: any = {
        checkOutTime: {
          gte: twentyFourHoursAgo,
          not: null,
        },
      };

      if (sessionId) {
        where.sessionId = sessionId;
      }

      const checkOuts = await ctx.db.checkInRecord.findMany({
        where,
        include: {
          child: {
            include: {
              family: {
                include: {
                  parents: {
                    select: {
                      name: true,
                      phone: true,
                    },
                  },
                },
              },
            },
          },
          session: {
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
          checkOutTime: "desc",
        },
        take: limit,
      });

      // Add flag for whether undo is available
      const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);
      const checkOutsWithUndoFlag = checkOuts.map((checkOut) => ({
        ...checkOut,
        canUndo: checkOut.checkOutTime
          ? checkOut.checkOutTime >= fiveMinutesAgo
          : false,
      }));

      return checkOutsWithUndoFlag;
    }),

  /**
   * Get check-out statistics for a session
   */
  getStats: protectedProcedure
    .input(
      z.object({
        sessionId: z.string(),
      })
    )
    .query(async ({ ctx, input }) => {
      const totalCheckIns = await ctx.db.checkInRecord.count({
        where: {
          sessionId: input.sessionId,
        },
      });

      const totalCheckOuts = await ctx.db.checkInRecord.count({
        where: {
          sessionId: input.sessionId,
          checkOutTime: { not: null },
        },
      });

      const currentlyCheckedIn = await ctx.db.checkInRecord.count({
        where: {
          sessionId: input.sessionId,
          checkOutTime: null,
        },
      });

      return {
        totalCheckIns,
        totalCheckOuts,
        currentlyCheckedIn,
        checkOutRate:
          totalCheckIns > 0 ? (totalCheckOuts / totalCheckIns) * 100 : 0,
      };
    }),
});
