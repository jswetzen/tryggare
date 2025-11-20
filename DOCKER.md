# Docker Configuration Guide

This project supports both development and production Docker deployments through separate Docker Compose configurations.

## Quick Start

### Development
```bash
# Start development environment with hot reload
docker-compose -f docker-compose.dev.yml up

# Rebuild and start (if Dockerfile changed)
docker-compose -f docker-compose.dev.yml up --build

# Stop
docker-compose -f docker-compose.dev.yml down
```

### Production
```bash
# Set required environment variables
export AUTH_SECRET="your-production-secret-key-here"
export NEXTAUTH_SECRET="your-production-secret-key-here"
export INITIAL_ADMIN_PASSWORD="your-secure-password"

# Build and start production environment
docker-compose -f docker-compose.prod.yml up --build

# Stop
docker-compose -f docker-compose.prod.yml down
```

## Architecture

### Dockerfile Stages

The Dockerfile uses multi-stage builds to optimize for different use cases:

1. **base**: Node.js 20 Alpine with pnpm enabled
2. **dependencies**: Installs all dependencies and generates Prisma client
3. **development**: For local development with hot reload (copies all files, overridden by volume mount)
4. **builder**: Builds the Next.js application for production
5. **runner**: Minimal production runtime with standalone Next.js output

**Note on Development Stage**: The development stage copies all source files (`COPY . .`) to ensure the image can run standalone. When using docker-compose.dev.yml, the volume mount (`.:/app`) overrides these files, providing hot reload functionality while preserving the container's `node_modules`.

### docker-compose.dev.yml (Development)

**Purpose**: Fast local development with hot reload

**Features**:
- Mounts source code as volume for instant hot reload
- Includes all dev dependencies
- Runs `pnpm dev --turbo` for fast refresh
- Separate database volume (`postgres_data_dev`)
- Container names suffixed with `-dev`

**Volume Mounts**:
- `.:/app` - Source code (enables hot reload)
- `/app/node_modules` - Prevents host overwriting container node_modules
- `/app/.next` - Prevents host overwriting build artifacts

**Usage**:
```bash
# First run (builds image)
docker-compose -f docker-compose.dev.yml up --build

# Subsequent runs (uses cached image)
docker-compose -f docker-compose.dev.yml up

# View logs
docker-compose -f docker-compose.dev.yml logs -f app

# Access database
docker-compose -f docker-compose.dev.yml exec db psql -U postgres -d conference-child-mgmt

# Run migrations manually
docker-compose -f docker-compose.dev.yml exec app pnpm prisma migrate dev

# Access shell
docker-compose -f docker-compose.dev.yml exec app sh
```

### docker-compose.prod.yml (Production)

**Purpose**: Optimized production deployment

**Features**:
- Uses standalone Next.js output (~100MB smaller)
- No dev dependencies in final image
- Runs as non-root user (nextjs:nodejs)
- Environment variable validation
- Resource limits (2 CPU, 2GB RAM)
- Health checks enabled
- Separate database volume (`postgres_data_prod`)

**Environment Variables**:

Required:
- `AUTH_SECRET` - NextAuth secret key
- `NEXTAUTH_SECRET` - Legacy NextAuth secret
- `INITIAL_ADMIN_PASSWORD` - Admin user password

Optional (with defaults):
- `POSTGRES_DB` (default: conference-child-mgmt)
- `POSTGRES_USER` (default: postgres)
- `POSTGRES_PASSWORD` (default: password)
- `DB_PORT` (default: 5432)
- `APP_PORT` (default: 3000)
- `NEXTAUTH_URL` (default: http://localhost:3000)
- `INITIAL_ADMIN_USERNAME` (default: admin)

**Usage**:
```bash
# Create .env.production file
cat > .env.production << EOF
AUTH_SECRET=$(openssl rand -base64 32)
NEXTAUTH_SECRET=$(openssl rand -base64 32)
INITIAL_ADMIN_PASSWORD=your-secure-password-here
NEXTAUTH_URL=https://your-domain.com
POSTGRES_PASSWORD=secure-db-password
EOF

# Load and start
set -a; source .env.production; set +a
docker-compose -f docker-compose.prod.yml up --build -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f app

# Check health
docker-compose -f docker-compose.prod.yml ps
```

## Image Sizes

Approximate sizes:
- Development image: ~800MB (includes all dev dependencies)
- Production image: ~200MB (standalone output, no dev dependencies)

## Database Volumes

Development and production use separate named volumes:
- `postgres_data_dev` - Development database
- `postgres_data_prod` - Production database

This prevents data conflicts when switching between environments.

### Backup Database

```bash
# Development
docker-compose -f docker-compose.dev.yml exec db pg_dump -U postgres conference-child-mgmt > backup-dev.sql

# Production
docker-compose -f docker-compose.prod.yml exec db pg_dump -U postgres conference-child-mgmt > backup-prod.sql
```

### Restore Database

```bash
# Development
docker-compose -f docker-compose.dev.yml exec -T db psql -U postgres conference-child-mgmt < backup-dev.sql

# Production
docker-compose -f docker-compose.prod.yml exec -T db psql -U postgres conference-child-mgmt < backup-prod.sql
```

## Troubleshooting

### Hot reload not working in development

1. Ensure volume is mounted correctly:
   ```bash
   docker-compose -f docker-compose.dev.yml exec app ls -la /app
   ```

2. Check if Next.js dev server is running:
   ```bash
   docker-compose -f docker-compose.dev.yml logs -f app
   ```

3. Restart the container:
   ```bash
   docker-compose -f docker-compose.dev.yml restart app
   ```

### Production build fails

1. Check if standalone output is enabled in `next.config.js`:
   ```javascript
   output: 'standalone'
   ```

2. Verify build logs:
   ```bash
   docker-compose -f docker-compose.prod.yml logs builder
   ```

3. Try building locally first:
   ```bash
   pnpm build
   ```

### Database connection issues

1. Wait for database health check:
   ```bash
   docker-compose -f docker-compose.dev.yml ps
   ```

2. Check database logs:
   ```bash
   docker-compose -f docker-compose.dev.yml logs db
   ```

3. Test connection manually:
   ```bash
   docker-compose -f docker-compose.dev.yml exec app pnpm prisma db push
   ```

### Permission issues

If you encounter permission errors with mounted volumes:

```bash
# Fix ownership (development)
docker-compose -f docker-compose.dev.yml exec app chown -R node:node /app
```

## Best Practices

1. **Never commit secrets**: Use environment variables or `.env` files (add to `.gitignore`)
2. **Separate volumes**: Development and production use different database volumes
3. **Health checks**: Both configurations include health checks for reliability
4. **Resource limits**: Production has CPU and memory limits to prevent resource exhaustion
5. **Migrations**: Run automatically via entrypoint scripts (`prisma migrate deploy`)

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Build and Push Docker Image

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build production image
        run: docker-compose -f docker-compose.prod.yml build

      - name: Run tests
        run: docker-compose -f docker-compose.prod.yml run app pnpm test:run

      - name: Push to registry
        # Add your registry push steps here
```

## Additional Resources

- [Next.js Standalone Output](https://nextjs.org/docs/app/api-reference/next-config-js/output)
- [Docker Multi-Stage Builds](https://docs.docker.com/build/building/multi-stage/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Prisma in Docker](https://www.prisma.io/docs/orm/more/development-environment/environment-variables)
