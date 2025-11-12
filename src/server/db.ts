// Re-export the Prisma client with middleware from lib/prisma.ts
export { prisma as db, setAuditUserId, clearAuditUserId } from "@/lib/prisma";
