const { PrismaClient } = require('@prisma/client');
const bcrypt = require('bcryptjs');

async function seed() {
  const prisma = new PrismaClient();
  try {
    const username = process.env.INITIAL_ADMIN_USERNAME || 'admin';
    const password = process.env.INITIAL_ADMIN_PASSWORD || 'changeme123';

    // Check if admin already exists
    const existing = await prisma.adminUser.findUnique({
      where: { username }
    });

    if (!existing) {
      const passwordHash = await bcrypt.hash(password, 10);
      await prisma.adminUser.create({
        data: {
          username,
          name: 'Administrator',
          passwordHash,
          isActive: true
        }
      });
      console.log('Initial admin user created:', username);
    } else {
      console.log('Admin user already exists:', username);
    }
  } finally {
    await prisma.$disconnect();
  }
}

seed().catch((error) => {
  console.error('Seeding error:', error);
  process.exit(1);
});
