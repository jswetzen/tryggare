#!/bin/sh
set -e

# Check if node_modules exists, if not install dependencies
# This handles the case where volume mounts wipe out node_modules
if [ ! -d "node_modules" ] || [ ! -f "node_modules/.bin/next" ]; then
  echo "Installing dependencies..."
  pnpm install --frozen-lockfile
fi

echo "Running database migrations..."
pnpm prisma migrate deploy

echo "Starting application..."
exec "$@"
