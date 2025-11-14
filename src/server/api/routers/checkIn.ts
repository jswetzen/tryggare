import { z } from "zod";
import { createTRPCRouter, protectedProcedure } from "~/server/api/trpc";
import { TRPCError } from "@trpc/server";

export const checkInRouter = createTRPCRouter({
  /**
   * Perform check-in for one or more children
   * Validates that children aren't already checked in
   * Generates QR tokens if needed
   * Returns QR data for printing labels
   */
  perform: protectedProcedure
    .input(
      z.object({
        childIds: z.array(z.string()).min(1, "At least one child is required"),
        sessionId: z.string(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      const { childIds, sessionId } = input;
      const staffId = ctx.session.user.id;

      // Verify session exists and is active
      const session = await ctx.db.session.findUnique({
        where: { id: sessionId },
      });

      if (!session) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Session not found",
        });
      }

      if (!session.isActive) {
        throw new TRPCError({
          code: "PRECONDITION_FAILED",
          message: "Cannot check in to an inactive session",
        });
      }

      // Validate each child
      const validationResults = [];
      for (const childId of childIds) {
        const child = await ctx.db.child.findUnique({
          where: { id: childId },
          include: {
            family: true,
          },
        });

        if (!child) {
          validationResults.push({
            childId,
            success: false,
            error: "Child not found",
          });
          continue;
        }

        // Check if already checked in
        const currentCheckIn = await ctx.db.checkInRecord.findFirst({
          where: {
            childId,
            checkOutTime: null,
          },
          include: {
            session: {
              select: {
                name: true,
              },
            },
          },
        });

        if (currentCheckIn) {
          validationResults.push({
            childId,
            success: false,
            error: `${child.firstName} ${child.lastName} is already checked into ${currentCheckIn.session.name}`,
          });
          continue;
        }

        validationResults.push({
          childId,
          child,
          success: true,
        });
      }

      // If any validation failed, return errors
      const failures = validationResults.filter((r) => !r.success);
      if (failures.length > 0) {
        throw new TRPCError({
          code: "PRECONDITION_FAILED",
          message: `Check-in validation failed for ${failures.length} child(ren)`,
          cause: failures,
        });
      }

      // Perform check-ins and generate QR tokens
      const checkInResults = [];
      for (const result of validationResults) {
        if (!result.success || !result.child) continue;

        const child = result.child;

        // Generate QR token if needed
        let qrToken = child.qrToken;
        if (!qrToken) {
          const crypto = await import("crypto");
          qrToken = crypto.randomUUID();

          await ctx.db.child.update({
            where: { id: child.id },
            data: { qrToken },
          });
        }

        // Create check-in record (middleware will auto-update participation dates)
        const checkInRecord = await ctx.db.checkInRecord.create({
          data: {
            childId: child.id,
            sessionId,
            checkInStaffId: staffId,
          },
          include: {
            child: true,
            session: true,
          },
        });

        checkInResults.push({
          childId: child.id,
          childName: `${child.firstName} ${child.lastName}`,
          qrToken,
          checkInRecord,
          success: true,
        });
      }

      return {
        success: true,
        checkIns: checkInResults,
        count: checkInResults.length,
      };
    }),

  /**
   * Get all currently checked-in children for a session
   */
  getCurrentCheckIns: protectedProcedure
    .input(
      z.object({
        sessionId: z.string().optional(),
      })
    )
    .query(async ({ ctx, input }) => {
      const where: any = {
        checkOutTime: null,
      };

      if (input.sessionId) {
        where.sessionId = input.sessionId;
      }

      const checkIns = await ctx.db.checkInRecord.findMany({
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
              startTime: true,
              endTime: true,
            },
          },
          checkInStaff: {
            select: {
              name: true,
            },
          },
        },
        orderBy: {
          checkInTime: "desc",
        },
      });

      return checkIns;
    }),

  /**
   * Validate if a child can be checked in
   * Returns validation result without performing check-in
   */
  validate: protectedProcedure
    .input(
      z.object({
        childId: z.string(),
        sessionId: z.string(),
      })
    )
    .query(async ({ ctx, input }) => {
      const { childId, sessionId } = input;

      // Check if session is active
      const session = await ctx.db.session.findUnique({
        where: { id: sessionId },
      });

      if (!session) {
        return {
          valid: false,
          reason: "Session not found",
        };
      }

      if (!session.isActive) {
        return {
          valid: false,
          reason: "Session is not active",
        };
      }

      // Check if child exists
      const child = await ctx.db.child.findUnique({
        where: { id: childId },
      });

      if (!child) {
        return {
          valid: false,
          reason: "Child not found",
        };
      }

      // Check if already checked in
      const currentCheckIn = await ctx.db.checkInRecord.findFirst({
        where: {
          childId,
          checkOutTime: null,
        },
        include: {
          session: {
            select: {
              name: true,
            },
          },
        },
      });

      if (currentCheckIn) {
        return {
          valid: false,
          reason: `Already checked into ${currentCheckIn.session.name}`,
          currentSession: currentCheckIn.session,
        };
      }

      return {
        valid: true,
        child,
        session,
      };
    }),
});
