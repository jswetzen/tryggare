# ============================================
# Base stage - shared dependencies
# ============================================
FROM node:20-alpine AS base

# Install OpenSSL - required by Prisma on Alpine
RUN apk add --no-cache libc6-compat openssl

# Enable corepack for pnpm
RUN corepack enable
RUN corepack prepare pnpm@latest --activate

WORKDIR /app

# ============================================
# Dependencies stage - install all dependencies
# ============================================
FROM base AS dependencies

# Copy package files
COPY package.json pnpm-lock.yaml ./
COPY prisma ./prisma

# Install all dependencies (including dev dependencies) with frozen lockfile
RUN pnpm install --frozen-lockfile

# Generate Prisma client
RUN pnpm prisma generate

# ============================================
# Development stage - for local development with hot reload
# Note: Source code is mounted as a volume in docker-compose.dev.yml
# ============================================
FROM base AS development

WORKDIR /app

# Copy dependencies from dependencies stage
COPY --from=dependencies /app/node_modules ./node_modules

# Copy only essential files needed for runtime
# Source code will be provided by volume mount in docker-compose.dev.yml
COPY package.json pnpm-lock.yaml ./
COPY prisma ./prisma
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Expose port 3000
EXPOSE 3000

# Use entrypoint to run migrations before starting
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["pnpm", "dev"]

# ============================================
# Builder stage - build the application for production
# ============================================
FROM dependencies AS builder

# Copy only necessary source files for build (not COPY . . - too bloated)
COPY src ./src
COPY public ./public
COPY next.config.js tsconfig.json postcss.config.js components.json ./
COPY .env* ./

# Set production environment
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Build arguments - DATABASE_URL passed from docker-compose for build-time access
# Default to dummy value for standalone builds (docker-compose will override)
ARG DATABASE_URL="postgresql://user:pass@localhost:5432/db"
ENV DATABASE_URL=$DATABASE_URL

# Set dummy AUTH_SECRET for build (actual secret will be provided at runtime)
ARG AUTH_SECRET=build-time-dummy-secret-replace-at-runtime
ENV AUTH_SECRET=$AUTH_SECRET
ENV SKIP_ENV_VALIDATION=true

# Build the Next.js application
# This creates a standalone output in .next/standalone
RUN pnpm build

# ============================================
# Init stage - for running migrations
# ============================================
FROM base AS init

WORKDIR /app

# Copy prisma schema and migrations
COPY --from=builder /app/prisma ./prisma

# Install Prisma CLI with exact version matching the client
# This ensures version compatibility
COPY --from=builder /app/node_modules/@prisma/client/package.json /tmp/prisma-version.json
RUN PRISMA_VERSION=$(node --print 'require("/tmp/prisma-version.json").version') && \
    npm install --global --save-exact "prisma@${PRISMA_VERSION}" && \
    rm /tmp/prisma-version.json

# Install bcryptjs for seeding
RUN npm install --global bcryptjs@2.4.3

# Copy Prisma client from builder (needed for seeding script)
COPY --from=builder /app/node_modules/.prisma ./node_modules/.prisma
COPY --from=builder /app/node_modules/@prisma ./node_modules/@prisma

# Copy init entrypoint (before switching to non-root user for chmod)
COPY docker-entrypoint-init.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs && \
    chown -R nextjs:nodejs /app

USER nextjs

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# ============================================
# Runner stage - minimal production runtime
# ============================================
FROM node:20-alpine AS runner

# Install OpenSSL - required by Prisma on Alpine
RUN apk add --no-cache libc6-compat openssl

WORKDIR /app

# Set production environment
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Create a non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy necessary files from builder with proper ownership
# .next/standalone contains the server and all runtime dependencies including Prisma client
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

# Copy Prisma schema (needed for runtime)
COPY --from=builder --chown=nextjs:nodejs /app/prisma ./prisma

# Note: Prisma client is already included in .next/standalone
# No Prisma CLI needed in runner - migrations handled by init container

# Copy production entrypoint script with proper ownership
COPY --chown=nextjs:nodejs docker-entrypoint-prod.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Switch to non-root user
USER nextjs

# Expose port 3000
EXPOSE 3000

# Set hostname
ENV HOSTNAME="0.0.0.0"
ENV PORT=3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000/api/health', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})"

# Use entrypoint to run migrations before starting
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["node", "server.js"]
