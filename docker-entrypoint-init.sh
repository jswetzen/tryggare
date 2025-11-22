#!/bin/sh
set -e

echo "=== Database Migration Init Container ==="
echo "Waiting for database to be ready..."

# Wait for database to be ready
until pnpm exec prisma db execute --stdin <<EOF 2>/dev/null
SELECT 1;
EOF
do
  echo "Database is unavailable - sleeping"
  sleep 2
done

echo "Database is ready!"
echo ""

echo "Running database migrations..."
pnpm exec prisma migrate deploy

echo ""
echo "Seeding database with initial admin user..."
node -e "
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
    await prisma.\$disconnect();
  }
}

seed().catch((error) => {
  console.error('Seeding error:', error);
  process.exit(1);
});
"

echo ""
echo "=== Migration and seeding complete! ==="
