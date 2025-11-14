import { PrismaClient } from "../../generated/prisma";

// ============================================================================
// Audit Context for tracking current user
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

// ============================================================================
// Base Prisma Client with Extensions
// ============================================================================

const globalForPrisma = globalThis as unknown as {
  prisma: ReturnType<typeof createPrismaClient> | undefined;
};

function createPrismaClient() {
  // Create base client
  const baseClient = new PrismaClient();

  // Store reference to base client for use in extensions
  let clientRef = baseClient as PrismaClient;

  // Extension 1: Automatic lastParticipationDate updates
  const extendedClient = baseClient.$extends({
    name: "participationDateUpdater",
    query: {
      checkInRecord: {
        async create({ args, query }) {
          const result = await query(args);

          // After creating a check-in record, update participation dates
          if (result && result.childId) {
            const now = new Date();

            // Update Child's lastParticipationDate
            await clientRef.child.update({
              where: { id: result.childId },
              data: { lastParticipationDate: now },
            });

            // Get the child's family to update family and parents
            const child = await clientRef.child.findUnique({
              where: { id: result.childId },
              include: { family: { include: { parents: true } } },
            });

            if (child) {
              // Update Family's lastParticipationDate
              await clientRef.family.update({
                where: { id: child.familyId },
                data: { lastParticipationDate: now },
              });

              // Update all Parents' lastParticipationDate
              if (child.family.parents.length > 0) {
                await clientRef.parent.updateMany({
                  where: { familyId: child.familyId },
                  data: { lastParticipationDate: now },
                });
              }
            }
          }

          return result;
        },
      },
    },
  }).$extends({
    name: "auditLogger",
    query: {
      $allModels: {
        async create({ model, args, query }) {
          const result = await query(args);

          if (auditContext.userId && model !== "AuditLog") {
            const action = `CREATE_${model.toUpperCase()}`;
            const entityId = (result as any)?.id || "unknown";

            try {
              await clientRef.auditLog.create({
                data: {
                  userId: auditContext.userId,
                  action,
                  entityType: model,
                  entityId,
                  details: JSON.parse(
                    JSON.stringify({
                      args,
                      timestamp: new Date().toISOString(),
                    })
                  ),
                },
              });
            } catch (error) {
              console.error("Failed to create audit log:", error);
            }
          }

          return result;
        },
        async update({ model, args, query }) {
          const result = await query(args);

          if (auditContext.userId && model !== "AuditLog") {
            const action = `UPDATE_${model.toUpperCase()}`;
            const entityId = (args.where as any)?.id || "unknown";

            try {
              await clientRef.auditLog.create({
                data: {
                  userId: auditContext.userId,
                  action,
                  entityType: model,
                  entityId,
                  details: JSON.parse(
                    JSON.stringify({
                      args,
                      timestamp: new Date().toISOString(),
                    })
                  ),
                },
              });
            } catch (error) {
              console.error("Failed to create audit log:", error);
            }
          }

          return result;
        },
        async updateMany({ model, args, query }) {
          const result = await query(args);

          if (auditContext.userId && model !== "AuditLog") {
            const action = `UPDATE_${model.toUpperCase()}`;

            try {
              await clientRef.auditLog.create({
                data: {
                  userId: auditContext.userId,
                  action,
                  entityType: model,
                  entityId: "multiple",
                  details: JSON.parse(
                    JSON.stringify({
                      args,
                      timestamp: new Date().toISOString(),
                    })
                  ),
                },
              });
            } catch (error) {
              console.error("Failed to create audit log:", error);
            }
          }

          return result;
        },
        async delete({ model, args, query }) {
          const result = await query(args);

          if (auditContext.userId && model !== "AuditLog") {
            const action = `DELETE_${model.toUpperCase()}`;
            const entityId = (args.where as any)?.id || "unknown";

            try {
              await clientRef.auditLog.create({
                data: {
                  userId: auditContext.userId,
                  action,
                  entityType: model,
                  entityId,
                  details: JSON.parse(
                    JSON.stringify({
                      args,
                      timestamp: new Date().toISOString(),
                    })
                  ),
                },
              });
            } catch (error) {
              console.error("Failed to create audit log:", error);
            }
          }

          return result;
        },
        async deleteMany({ model, args, query }) {
          const result = await query(args);

          if (auditContext.userId && model !== "AuditLog") {
            const action = `DELETE_${model.toUpperCase()}`;

            try {
              await clientRef.auditLog.create({
                data: {
                  userId: auditContext.userId,
                  action,
                  entityType: model,
                  entityId: "multiple",
                  details: JSON.parse(
                    JSON.stringify({
                      args,
                      timestamp: new Date().toISOString(),
                    })
                  ),
                },
              });
            } catch (error) {
              console.error("Failed to create audit log:", error);
            }
          }

          return result;
        },
      },
    },
  });

  return extendedClient;
}

export const prisma = globalForPrisma.prisma ?? createPrismaClient();

if (process.env.NODE_ENV !== "production") globalForPrisma.prisma = prisma;

export default prisma;
