# Traefik Integration for Production Deployment

## Overview

Traefik reverse proxy support has been added to `docker-compose.prod.yml` to enable seamless integration with existing Traefik deployments (e.g., Portainer GitOps setups).

## What Was Changed

### 1. `docker-compose.prod.yml`
- Added external `traefik` network configuration
- Added Traefik labels to the `web` service
- Labels use environment variables for flexibility
- Web service now connects to both internal networks and the traefik network

### 2. `.env.prod.example`
Added new Traefik configuration variables:
```env
TRAEFIK_ENABLE=false              # Set to true to enable
TRAEFIK_HOST=checkins.example.com # Your domain
TRAEFIK_ENTRYPOINT=websecure      # HTTP/HTTPS entrypoint
TRAEFIK_CERTRESOLVER=le           # Certificate resolver
TRAEFIK_NETWORK=traefik           # Traefik network name
```

### 3. `PRODUCTION_DEPLOYMENT.md`
Added comprehensive Traefik setup instructions, including:
- Environment variable configuration
- Portainer GitOps deployment notes
- HTTPS/SSL settings
- Requirements and prerequisites

## Usage

### For Portainer GitOps Deployment

1. Point Portainer to this repository
2. Select `docker-compose.prod.yml` as the compose file
3. Set environment variables in Portainer:
   ```env
   # Traefik Configuration
   TRAEFIK_ENABLE=true
   TRAEFIK_HOST=checkins.yourdomain.com
   TRAEFIK_ENTRYPOINT=websecure
   TRAEFIK_CERTRESOLVER=le
   TRAEFIK_NETWORK=traefik

   # Django Security (for HTTPS)
   ALLOWED_HOSTS=checkins.yourdomain.com,localhost
   CORS_ALLOWED_ORIGINS=https://checkins.yourdomain.com
   CSRF_TRUSTED_ORIGINS=https://checkins.yourdomain.com
   SESSION_COOKIE_SECURE=true
   CSRF_COOKIE_SECURE=true

   # Standard settings (copy from .env.prod.example)
   SECRET_KEY=your-secret-key
   DATABASE_URL=postgresql://...
   # ... etc
   ```

### For Manual Deployment

1. Copy `.env.prod.example` to `.env.prod`
2. Set `TRAEFIK_ENABLE=true` and configure other Traefik variables
3. Deploy: `podman-compose -f docker-compose.prod.yml up -d`

### To Disable Traefik

Set `TRAEFIK_ENABLE=false` (default) to disable Traefik integration and use standard port exposure (port 8080).

## Label Syntax

The implementation uses Traefik v3-compatible label syntax:

```yaml
labels:
  traefik.enable: "true"
  traefik.http.routers.checkins.rule: "Host(`checkins.example.com`)"
  traefik.http.routers.checkins.entrypoints: "websecure"
  traefik.http.routers.checkins.tls.certresolver: "le"
  traefik.docker.network: "traefik"
```

## Network Configuration

- **frontend**: Internal bridge network for web container
- **backend**: Internal bridge network (isolated) for DB/cache
- **traefik**: External network (created by Traefik)

The web service connects to all three networks to enable:
- Database access (backend network)
- Traefik routing (traefik network)
- Container communication (frontend network)

## Requirements

1. Traefik must be running on the host
2. Traefik must have a network (default: `traefik`)
3. Certificate resolver must be configured in Traefik (e.g., Let's Encrypt)
4. The Traefik network name must match `TRAEFIK_NETWORK` setting

## Benefits

- ✅ No manual reverse proxy configuration files needed
- ✅ Automatic SSL/TLS via Let's Encrypt
- ✅ WebSocket support works automatically
- ✅ Easy to enable/disable via environment variables
- ✅ Compatible with Portainer GitOps workflow
- ✅ Can run with or without Traefik (backward compatible)

## Testing

To test without Traefik (direct access on port 8080):
```env
TRAEFIK_ENABLE=false
SESSION_COOKIE_SECURE=false
CSRF_COOKIE_SECURE=false
```

Access at: `http://localhost:8080`
