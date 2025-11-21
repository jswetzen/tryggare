#!/bin/sh
set -e

echo "=== Starting Next.js Application ==="
echo "Migrations and seeding are handled by the init container"
echo "Starting application server..."
echo ""

exec "$@"
