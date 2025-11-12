# Conference Child Management System

A comprehensive check-in/check-out system for managing children at conference events.

## Getting Started

### Prerequisites

- Docker and Docker Compose installed
- Node.js 20+ (for local development without Docker)
- pnpm (package manager)

### Environment Setup

1. Copy the environment variables template:
   ```bash
   cp .env.example .env
   ```

2. Update the `.env` file with your configuration (especially in production):
   - Generate a secure `NEXTAUTH_SECRET`: `openssl rand -base64 32`
   - Set appropriate admin credentials
   - Configure database connection string if not using Docker

## Docker Development

### Start Services

Start all services (PostgreSQL database + Next.js application):
```bash
docker-compose up -d
```

The application will be available at: http://localhost:3000

### View Logs

View application logs:
```bash
docker-compose logs -f app
```

View database logs:
```bash
docker-compose logs -f db
```

View all logs:
```bash
docker-compose logs -f
```

### Stop Services

Stop all services:
```bash
docker-compose down
```

Stop services and remove volumes (⚠️ this will delete all data):
```bash
docker-compose down -v
```

### Database Operations in Docker

#### Access PostgreSQL Database

Connect to the PostgreSQL container:
```bash
docker exec -it conference-db psql -U postgres -d conference-child-mgmt
```

#### Run Prisma Migrations

Run migrations:
```bash
docker-compose exec app pnpm prisma migrate dev
```

Generate Prisma client:
```bash
docker-compose exec app pnpm prisma generate
```

#### Seed Database

Seed the database with initial data:
```bash
docker-compose exec app pnpm prisma db seed
```

Reset database and re-seed:
```bash
docker-compose exec app pnpm prisma migrate reset
```

## Local Development (Without Docker)

If you prefer to develop without Docker:

1. Ensure PostgreSQL is running locally on port 5432
2. Update `.env` with your local database connection string
3. Install dependencies:
   ```bash
   pnpm install
   ```
4. Generate Prisma client:
   ```bash
   pnpm prisma generate
   ```
5. Run migrations:
   ```bash
   pnpm prisma migrate dev
   ```
6. Seed database:
   ```bash
   pnpm prisma db seed
   ```
7. Start development server:
   ```bash
   pnpm dev
   ```

## Tech Stack

- **Framework:** Next.js 15 with App Router
- **Language:** TypeScript
- **API Layer:** tRPC
- **Database:** PostgreSQL with Prisma ORM
- **Authentication:** NextAuth.js
- **Styling:** Tailwind CSS + shadcn/ui
- **Internationalization:** next-intl

## Project Structure

```
src/
├── features/          # Feature-based modules
│   ├── auth/         # Authentication
│   ├── families/     # Family management
│   ├── children/     # Child management
│   ├── sessions/     # Session management
│   ├── check-in/     # Check-in functionality
│   ├── check-out/    # Check-out functionality
│   └── admin/        # Admin features
├── components/        # React components
│   ├── ui/           # shadcn/ui components
│   └── shared/       # Shared components
├── lib/              # Utility functions
└── server/           # Server-side code
    └── api/          # tRPC routers
```

## Documentation

- [Project Specification](./PROJECT_SPECIFICATION.md) - Detailed requirements
- [Technical Design](./TECHNICAL_DESIGN.md) - Architecture and technical details
- [Implementation Plan](./IMPLEMENTATION_PLAN.md) - Development roadmap

## License

Private project - All rights reserved
