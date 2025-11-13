import { z } from "zod";
import { TRPCError } from "@trpc/server";

import { createTRPCRouter, protectedProcedure } from "~/server/api/trpc";

export const sessionRouter = createTRPCRouter({
  /**
   * Create a new session
   * Requires authentication
   */
  create: protectedProcedure
    .input(
      z.object({
        name: z.string().min(1).max(200),
        startTime: z.date(),
        endTime: z.date(),
        requiresTicket: z.boolean().default(false),
        eventId: z.string(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Validate that endTime is after startTime
      if (input.endTime <= input.startTime) {
        throw new TRPCError({
          code: "BAD_REQUEST",
          message: "End time must be after start time",
        });
      }

      // Verify event exists
      const event = await ctx.db.event.findUnique({
        where: { id: input.eventId },
      });

      if (!event) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Event not found",
        });
      }

      const session = await ctx.db.session.create({
        data: {
          name: input.name,
          startTime: input.startTime,
          endTime: input.endTime,
          requiresTicket: input.requiresTicket,
          isActive: false, // Sessions start inactive by default
          eventId: input.eventId,
        },
        include: {
          event: {
            select: {
              id: true,
              name: true,
              startDate: true,
              endDate: true,
            },
          },
        },
      });

      return session;
    }),

  /**
   * List all sessions with optional filtering
   * Requires authentication
   */
  list: protectedProcedure
    .input(
      z
        .object({
          eventId: z.string().optional(),
          isActive: z.boolean().optional(),
          includeEvent: z.boolean().optional().default(true),
        })
        .optional()
    )
    .query(async ({ ctx, input }) => {
      const sessions = await ctx.db.session.findMany({
        where: {
          ...(input?.eventId && { eventId: input.eventId }),
          ...(input?.isActive !== undefined && { isActive: input.isActive }),
        },
        include: input?.includeEvent
          ? {
              event: {
                select: {
                  id: true,
                  name: true,
                  startDate: true,
                  endDate: true,
                },
              },
            }
          : undefined,
        orderBy: {
          startTime: "asc",
        },
      });

      return sessions;
    }),

  /**
   * Get currently active sessions
   * Requires authentication
   */
  getActive: protectedProcedure.query(async ({ ctx }) => {
    const activeSessions = await ctx.db.session.findMany({
      where: { isActive: true },
      include: {
        event: {
          select: {
            id: true,
            name: true,
            startDate: true,
            endDate: true,
          },
        },
        checkInRecords: {
          where: {
            checkOutTime: null, // Only get currently checked-in children
          },
          select: {
            id: true,
          },
        },
      },
      orderBy: {
        startTime: "asc",
      },
    });

    // Map to include currentCheckInCount
    return activeSessions.map((session) => ({
      ...session,
      currentCheckInCount: session.checkInRecords.length,
      checkInRecords: undefined, // Remove from response for cleaner API
    }));
  }),

  /**
   * Get active session count
   * Requires authentication
   */
  getActiveCount: protectedProcedure.query(async ({ ctx }) => {
    const count = await ctx.db.session.count({
      where: { isActive: true },
    });

    return count;
  }),

  /**
   * Get a single session by ID
   * Requires authentication
   */
  getById: protectedProcedure
    .input(z.object({ id: z.string() }))
    .query(async ({ ctx, input }) => {
      const session = await ctx.db.session.findUnique({
        where: { id: input.id },
        include: {
          event: {
            select: {
              id: true,
              name: true,
              startDate: true,
              endDate: true,
            },
          },
          checkInRecords: {
            where: {
              checkOutTime: null, // Only get currently checked-in children
            },
            select: {
              id: true,
            },
          },
        },
      });

      if (!session) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Session not found",
        });
      }

      return {
        ...session,
        currentCheckInCount: session.checkInRecords.length,
        checkInRecords: undefined, // Remove from response for cleaner API
      };
    }),

  /**
   * Activate a session (make it available for check-ins)
   * Requires authentication
   */
  activate: protectedProcedure
    .input(z.object({ id: z.string() }))
    .mutation(async ({ ctx, input }) => {
      const session = await ctx.db.session.update({
        where: { id: input.id },
        data: { isActive: true },
        include: {
          event: {
            select: {
              id: true,
              name: true,
            },
          },
        },
      });

      return session;
    }),

  /**
   * Deactivate a session (prevent new check-ins)
   * Requires authentication
   */
  deactivate: protectedProcedure
    .input(z.object({ id: z.string() }))
    .mutation(async ({ ctx, input }) => {
      const session = await ctx.db.session.update({
        where: { id: input.id },
        data: { isActive: false },
        include: {
          event: {
            select: {
              id: true,
              name: true,
            },
          },
        },
      });

      return session;
    }),

  /**
   * Update session details
   * Requires authentication
   */
  update: protectedProcedure
    .input(
      z.object({
        id: z.string(),
        name: z.string().min(1).max(200).optional(),
        startTime: z.date().optional(),
        endTime: z.date().optional(),
        requiresTicket: z.boolean().optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      const { id, ...updateData } = input;

      // If both times are provided, validate them
      if (updateData.startTime && updateData.endTime) {
        if (updateData.endTime <= updateData.startTime) {
          throw new TRPCError({
            code: "BAD_REQUEST",
            message: "End time must be after start time",
          });
        }
      }

      const session = await ctx.db.session.update({
        where: { id },
        data: updateData,
        include: {
          event: {
            select: {
              id: true,
              name: true,
            },
          },
        },
      });

      return session;
    }),

  /**
   * Delete a session
   * Only allowed if no check-ins exist
   * Requires authentication
   */
  delete: protectedProcedure
    .input(z.object({ id: z.string() }))
    .mutation(async ({ ctx, input }) => {
      // Check if there are any check-ins for this session
      const checkInCount = await ctx.db.checkInRecord.count({
        where: { sessionId: input.id },
      });

      if (checkInCount > 0) {
        throw new TRPCError({
          code: "BAD_REQUEST",
          message: `Cannot delete session with ${checkInCount} check-in record(s)`,
        });
      }

      await ctx.db.session.delete({
        where: { id: input.id },
      });

      return { success: true };
    }),
});
