import { z } from "zod";
import { createTRPCRouter, protectedProcedure } from "~/server/api/trpc";

export const eventRouter = createTRPCRouter({
  /**
   * Create a new event
   */
  create: protectedProcedure
    .input(
      z.object({
        name: z.string().min(1, "Event name is required"),
        startDate: z.date(),
        endDate: z.date(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      const event = await ctx.db.event.create({
        data: {
          name: input.name,
          startDate: input.startDate,
          endDate: input.endDate,
        },
      });

      return event;
    }),

  /**
   * List all events
   */
  list: protectedProcedure.query(async ({ ctx }) => {
    const events = await ctx.db.event.findMany({
      orderBy: {
        startDate: "desc",
      },
      include: {
        _count: {
          select: {
            sessions: true,
          },
        },
      },
    });

    return events;
  }),

  /**
   * Get event by ID
   */
  getById: protectedProcedure
    .input(z.object({ id: z.string() }))
    .query(async ({ ctx, input }) => {
      const event = await ctx.db.event.findUnique({
        where: { id: input.id },
        include: {
          sessions: {
            orderBy: {
              startTime: "asc",
            },
          },
        },
      });

      return event;
    }),
});
