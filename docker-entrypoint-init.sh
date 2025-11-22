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
  if pnpm exec prisma db execute --schema=./prisma/schema.prisma --stdin <<EOF
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
echo "Current directory: $(pwd)"
echo "Checking for node_modules..."
ls -la node_modules/@prisma/ 2>/dev/null || echo "No @prisma in node_modules"
ls -la node_modules/bcryptjs/ 2>/dev/null || echo "No bcryptjs in node_modules"
echo "Running seed script..."
node seed-admin.js

echo ""
echo "=== Migration and seeding complete! ==="
