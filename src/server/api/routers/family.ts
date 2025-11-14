import { z } from "zod";
import { createTRPCRouter, protectedProcedure } from "~/server/api/trpc";
import { TRPCError } from "@trpc/server";

export const familyRouter = createTRPCRouter({
  /**
   * Search for families by last name, first name, or phone
   * Returns families with their parents and children
   */
  search: protectedProcedure
    .input(
      z.object({
        query: z.string().min(1, "Search query must be at least 1 character"),
        limit: z.number().min(1).max(100).default(20),
      })
    )
    .query(async ({ ctx, input }) => {
      const { query, limit } = input;

      // Search in multiple fields
      const families = await ctx.db.family.findMany({
        where: {
          OR: [
            {
              children: {
                some: {
                  OR: [
                    { firstName: { contains: query, mode: "insensitive" } },
                    { lastName: { contains: query, mode: "insensitive" } },
                  ],
                },
              },
            },
            {
              parents: {
                some: {
                  OR: [
                    { name: { contains: query, mode: "insensitive" } },
                    { phone: { contains: query } },
                  ],
                },
              },
            },
          ],
        },
        include: {
          parents: {
            orderBy: { name: "asc" },
          },
          children: {
            orderBy: [{ lastName: "asc" }, { firstName: "asc" }],
          },
        },
        take: limit,
        orderBy: {
          lastParticipationDate: { sort: "desc", nulls: "last" },
        },
      });

      return families;
    }),

  /**
   * Get a single family by ID with all relations
   */
  getById: protectedProcedure
    .input(z.object({ id: z.string() }))
    .query(async ({ ctx, input }) => {
      const family = await ctx.db.family.findUnique({
        where: { id: input.id },
        include: {
          parents: {
            orderBy: { name: "asc" },
          },
          children: {
            orderBy: [{ lastName: "asc" }, { firstName: "asc" }],
          },
        },
      });

      if (!family) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Family not found",
        });
      }

      return family;
    }),

  /**
   * Get families by last participation date (for GDPR review)
   * Returns families that haven't participated since the specified date
   */
  getByLastParticipation: protectedProcedure
    .input(
      z.object({
        beforeDate: z.date(),
        limit: z.number().min(1).max(100).default(50),
      })
    )
    .query(async ({ ctx, input }) => {
      const families = await ctx.db.family.findMany({
        where: {
          OR: [
            { lastParticipationDate: { lt: input.beforeDate } },
            { lastParticipationDate: null },
          ],
        },
        include: {
          parents: {
            select: {
              id: true,
              name: true,
              lastParticipationDate: true,
            },
          },
          children: {
            select: {
              id: true,
              firstName: true,
              lastName: true,
              lastParticipationDate: true,
            },
          },
        },
        take: input.limit,
        orderBy: {
          lastParticipationDate: { sort: "asc", nulls: "first" },
        },
      });

      return families;
    }),

  /**
   * Create a new family with parents and children
   */
  create: protectedProcedure
    .input(
      z.object({
        parents: z
          .array(
            z.object({
              name: z.string().min(1, "Parent name is required"),
              phone: z.string().optional(),
              email: z.string().email().optional().or(z.literal("")),
              relationshipType: z
                .string()
                .min(1, "Relationship type is required"),
            })
          )
          .min(1, "At least one parent is required"),
        children: z
          .array(
            z.object({
              firstName: z.string().min(1, "First name is required"),
              lastName: z.string().min(1, "Last name is required"),
              birthdate: z.date(),
              allergies: z.string().optional(),
              notes: z.string().optional(),
            })
          )
          .min(1, "At least one child is required"),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Create family with nested parents and children
      const family = await ctx.db.family.create({
        data: {
          parents: {
            create: input.parents.map((parent) => ({
              name: parent.name,
              phone: parent.phone,
              email: parent.email || null,
              relationshipType: parent.relationshipType,
            })),
          },
          children: {
            create: input.children.map((child) => ({
              firstName: child.firstName,
              lastName: child.lastName,
              birthdate: child.birthdate,
              allergies: child.allergies,
              notes: child.notes,
            })),
          },
        },
        include: {
          parents: true,
          children: true,
        },
      });

      return family;
    }),

  /**
   * Update family details (parents and children updated separately)
   */
  update: protectedProcedure
    .input(
      z.object({
        id: z.string(),
        lastParticipationDate: z.date().optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      const family = await ctx.db.family.update({
        where: { id: input.id },
        data: {
          lastParticipationDate: input.lastParticipationDate,
        },
        include: {
          parents: true,
          children: true,
        },
      });

      return family;
    }),

  /**
   * Delete a family (with cascade to parents and children)
   */
  delete: protectedProcedure
    .input(z.object({ id: z.string() }))
    .mutation(async ({ ctx, input }) => {
      // Check if any children have check-in records
      const childrenWithCheckIns = await ctx.db.child.findFirst({
        where: {
          familyId: input.id,
          checkInRecords: {
            some: {},
          },
        },
      });

      if (childrenWithCheckIns) {
        throw new TRPCError({
          code: "PRECONDITION_FAILED",
          message:
            "Cannot delete family with check-in history. Consider archiving instead.",
        });
      }

      // Delete family (cascades to parents and children)
      await ctx.db.family.delete({
        where: { id: input.id },
      });

      return { success: true };
    }),

  /**
   * List all families with basic info
   */
  list: protectedProcedure
    .input(
      z
        .object({
          limit: z.number().min(1).max(100).default(50),
          offset: z.number().min(0).default(0),
        })
        .optional()
    )
    .query(async ({ ctx, input }) => {
      const { limit = 50, offset = 0 } = input ?? {};

      const families = await ctx.db.family.findMany({
        include: {
          parents: {
            select: {
              id: true,
              name: true,
              phone: true,
            },
          },
          children: {
            select: {
              id: true,
              firstName: true,
              lastName: true,
              birthdate: true,
            },
          },
        },
        take: limit,
        skip: offset,
        orderBy: {
          lastParticipationDate: { sort: "desc", nulls: "last" },
        },
      });

      const total = await ctx.db.family.count();

      return {
        families,
        total,
        limit,
        offset,
      };
    }),
});
