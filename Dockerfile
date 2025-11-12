# Base stage - shared dependencies
FROM node:20-alpine AS base

# Enable corepack for pnpm
RUN corepack enable
RUN corepack prepare pnpm@latest --activate

WORKDIR /app

# Dependencies stage - install all dependencies
FROM base AS dependencies

# Copy package files
COPY package.json pnpm-lock.yaml ./
COPY prisma ./prisma

# Install dependencies
RUN pnpm install --frozen-lockfile

# Generate Prisma client with Alpine Linux support
RUN pnpm prisma generate

# Development stage
FROM base AS development

WORKDIR /app

# Copy dependencies from dependencies stage
COPY --from=dependencies /app/node_modules ./node_modules
COPY --from=dependencies /app/generated ./generated

# Copy all source files
COPY . .

# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Expose port 3000
EXPOSE 3000

# Use entrypoint to run migrations before starting
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["pnpm", "dev"]

# Builder stage - build the application
FROM dependencies AS builder

# Copy all source files
COPY . .

# Set production environment
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Build the Next.js application
RUN pnpm build

# Runner stage - production runtime
FROM node:20-alpine AS runner

WORKDIR /app

# Set production environment
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Install Prisma CLI for running migrations
RUN corepack enable && corepack prepare pnpm@latest --activate
RUN pnpm add -g prisma@6.19.0

# Create a non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy necessary files from builder
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/generated ./generated
COPY --from=builder /app/prisma ./prisma
COPY --from=builder /app/package.json ./package.json

# Copy production entrypoint script
COPY docker-entrypoint-prod.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Set correct permissions
RUN chown -R nextjs:nodejs /app

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
