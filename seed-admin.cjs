// Import from custom output location (see prisma/schema.prisma generator config)
const { PrismaClient } = require('./generated/prisma');
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
      console.log('Creating admin user with username:', username);
      console.log('Password length:', password.length);
      const passwordHash = await bcrypt.hash(password, 10);
      console.log('Generated password hash:', passwordHash);
      console.log('Hash length:', passwordHash.length);

      await prisma.adminUser.create({
        data: {
          username,
          name: 'Administrator',
          passwordHash,
          isActive: true
        }
      });
      console.log('Initial admin user created:', username);

      // Verify the hash works immediately after creation
      const testCompare = await bcrypt.compare(password, passwordHash);
      console.log('Immediate hash verification:', testCompare ? 'SUCCESS' : 'FAILED');
    } else {
      console.log('Admin user already exists:', username);
      console.log('Existing user passwordHash:', existing.passwordHash);
      console.log('Testing password against existing hash...');
      const testCompare = await bcrypt.compare(password, existing.passwordHash);
      console.log('Hash verification:', testCompare ? 'SUCCESS' : 'FAILED');
    }
  } finally {
    await prisma.$disconnect();
  }
}

seed().catch((error) => {
  console.error('Seeding error:', error);
  process.exit(1);
});
