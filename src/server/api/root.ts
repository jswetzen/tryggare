import { createCallerFactory, createTRPCRouter } from "~/server/api/trpc";
import { adminUserRouter } from "~/server/api/routers/adminUser";
import { sessionRouter } from "~/server/api/routers/session";
import { familyRouter } from "~/server/api/routers/family";
import { childRouter } from "~/server/api/routers/child";
import { parentRouter } from "~/server/api/routers/parent";
import { checkInRouter } from "~/server/api/routers/checkIn";
import { checkOutRouter } from "~/server/api/routers/checkOut";

/**
 * This is the primary router for your server.
 *
 * All routers added in /api/routers should be manually added here.
 */
export const appRouter = createTRPCRouter({
  adminUser: adminUserRouter,
  session: sessionRouter,
  family: familyRouter,
  child: childRouter,
  parent: parentRouter,
  checkIn: checkInRouter,
  checkOut: checkOutRouter,
});

// export type definition of API
export type AppRouter = typeof appRouter;

/**
 * Create a server-side caller for the tRPC API.
 * @example
 * const trpc = createCaller(createContext);
 * const res = await trpc.post.all();
 *       ^? Post[]
 */
export const createCaller = createCallerFactory(appRouter);
