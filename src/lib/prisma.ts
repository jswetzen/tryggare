import { PrismaClient } from "../../generated/prisma";

// PrismaClient is attached to the `global` object in development to prevent
// exhausting your database connection limit.
const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient | undefined;
};

export const prisma = globalForPrisma.prisma ?? new PrismaClient();

if (process.env.NODE_ENV !== "production") globalForPrisma.prisma = prisma;

// ============================================================================
// Middleware for automatic lastParticipationDate updates
// ============================================================================

prisma.$use(async (params, next) => {
  // Only process CheckInRecord create operations
  if (params.model === "CheckInRecord" && params.action === "create") {
    const result = await next(params);

    // After creating a check-in record, update participation dates
    if (result && result.childId) {
      const now = new Date();

      // Update Child's lastParticipationDate
      await prisma.child.update({
        where: { id: result.childId },
        data: { lastParticipationDate: now },
      });

      // Get the child's family to update family and parents
      const child = await prisma.child.findUnique({
        where: { id: result.childId },
        include: { family: { include: { parents: true } } },
      });

      if (child) {
        // Update Family's lastParticipationDate
        await prisma.family.update({
          where: { id: child.familyId },
          data: { lastParticipationDate: now },
        });

        // Update all Parents' lastParticipationDate
        if (child.family.parents.length > 0) {
          await prisma.parent.updateMany({
            where: { familyId: child.familyId },
            data: { lastParticipationDate: now },
          });
        }
      }
    }

    return result;
  }

  return next(params);
});

// ============================================================================
// Middleware for audit logging
// ============================================================================

// Context to store current user ID for audit logging
export type AuditContext = {
  userId?: string;
};

const auditContext: AuditContext = {};

export function setAuditUserId(userId: string) {
  auditContext.userId = userId;
}

export function clearAuditUserId() {
  auditContext.userId = undefined;
}

prisma.$use(async (params, next) => {
  // Only log specific operations
  const shouldAudit =
    params.action === "create" ||
    params.action === "update" ||
    params.action === "delete" ||
    params.action === "deleteMany" ||
    params.action === "updateMany";

  if (!shouldAudit || !auditContext.userId) {
    return next(params);
  }

  // Execute the operation
  const result = await next(params);

  // Determine action type
  let action = "";
  switch (params.action) {
    case "create":
      action = `CREATE_${params.model?.toUpperCase()}`;
      break;
    case "update":
    case "updateMany":
      action = `UPDATE_${params.model?.toUpperCase()}`;
      break;
    case "delete":
    case "deleteMany":
      action = `DELETE_${params.model?.toUpperCase()}`;
      break;
  }

  // Extract entity ID if available
  let entityId = "";
  if (params.action === "create" && result?.id) {
    entityId = result.id;
  } else if (params.args?.where?.id) {
    entityId = params.args.where.id;
  }

  // Create audit log entry (don't audit AuditLog itself)
  if (params.model !== "AuditLog" && action && params.model) {
    try {
      await prisma.auditLog.create({
        data: {
          userId: auditContext.userId,
          action,
          entityType: params.model,
          entityId: entityId || "unknown",
          details: {
            args: params.args,
            timestamp: new Date().toISOString(),
          },
        },
      });
    } catch (error) {
      // Log error but don't fail the original operation
      console.error("Failed to create audit log:", error);
    }
  }

  return result;
});

export default prisma;
