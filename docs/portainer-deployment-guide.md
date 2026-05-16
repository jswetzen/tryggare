# Portainer Stack Deployment Guide

This guide explains how to deploy the Conference Child Management System as a Portainer stack.

## Overview

The `docker-compose.prod.yml` file has been fully parametrized to support easy deployment through Portainer. All configurable values are now defined in `.env.prod` with sensible defaults.

## Deployment Steps

### 1. Prepare Environment File

Copy the contents of `.env.prod` and customize the following key variables for your deployment:

#### Required Changes

```bash
# Change these to match your domain/IP
ALLOWED_HOSTS=yourdomain.com,your-server-ip
CORS_ALLOWED_ORIGINS=https://yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com

# Generate new secure keys (CRITICAL!)
SECRET_KEY=<generate-new-secret-key>
DB_PASSWORD=<generate-strong-password>
REDIS_PASSWORD=<generate-strong-password>

# Update DATABASE_URL with new password (URL-encode special chars)
DATABASE_URL=postgresql://postgres:<url-encoded-password>@db-prod:5432/checkins

# Update VALKEY_URL with new password (URL-encode special chars)
VALKEY_URL=redis://:<url-encoded-password>@valkey-prod:6379/0
```

#### SSL/HTTPS Configuration

If deploying behind a reverse proxy with SSL:

```bash
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
```

If deploying without SSL (not recommended for production):

```bash
SESSION_COOKIE_SECURE=false
CSRF_COOKIE_SECURE=false
```

### 2. Create Portainer Stack

1. Log into your Portainer instance
2. Navigate to **Stacks** > **Add Stack**
3. Name your stack (e.g., `conference-checkin`)
4. Choose **Git Repository** or **Upload from computer**

#### Option A: Git Repository

- Repository URL: Your git repository URL
- Repository reference: `refs/heads/main` (or your branch)
- Compose path: `docker-compose.prod.yml`
- Add your customized environment variables in the **Environment variables** section

#### Option B: Web editor

- Copy the contents of `docker-compose.prod.yml` into the web editor
- Add your customized environment variables in the **Environment variables** section

### 3. Configure Environment Variables in Portainer

In the **Environment variables** section, add each variable from your customized `.env.prod` file:

```
COMPOSE_PROJECT_NAME=conference-checkin
SECRET_KEY=<your-secret-key>
ALLOWED_HOSTS=yourdomain.com
DB_USER=postgres
DB_PASSWORD=<your-db-password>
POSTGRES_DB=checkins
DATABASE_URL=postgresql://postgres:<url-encoded-password>@db-prod:5432/checkins
REDIS_PASSWORD=<your-redis-password>
VALKEY_URL=redis://:<url-encoded-password>@valkey-prod:6379/0
CORS_ALLOWED_ORIGINS=https://yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
WEB_HOST_PORT=8080
... (add all other variables as needed)
```

### 4. Deploy the Stack

Click **Deploy the stack** and wait for all services to start.

## Configurable Parameters

### Core Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `COMPOSE_PROJECT_NAME` | `check-in-prod` | Docker Compose project name |
| `SECRET_KEY` | (required) | Django secret key - MUST be unique and secure |
| `ALLOWED_HOSTS` | (required) | Comma-separated list of allowed hostnames |
| `WEB_HOST_PORT` | `8080` | Port to expose the web service on host |

### Database Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_IMAGE` | `docker.io/postgres:16-alpine` | PostgreSQL Docker image |
| `POSTGRES_DB` | `checkins` | Database name |
| `DB_USER` | `postgres` | Database username |
| `DB_PASSWORD` | (required) | Database password |
| `DATABASE_URL` | (required) | Full PostgreSQL connection URL |

### Cache Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `VALKEY_IMAGE` | `docker.io/valkey/valkey:7-alpine` | Valkey/Redis Docker image |
| `REDIS_PASSWORD` | (required) | Valkey/Redis password |
| `VALKEY_URL` | (required) | Full Valkey connection URL |

### Security Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CORS_ALLOWED_ORIGINS` | (required) | Comma-separated list of allowed CORS origins |
| `CSRF_TRUSTED_ORIGINS` | (required) | Comma-separated list of trusted CSRF origins |
| `SESSION_COOKIE_SECURE` | `false` | Set to `true` for HTTPS deployments |
| `CSRF_COOKIE_SECURE` | `false` | Set to `true` for HTTPS deployments |

### Frontend Build Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_PUBLIC_API_BASE_URL` | (empty) | API base URL - leave empty for relative paths |
| `VITE_PUBLIC_WS_BASE_URL` | (empty) | WebSocket base URL - leave empty for relative paths |

### Resource Limits

#### Web Service
| Variable | Default | Description |
|----------|---------|-------------|
| `WEB_CPU_LIMIT` | `2.0` | Maximum CPU cores |
| `WEB_MEMORY_LIMIT` | `2G` | Maximum memory |
| `WEB_CPU_RESERVATION` | `0.5` | Reserved CPU cores |
| `WEB_MEMORY_RESERVATION` | `512M` | Reserved memory |

#### Database
| Variable | Default | Description |
|----------|---------|-------------|
| `DB_CPU_LIMIT` | `1.0` | Maximum CPU cores |
| `DB_MEMORY_LIMIT` | `1G` | Maximum memory |
| `DB_CPU_RESERVATION` | `0.25` | Reserved CPU cores |
| `DB_MEMORY_RESERVATION` | `256M` | Reserved memory |

#### Cache
| Variable | Default | Description |
|----------|---------|-------------|
| `VALKEY_CPU_LIMIT` | `0.5` | Maximum CPU cores |
| `VALKEY_MEMORY_LIMIT` | `512M` | Maximum memory |
| `VALKEY_CPU_RESERVATION` | `0.1` | Reserved CPU cores |
| `VALKEY_MEMORY_RESERVATION` | `128M` | Reserved memory |

### Logging Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_MAX_SIZE` | `5m` | Maximum log file size |
| `LOG_MAX_FILES` | `3` | Number of log files to retain |

## URL Encoding for Passwords

Special characters in passwords must be URL-encoded when used in connection URLs:

- `/` → `%2F`
- `+` → `%2B`
- `=` → `%3D`
- `@` → `%40`
- `:` → `%3A`
- `?` → `%3F`
- `#` → `%23`
- `&` → `%26`

Example:
- Password: `qfON/YM+Uc=`
- Encoded: `qfON%2FYM%2BUc%3D`

## Post-Deployment

### 1. Verify Services

Check that all three services are running:
- `web` - Django application serving frontend and API
- `db-prod` - PostgreSQL database
- `valkey-prod` - Valkey cache

### 2. Create Superuser

Access the web container and create an admin user:

```bash
docker exec -it <container-name> sh
uv run python manage.py createsuperuser
```

### 3. Access the Application

- Application: `http://your-server:8080` (or your configured port)
- Admin panel: `http://your-server:8080/admin`

### 4. Configure Reverse Proxy (Recommended)

For production deployments, set up a reverse proxy (Nginx, Caddy, Traefik) to:
- Provide SSL/TLS termination
- Handle static file serving efficiently
- Provide additional security headers

Example Nginx configuration:

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws/ {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

## Security Checklist

- [ ] Generated new unique `SECRET_KEY`
- [ ] Set strong passwords for `DB_PASSWORD` and `REDIS_PASSWORD`
- [ ] Updated `ALLOWED_HOSTS` to match your domain
- [ ] Configured `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` correctly
- [ ] Set `SESSION_COOKIE_SECURE=true` and `CSRF_COOKIE_SECURE=true` for HTTPS
- [ ] Properly URL-encoded passwords in connection URLs
- [ ] Configured reverse proxy with SSL/TLS
- [ ] Reviewed and adjusted resource limits for your hardware
- [ ] Set up regular database backups
- [ ] Configured log rotation appropriately

## Backup and Restore

### Backup Database

```bash
docker exec <db-container> pg_dump -U postgres checkins > backup.sql
```

### Restore Database

```bash
cat backup.sql | docker exec -i <db-container> psql -U postgres checkins
```

### Persistent Data

The following Docker volumes store persistent data:
- `pg_data_prod` - PostgreSQL database files

Ensure these volumes are included in your backup strategy.

## Troubleshooting

### Container won't start

Check logs in Portainer or via:
```bash
docker logs <container-name>
```

### Database connection errors

Verify:
- `DATABASE_URL` is correctly formatted
- Password is properly URL-encoded
- Database service is healthy

### CORS/CSRF errors

Ensure:
- `ALLOWED_HOSTS` includes your domain
- `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` match the URLs users access
- Protocol (http/https) matches your deployment

### SSL/Cookie issues

If using HTTPS, ensure:
- `SESSION_COOKIE_SECURE=true`
- `CSRF_COOKIE_SECURE=true`
- Reverse proxy is forwarding `X-Forwarded-Proto` header

## Support

For issues or questions, refer to:
- Project documentation in `/docs`
- Architecture: [`architecture.md`](architecture.md)
- Specification: [`specification.md`](specification.md)
