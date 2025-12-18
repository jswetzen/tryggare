# Production Deployment Guide - Static Build

This guide covers deploying the Conference Child Management System using **Static Build Served by Django** - where Django serves both the API and the built SvelteKit frontend as static files from a single port (8000).

**Note**: This guide is also used for **local "production-style" testing** - running the production configuration locally in Podman containers (not on a remote server). The setup at `docker-compose.prod.yml` runs on `localhost:8080` for testing purposes.

## Quick Start

```bash
# 1. Create production environment file
cp .env.prod.example .env.prod

# 2. Edit .env.prod with your actual values (SECRET_KEY, domain, etc.)
nano .env.prod

# 3. Build and start production services
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d --build

# 4. Create superuser
docker-compose -f docker-compose.prod.yml exec web uv run python manage.py createsuperuser

# 5. Access at http://localhost:8080
```

**Note**: Production setup runs on port **8080** (not 8000) so you can run dev servers alongside it.

**Local Testing**: This production configuration is often run locally for testing. See [VERIFICATION_GUIDE.md](./VERIFICATION_GUIDE.md) for comprehensive testing workflows.

For detailed instructions including reverse proxy setup, see sections below.

---

## Current Setup (Development)

**Architecture:**
- Django (port 8000) - API + WebSocket server
- SvelteKit (port 5173) - Dev server with HMR
- Browser connects to both separately

**Pros:**
- Hot module reloading (HMR) for fast development
- Easy debugging with separate logs

**Cons:**
- Two ports to manage
- CORS complexity
- WebSocket URL configuration needed

## Recommended Production Setup

### Option 1: SvelteKit Adapter + Reverse Proxy (Recommended)

**Architecture:**
```
Browser → Nginx/Caddy → Django (static files + API + WebSocket)
                      → SvelteKit Node server (SSR pages)
```

**Steps:**

1. **Build SvelteKit for production**:
   ```bash
   cd frontend
   pnpm build
   ```

2. **Use SvelteKit adapter-node**:
   - Already configured in `svelte.config.js`
   - Outputs to `.svelte-kit/output`
   - Run with: `node build/index.js`

3. **Configure Nginx**:
   ```nginx
   server {
       listen 80;
       server_name yourdomain.com;

       # SvelteKit SSR
       location / {
           proxy_pass http://localhost:3000;  # SvelteKit node server
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection 'upgrade';
           proxy_set_header Host $host;
       }

       # Django API
       location /api {
           proxy_pass http://localhost:8000;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header Host $host;
       }

       # Django Admin
       location /admin {
           proxy_pass http://localhost:8000;
       }

       # WebSocket
       location /ws {
           proxy_pass http://localhost:8000;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
       }

       # Django static files
       location /static {
           alias /path/to/staticfiles;
       }
   }
   ```

4. **Update environment variables**:
   ```env
   # .env.production
   VITE_API_BASE_URL=https://yourdomain.com/api
   VITE_PUBLIC_WS_BASE_URL=wss://yourdomain.com/ws
   ```

5. **Docker Compose for production**:
   ```yaml
   services:
     web:
       # Django with Daphne
       command: daphne -b 0.0.0.0 -p 8000 config.asgi:application

     frontend:
       # Build and run SvelteKit
       command: sh -c "pnpm build && node build/index.js"
       environment:
         - PORT=3000

     nginx:
       # Reverse proxy
       ports:
         - "80:80"
         - "443:443"
   ```

**Pros:**
- SSR (Server-Side Rendering) works
- SEO friendly
- Fast page loads
- Each service can scale independently

**Cons:**
- More complex setup
- Need to run SvelteKit Node server

---

### Option 2: Static Build Served by Django

**Architecture:**
```
Browser → Django → Static SvelteKit files + API + WebSocket
```

**Steps:**

1. **Switch to static adapter**:
   ```javascript
   // svelte.config.js
   import adapter from '@sveltejs/adapter-static';

   export default {
     kit: {
       adapter: adapter({
         pages: 'build',
         assets: 'build',
         fallback: 'index.html',
         precompress: false
       })
     }
   };
   ```

2. **Build SvelteKit**:
   ```bash
   cd frontend
   pnpm build
   # Output: frontend/build/
   ```

3. **Serve from Django**:
   ```python
   # urls.py
   from django.urls import path, re_path
   from django.views.generic import TemplateView

   urlpatterns = [
       path('admin/', admin.site.urls),
       path('api/', include('your_api.urls')),
       path('ws/', include('your_ws.urls')),

       # Serve SvelteKit app
       re_path(r'^.*$', TemplateView.as_view(template_name='index.html')),
   ]
   ```

4. **Copy built files to Django static**:
   ```bash
   # After building SvelteKit
   cp -r frontend/build/* backend/static/
   ```

5. **Update settings**:
   ```python
   # settings.py
   TEMPLATES = [{
       'DIRS': [BASE_DIR / 'static'],
   }]

   STATICFILES_DIRS = [BASE_DIR / 'static']
   ```

**Pros:**
- Single server/port
- Simpler deployment
- No CORS issues
- Fewer moving parts

**Cons:**
- No SSR (client-side only)
- Worse SEO
- Larger initial bundle
- Need to rebuild frontend for every change

---

### Option 3: Full Static + CDN (Current Development Path)

**Architecture:**
```
Browser → CDN (SvelteKit static) + Django (API + WebSocket)
```

**Best for:** JAMstack approach with separated frontend/backend

**Pros:**
- Best performance (CDN edge caching)
- Independent scaling
- Can use services like Vercel/Netlify for frontend

**Cons:**
- Still need CORS
- WebSocket configuration more complex
- More services to manage

---

## Recommendation

**For your use case (internal conference tool):**

### Go with Option 1: Adapter-node + Nginx

**Why:**
1. ✅ SSR works (better UX)
2. ✅ Single domain (no CORS complexity)
3. ✅ WebSocket works seamlessly
4. ✅ Can scale each service independently
5. ✅ Standard production pattern

**Quick Start:**

```bash
# 1. Create production docker-compose
cat > docker-compose.prod.yml << 'EOF'
version: '3.9'

services:
  web:
    build: ./backend
    command: daphne -b 0.0.0.0 -p 8000 config.asgi:application
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.production
    ports:
      - "8000:8000"
    depends_on:
      - db
      - valkey

  frontend:
    build: ./frontend
    command: sh -c "pnpm build && node build/index.js"
    environment:
      - PORT=3000
      - ORIGIN=https://yourdomain.com
      - VITE_API_BASE_URL=http://web:8000/api
      - VITE_PUBLIC_WS_BASE_URL=wss://yourdomain.com/ws
    ports:
      - "3000:3000"
    depends_on:
      - web

  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./backend/staticfiles:/var/www/static:ro
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - web
      - frontend

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: checkins
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pg_data:/var/lib/postgresql/data

  valkey:
    image: valkey/valkey:7-alpine
    volumes:
      - valkey_data:/data

volumes:
  pg_data:
  valkey_data:
EOF

# 2. Run
docker-compose -f docker-compose.prod.yml up -d
```

## WebSocket in Production

**Important:** Use WSS (WebSocket Secure) in production:

```env
VITE_PUBLIC_WS_BASE_URL=wss://yourdomain.com/ws
```

**SSL Certificate:**
- Use Let's Encrypt with Certbot
- Or use Cloudflare (handles SSL automatically)

**Django Channels with SSL:**
Daphne handles WSS automatically when behind a reverse proxy with SSL termination.

## Environment Variables Summary

### Development (Docker)
```env
# Server-side (SvelteKit → Django)
VITE_API_BASE_URL=http://web:8000

# Client-side (Browser → Django)
VITE_PUBLIC_WS_BASE_URL=ws://localhost:8000
```

### Production
```env
# Server-side (SvelteKit → Django, internal)
VITE_API_BASE_URL=http://web:8000/api

# Client-side (Browser → Nginx → Django)
VITE_PUBLIC_WS_BASE_URL=wss://yourdomain.com/ws
```

## Checklist for Production

- [ ] Switch to production Django settings
- [ ] Set strong SECRET_KEY
- [ ] Set DEBUG=False
- [ ] Configure ALLOWED_HOSTS
- [ ] Set up SSL/TLS certificates
- [ ] Configure session backend (Redis/Valkey)
- [ ] Set up proper logging
- [ ] Configure static file serving
- [ ] Set up database backups
- [ ] Configure rate limiting
- [ ] Set up monitoring (Sentry, etc.)
- [ ] Use environment secrets management
- [ ] Set secure cookie settings (Secure, SameSite)
- [ ] Configure CORS properly
- [ ] Set up health checks
- [ ] Configure WebSocket timeouts

---

## Reverse Proxy Setup (Nginx/Caddy)

For production, use a reverse proxy like Nginx or Caddy for SSL termination and security.

### Port Configuration

- **Container internal port**: 8000 (Django/Daphne)
- **Host exposed port**: 8080 (configured in docker-compose.prod.yml)
- **Reverse proxy**: Points to `localhost:8080`

### Important: No Hardcoded URLs!

The application is **fully configurable** via environment variables. No URLs or ports are hardcoded:

**Frontend** (all configurable, with fallback defaults for dev):
- Server-side API calls: `VITE_API_BASE_URL` (default: `http://localhost:8000`)
- Client-side API calls: `VITE_PUBLIC_API_BASE_URL` (default: `http://localhost:8000/api`)
- WebSocket URL: `VITE_PUBLIC_WS_BASE_URL` (default: `ws://localhost:8000`)

**Backend** (all from Django settings):
- Uses `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` from `.env.prod`
- Handles `X-Forwarded-Proto` header for SSL (already configured in `config/settings/prod.py`)

### Environment Variables for Reverse Proxy

When using a reverse proxy with SSL on `https://yourdomain.com`:

```env
# .env.prod
SECRET_KEY=your-generated-secret-key
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
```

### Traefik Example (Recommended for Container Environments)

Traefik integration is built into `docker-compose.prod.yml` and can be enabled via environment variables.

**Configuration in `.env.prod` or Portainer environment variables:**
```env
# Enable Traefik
TRAEFIK_ENABLE=true
TRAEFIK_HOST=checkins.yourdomain.com
TRAEFIK_ENTRYPOINT=websecure
TRAEFIK_CERTRESOLVER=le
TRAEFIK_NETWORK=traefik

# Django settings for HTTPS
ALLOWED_HOSTS=checkins.yourdomain.com,localhost
CORS_ALLOWED_ORIGINS=https://checkins.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://checkins.yourdomain.com
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
```

**What it does:**
- Automatically routes traffic from your domain to the container
- Handles SSL/TLS with Let's Encrypt (or your configured cert resolver)
- WebSocket support is automatic
- No manual reverse proxy configuration needed

**Requirements:**
- Traefik must be running with a network named `traefik` (or set `TRAEFIK_NETWORK` to your network name)
- Your Traefik instance should have the certificate resolver configured (e.g., `le` for Let's Encrypt)

**For Portainer GitOps:**
Point Portainer to this repository and set the environment variables above. The stack will automatically integrate with your existing Traefik instance.

### Caddy Example (Recommended - Auto SSL)

```caddy
yourdomain.com {
    reverse_proxy localhost:8080
}
```

Caddy automatically handles:
- SSL certificates (Let's Encrypt)
- HTTP to HTTPS redirect
- Header forwarding (`X-Forwarded-Proto`, etc.)
- WebSocket upgrades

### Nginx Example

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    # SSL configuration (use certbot for Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Proxy to Django on port 8080
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Increase timeouts for WebSocket
    proxy_read_timeout 86400;
    proxy_send_timeout 86400;
}
```

### Testing Without Reverse Proxy (Direct Access on 8080)

For local testing on port 8080 without SSL:

```env
# .env.prod (local testing)
SECRET_KEY=your-generated-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:8080
CSRF_TRUSTED_ORIGINS=http://localhost:8080
SESSION_COOKIE_SECURE=false
CSRF_COOKIE_SECURE=false
```

Access at: `http://localhost:8080`

---

## Static Build Implementation (NEW)

This has been implemented using the static adapter approach. See the quick start guide at the top.

### What Was Configured

1. ✅ SvelteKit configured with `@sveltejs/adapter-static`
2. ✅ Production Dockerfile for frontend (`frontend/Dockerfile.prod`)
3. ✅ Production Dockerfile for backend (`backend/Dockerfile.prod`)
4. ✅ Production docker-compose file (`docker-compose.prod.yml`)
5. ✅ Django configured to serve SPA (`config/urls.py`)
6. ✅ Environment template (`.env.prod.example`)
7. ✅ Build-time auth bypass for SPA fallback generation

**Note on Authentication During Build**: The app uses server-side authentication hooks, which would normally prevent the SPA fallback page from being generated during build. The solution is to set `BUILDING=true` environment variable during the build process, which tells `hooks.server.ts` to skip authentication checks. This is configured in `frontend/Dockerfile.prod`.

### Architecture

```
Browser → :8000 → Django
                   ├── /api/* → REST API
                   ├── /admin → Django Admin
                   ├── /qr/* → QR endpoints
                   ├── /static/* → WhiteNoise (CSS, JS, images)
                   └── /* → index.html (SPA)
```

### Build Process (Multi-Stage Dockerfile)

The production build uses a **single multi-stage Dockerfile** (`backend/Dockerfile.prod`):

**Stage 1 - Frontend Builder**:
1. Node.js Alpine image builds the SvelteKit app
2. Runs `pnpm build` with `BUILDING=true` to skip auth during prerender
3. Creates static files in `/app/build`

**Stage 2 - Backend**:
1. Python image with uv installs Django dependencies
2. Copies frontend build from Stage 1 into `/app/staticfiles/`
3. Django's `collectstatic` gathers all static files
4. WhiteNoise serves static files efficiently
5. SPA handles client-side routing

**Benefits**:
- Single image contains both frontend and backend
- No separate frontend-builder service needed
- Cleaner architecture - frontend is built once during image build
- Smaller final image (multi-stage build discards build tools)

---

## Troubleshooting

### `DisallowedHost: Invalid HTTP_HOST header`

**Error**: `django.core.exceptions.DisallowedHost: Invalid HTTP_HOST header: '192.168.1.164:8080'`

**Solution**: Add the IP address or hostname to `ALLOWED_HOSTS` in `.env.prod` - **without the port**:

```env
# ✅ Correct - no port
ALLOWED_HOSTS=192.168.1.164,localhost

# ❌ Wrong - includes port
ALLOWED_HOSTS=192.168.1.164:8080
```

Django automatically handles ports. The `ALLOWED_HOSTS` setting only validates the hostname/IP part of the `Host` header.

For CORS and CSRF, you **do** need to include the port:
```env
CORS_ALLOWED_ORIGINS=http://192.168.1.164:8080,http://localhost:8080
CSRF_TRUSTED_ORIGINS=http://192.168.1.164:8080,http://localhost:8080
```

### Frontend not loading
- Verify static files exist: `docker-compose -f docker-compose.prod.yml exec web-prod ls -la /app/staticfiles`
- Check build logs: `docker-compose -f docker-compose.prod.yml logs web-prod | grep -i "build\|frontend"`

### API errors
- Check backend logs: `docker-compose -f docker-compose.prod.yml logs web-prod`
- Verify environment variables: `docker-compose -f docker-compose.prod.yml exec web-prod env | grep -E "ALLOWED_HOSTS|CORS|CSRF"`

### Database connection issues
- Check database is running: `docker-compose -f docker-compose.prod.yml ps db-prod`
- Verify DATABASE_URL is correct
- Check database logs: `docker-compose -f docker-compose.prod.yml logs db-prod`

---

## Next Steps

1. Copy `.env.prod.example` to `.env.prod` and configure
2. **Set ALLOWED_HOSTS** to your IP/domain (no port): `ALLOWED_HOSTS=192.168.1.164,localhost`
3. Run `docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d --build`
4. Create superuser and test the deployment
5. Set up reverse proxy (Nginx/Caddy) with SSL for production
6. Configure monitoring and backups
