import { PrismaClient } from "../generated/prisma";
import * as bcrypt from "bcryptjs";
import { randomUUID } from "crypto";

const prisma = new PrismaClient();

async function main() {
  console.log("🌱 Starting database seed...");

  // Clean existing data
  console.log("🧹 Cleaning existing data...");
  await prisma.auditLog.deleteMany();
  await prisma.checkInRecord.deleteMany();
  await prisma.ticket.deleteMany();
  await prisma.child.deleteMany();
  await prisma.parent.deleteMany();
  await prisma.family.deleteMany();
  await prisma.session.deleteMany();
  await prisma.event.deleteMany();
  await prisma.adminUser.deleteMany();

  // ============================================================================
  // Seed Admin User
  // ============================================================================
  console.log("👤 Creating admin user...");

  const username = process.env.INITIAL_ADMIN_USERNAME || "admin";
  const password = process.env.INITIAL_ADMIN_PASSWORD || "changeme123";
  const passwordHash = await bcrypt.hash(password, 10);

  const admin = await prisma.adminUser.create({
    data: {
      username,
      passwordHash,
      name: "System Administrator",
      isActive: true,
    },
  });

  console.log(`✅ Admin user created: ${admin.username}`);

  // ============================================================================
  // Seed Events
  // ============================================================================
  console.log("📅 Creating events...");

  const summerConf = await prisma.event.create({
    data: {
      name: "Summer Conference 2025",
      startDate: new Date("2025-07-01"),
      endDate: new Date("2025-07-03"),
    },
  });

  const fallWorkshop = await prisma.event.create({
    data: {
      name: "Fall Workshop Weekend",
      startDate: new Date("2025-10-15"),
      endDate: new Date("2025-10-16"),
    },
  });

  console.log("✅ Events created");

  // ============================================================================
  // Seed Sessions
  // ============================================================================
  console.log("🎪 Creating sessions...");

  // Summer Conference Sessions
  const summerSessions = await Promise.all([
    prisma.session.create({
      data: {
        name: "Morning Worship - Day 1",
        startTime: new Date("2025-07-01T09:00:00"),
        endTime: new Date("2025-07-01T11:00:00"),
        isActive: true,
        requiresTicket: false,
        eventId: summerConf.id,
      },
    }),
    prisma.session.create({
      data: {
        name: "Afternoon Workshop - Day 1",
        startTime: new Date("2025-07-01T14:00:00"),
        endTime: new Date("2025-07-01T16:00:00"),
        isActive: true,
        requiresTicket: true,
        eventId: summerConf.id,
      },
    }),
    prisma.session.create({
      data: {
        name: "Evening Service - Day 1",
        startTime: new Date("2025-07-01T19:00:00"),
        endTime: new Date("2025-07-01T21:00:00"),
        isActive: false,
        requiresTicket: false,
        eventId: summerConf.id,
      },
    }),
    prisma.session.create({
      data: {
        name: "Family Activities - Day 2",
        startTime: new Date("2025-07-02T10:00:00"),
        endTime: new Date("2025-07-02T12:00:00"),
        isActive: false,
        requiresTicket: true,
        eventId: summerConf.id,
      },
    }),
  ]);

  // Fall Workshop Sessions
  const fallSessions = await Promise.all([
    prisma.session.create({
      data: {
        name: "Opening Session",
        startTime: new Date("2025-10-15T09:00:00"),
        endTime: new Date("2025-10-15T11:00:00"),
        isActive: false,
        requiresTicket: false,
        eventId: fallWorkshop.id,
      },
    }),
    prisma.session.create({
      data: {
        name: "Breakout Sessions",
        startTime: new Date("2025-10-15T13:00:00"),
        endTime: new Date("2025-10-15T15:00:00"),
        isActive: false,
        requiresTicket: true,
        eventId: fallWorkshop.id,
      },
    }),
    prisma.session.create({
      data: {
        name: "Kids Ministry Training",
        startTime: new Date("2025-10-16T09:00:00"),
        endTime: new Date("2025-10-16T12:00:00"),
        isActive: false,
        requiresTicket: false,
        eventId: fallWorkshop.id,
      },
    }),
    prisma.session.create({
      data: {
        name: "Closing Celebration",
        startTime: new Date("2025-10-16T18:00:00"),
        endTime: new Date("2025-10-16T20:00:00"),
        isActive: false,
        requiresTicket: false,
        eventId: fallWorkshop.id,
      },
    }),
  ]);

  console.log("✅ Sessions created");

  // ============================================================================
  // Seed Families with Parents and Children
  // ============================================================================
  console.log("👨‍👩‍👧‍👦 Creating families...");

  // Family 1: Smith Family
  const smithFamily = await prisma.family.create({
    data: {
      parents: {
        create: [
          {
            name: "John Smith",
            phone: "+1-555-0101",
            email: "john.smith@example.com",
            relationshipType: "Dad",
          },
          {
            name: "Sarah Smith",
            phone: "+1-555-0102",
            email: "sarah.smith@example.com",
            relationshipType: "Mom",
          },
        ],
      },
      children: {
        create: [
          {
            firstName: "Emma",
            lastName: "Smith",
            birthdate: new Date("2021-03-15"),
            allergies: "Peanut allergy",
            notes: "Carries EpiPen at all times",
          },
          {
            firstName: "Oliver",
            lastName: "Smith",
            birthdate: new Date("2018-06-22"),
            allergies: null,
            notes: "Loves dinosaurs",
          },
          {
            firstName: "Sophia",
            lastName: "Smith",
            birthdate: new Date("2015-11-08"),
            allergies: null,
            notes: "Takes asthma medication if needed",
          },
        ],
      },
    },
    include: {
      children: true,
    },
  });

  // Family 2: Johnson Family (single parent)
  const johnsonFamily = await prisma.family.create({
    data: {
      parents: {
        create: [
          {
            name: "Maria Johnson",
            phone: "+1-555-0201",
            email: "maria.johnson@example.com",
            relationshipType: "Mom",
          },
        ],
      },
      children: {
        create: [
          {
            firstName: "Lucas",
            lastName: "Johnson",
            birthdate: new Date("2020-04-10"),
            allergies: null,
            notes: null,
          },
          {
            firstName: "Mia",
            lastName: "Johnson",
            birthdate: new Date("2017-09-25"),
            allergies: null,
            notes: null,
          },
        ],
      },
    },
    include: {
      children: true,
    },
  });

  // Family 3: Garcia Family
  const garciaFamily = await prisma.family.create({
    data: {
      parents: {
        create: [
          {
            name: "Carlos Garcia",
            phone: "+1-555-0301",
            email: "carlos.garcia@example.com",
            relationshipType: "Dad",
          },
          {
            name: "Rosa Martinez",
            phone: "+1-555-0302",
            email: "rosa.martinez@example.com",
            relationshipType: "Other - Grandparent",
          },
        ],
      },
      children: {
        create: [
          {
            firstName: "Isabella",
            lastName: "Garcia",
            birthdate: new Date("2019-07-14"),
            allergies: "Dairy, eggs, tree nuts",
            notes: "Multiple food allergies - please check all snacks",
          },
        ],
      },
    },
    include: {
      children: true,
    },
  });

  // Family 4: Old Family (for GDPR testing)
  const oldFamily = await prisma.family.create({
    data: {
      lastParticipationDate: new Date("2022-01-15"), // Over 2 years ago
      parents: {
        create: [
          {
            name: "Robert Williams",
            phone: "+1-555-0401",
            email: "robert.williams@example.com",
            relationshipType: "Dad",
            lastParticipationDate: new Date("2022-01-15"),
          },
        ],
      },
      children: {
        create: [
          {
            firstName: "Emily",
            lastName: "Williams",
            birthdate: new Date("2016-12-01"),
            lastParticipationDate: new Date("2022-01-15"),
            allergies: null,
            notes: "Last attended over 2 years ago",
          },
        ],
      },
    },
    include: {
      children: true,
    },
  });

  console.log("✅ Families created");

  // ============================================================================
  // Seed Tickets
  // ============================================================================
  console.log("🎫 Creating tickets...");

  // Event passes for Smith children
  await Promise.all(
    smithFamily.children.map((child) =>
      prisma.ticket.create({
        data: {
          type: "EVENT_PASS",
          childId: child.id,
          sessionId: null,
        },
      })
    )
  );

  // Session tickets for Johnson children
  await prisma.ticket.create({
    data: {
      type: "SESSION_TICKET",
      childId: johnsonFamily.children[0]!.id,
      sessionId: summerSessions[1]!.id, // Afternoon Workshop
    },
  });

  await prisma.ticket.create({
    data: {
      type: "SESSION_TICKET",
      childId: johnsonFamily.children[1]!.id,
      sessionId: summerSessions[1]!.id,
    },
  });

  // Mix for Garcia child
  await prisma.ticket.create({
    data: {
      type: "EVENT_PASS",
      childId: garciaFamily.children[0]!.id,
      sessionId: null,
    },
  });

  console.log("✅ Tickets created");

  // ============================================================================
  // Seed Check-In Records
  // ============================================================================
  console.log("✅ Creating check-in records...");

  // Generate QR tokens for children who will be checked in
  const emmaQR = randomUUID();
  const oliverQR = randomUUID();
  const lucasQR = randomUUID();

  // Update children with QR tokens
  await prisma.child.update({
    where: { id: smithFamily.children[0]!.id },
    data: { qrToken: emmaQR },
  });

  await prisma.child.update({
    where: { id: smithFamily.children[1]!.id },
    data: { qrToken: oliverQR },
  });

  await prisma.child.update({
    where: { id: johnsonFamily.children[0]!.id },
    data: { qrToken: lucasQR },
  });

  // Currently checked in (no checkOutTime)
  await prisma.checkInRecord.create({
    data: {
      childId: smithFamily.children[0]!.id, // Emma
      sessionId: summerSessions[0]!.id, // Morning Worship
      checkInStaffId: admin.id,
      checkInTime: new Date(),
    },
  });

  await prisma.checkInRecord.create({
    data: {
      childId: smithFamily.children[1]!.id, // Oliver
      sessionId: summerSessions[0]!.id,
      checkInStaffId: admin.id,
      checkInTime: new Date(),
    },
  });

  // Already checked out
  const now = new Date();
  const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);
  const twoHoursAgo = new Date(now.getTime() - 120 * 60 * 1000);
  const thirtyMinutesAgo = new Date(now.getTime() - 30 * 60 * 1000);

  await prisma.checkInRecord.create({
    data: {
      childId: johnsonFamily.children[0]!.id, // Lucas
      sessionId: summerSessions[0]!.id,
      checkInStaffId: admin.id,
      checkInTime: twoHoursAgo,
      checkOutTime: oneHourAgo,
      pickedUpBy: "Maria Johnson (Mom)",
      checkOutStaffId: admin.id,
    },
  });

  await prisma.checkInRecord.create({
    data: {
      childId: johnsonFamily.children[1]!.id, // Mia
      sessionId: summerSessions[0]!.id,
      checkInStaffId: admin.id,
      checkInTime: twoHoursAgo,
      checkOutTime: oneHourAgo,
      pickedUpBy: "Maria Johnson (Mom)",
      checkOutStaffId: admin.id,
    },
  });

  // Recent check-out (for testing undo feature)
  await prisma.checkInRecord.create({
    data: {
      childId: garciaFamily.children[0]!.id, // Isabella
      sessionId: summerSessions[0]!.id,
      checkInStaffId: admin.id,
      checkInTime: oneHourAgo,
      checkOutTime: thirtyMinutesAgo,
      pickedUpBy: "Carlos Garcia (Dad)",
      checkOutStaffId: admin.id,
    },
  });

  console.log("✅ Check-in records created");

  // ============================================================================
  // Summary
  // ============================================================================
  console.log("\n📊 Seed Summary:");
  console.log(`   👤 Admin Users: ${await prisma.adminUser.count()}`);
  console.log(`   📅 Events: ${await prisma.event.count()}`);
  console.log(`   🎪 Sessions: ${await prisma.session.count()}`);
  console.log(`   👨‍👩‍👧‍👦 Families: ${await prisma.family.count()}`);
  console.log(`   👥 Parents: ${await prisma.parent.count()}`);
  console.log(`   👶 Children: ${await prisma.child.count()}`);
  console.log(`   🎫 Tickets: ${await prisma.ticket.count()}`);
  console.log(`   ✅ Check-ins: ${await prisma.checkInRecord.count()}`);

  console.log("\n✨ Database seeded successfully!");
  console.log(`\n🔐 Admin Login: ${username} / ${password}`);
}

main()
  .catch((e) => {
    console.error("❌ Error seeding database:", e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
