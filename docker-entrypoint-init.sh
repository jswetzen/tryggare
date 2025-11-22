#!/bin/sh
set -e

echo "=== Database Migration Init Container ==="
echo "Waiting for database to be ready..."
echo "DATABASE_URL: ${DATABASE_URL}"

# Wait for database to be ready
# Using a simpler approach that works reliably
MAX_TRIES=30
TRY=0
until [ $TRY -ge $MAX_TRIES ]
do
  echo "Attempting database connection (try $((TRY+1))/$MAX_TRIES)..."
  if pnpm exec prisma db execute --stdin <<EOF
SELECT 1;
EOF
  then
    echo "Database is ready!"
    break
  fi
  TRY=$((TRY+1))
  if [ $TRY -ge $MAX_TRIES ]; then
    echo "Failed to connect to database after $MAX_TRIES attempts"
    exit 1
  fi
  echo "Database not ready, waiting..."
  sleep 2
done

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
