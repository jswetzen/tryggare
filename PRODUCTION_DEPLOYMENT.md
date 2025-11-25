# Production Deployment Guide

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

## Next Steps

1. **Test current setup** with WebSocket fix
2. **Choose deployment option** based on your needs
3. **Create production Dockerfile** for SvelteKit if using Option 1
4. **Set up Nginx config**
5. **Test in staging environment**
6. **Deploy to production**

Let me know which option you prefer and I can help set it up!
