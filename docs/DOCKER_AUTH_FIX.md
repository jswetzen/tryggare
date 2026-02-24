# Docker Authentication Fix

## Issues Fixed

### 1. Connection Refused Error (ECONNREFUSED)
**Problem**: Frontend container couldn't connect to backend at `localhost:8000`

**Root Cause**: In Docker, `localhost` refers to the container itself, not the host machine or other containers.

**Solution**: Changed `VITE_API_BASE_URL` from `http://localhost:8000` to `http://web:8000` (using Docker service name)

### 2. TypeScript Configuration Warnings
**Problem**: Two tsconfig.json issues:
- Not extending `.svelte-kit/tsconfig.json`
- Defining `paths` which conflicts with SvelteKit's auto-generated config

**Solution**:
- Updated `frontend/tsconfig.json` to extend the SvelteKit-generated config
- Removed `paths` configuration (already defined in `svelte.config.js` via `kit.alias`)

### 3. Server-Side Environment Variables
**Problem**: `process.env.VITE_API_BASE_URL` wasn't available in server-side code

**Solution**: Changed to use SvelteKit's `$env/dynamic/private` API for accessing environment variables at runtime

### 4. Redirect Being Caught as Error
**Problem**: Login action's `throw redirect()` was being caught by try-catch block, showing "Login error: Redirect"

**Solution**: Moved the redirect outside the try-catch block so it's not caught as an error

## Files Changed

### 1. docker-compose.yml
```yaml
environment:
  - VITE_API_BASE_URL=http://web:8000  # Changed from localhost
  - VITE_WS_BASE_URL=ws://web:8000/ws  # Changed from localhost
depends_on:
  - web  # Ensure backend starts first
```

### 2. frontend/tsconfig.json
```json
{
  "extends": "./.svelte-kit/tsconfig.json"  // Changed from ./tsconfig.base.json
  // Removed compilerOptions.paths - already defined in svelte.config.js
}
```

Note: Path aliases are configured in `svelte.config.js`:
```javascript
kit: {
  alias: {
    $lib: 'src/lib'
  }
}
```

### 3. frontend/src/hooks.server.ts
```typescript
import { env } from '$env/dynamic/private';  // Added

const API_BASE_URL = env.VITE_API_BASE_URL || 'http://localhost:8000';
```

### 4. frontend/src/routes/login/+page.server.ts
```typescript
import { env } from '$env/dynamic/private';  // Added

const API_BASE_URL = env.VITE_API_BASE_URL || 'http://localhost:8000';

// ... inside actions.default ...

// Set cookies inside try-catch
loginResponse.headers.forEach((value, key) => {
  if (key.toLowerCase() === 'set-cookie') {
    cookies.set(cookieName, cookieValue, options);
  }
});

} catch (error) {
  return fail(500, { error: 'Network error' });
}

// Redirect OUTSIDE try-catch (important!)
throw redirect(303, '/checkin');
```

### 5. frontend/src/routes/logout/+page.server.ts
```typescript
import { env } from '$env/dynamic/private';  // Added

const API_BASE_URL = env.VITE_API_BASE_URL || 'http://localhost:8000';
```

### 6. backend/.env.example
```env
ALLOWED_HOSTS=*  # Changed from localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

## How Docker Networking Works

### Container-to-Container Communication
- Containers communicate using **service names** from docker-compose.yml
- Frontend → Backend: Use `http://web:8000` (not `localhost:8000`)
- Backend → Database: Use `postgresql://postgres@db:5432` (not `localhost:5432`)

### Host-to-Container Communication
- From your local machine → Use `http://localhost:PORT`
- Browser → Frontend: `http://localhost:5173`
- Browser → Backend: `http://localhost:8000`

### Container Network Flow
```
Browser (localhost:5173)
    ↓ (frontend service exposed on port 5173)
Frontend Container
    ↓ (internal network: http://web:8000)
Backend Container (web service)
    ↓ (internal network: postgresql://db:5432)
Database Container (db service)
```

## Environment Variables in SvelteKit

### Client-Side (Browser)
- Use `import.meta.env.VITE_*`
- Available in browser code
- Must be prefixed with `VITE_`

### Server-Side (Node.js)
- Use `import { env } from '$env/dynamic/private'`
- Available in server routes, hooks, and actions
- Can access any environment variable
- Reads from Docker `environment:` section at runtime

### Example
```typescript
// Client-side (.svelte files)
const API_URL = import.meta.env.VITE_API_BASE_URL;

// Server-side (+page.server.ts, hooks.server.ts)
import { env } from '$env/dynamic/private';
const API_URL = env.VITE_API_BASE_URL;
```

## Testing

### Rebuild and Restart Containers
```bash
docker compose down
docker compose up --build
```

### Check Logs
```bash
# Frontend logs
docker compose logs -f frontend

# Backend logs
docker compose logs -f web
```

### Verify Connection
1. Frontend should start without errors
2. No "Auth check error: TypeError: fetch failed"
3. No "ECONNREFUSED" errors
4. Navigate to http://localhost:5173
5. Should redirect to login page
6. Login should work and persist session

## Common Docker Issues

### Issue: "Connection Refused"
**Cause**: Using `localhost` instead of service name
**Fix**: Use service name (e.g., `web`, `db`, `valkey`)

### Issue: "Service not found"
**Cause**: Service not started or wrong service name
**Fix**: Check `docker compose ps` and verify service names

### Issue: "CORS error"
**Cause**: Backend doesn't allow frontend's origin
**Fix**: Add to `CORS_ALLOWED_ORIGINS` in backend/.env.example

### Issue: Environment variable not working
**Cause**: Not rebuilding after changing docker-compose.yml
**Fix**: Run `docker compose up --build`

## Production Notes

For production deployment:
- Use specific service hostnames
- Set proper CORS origins
- Enable HTTPS (SESSION_COOKIE_SECURE=true)
- Use secrets for sensitive values
- Set proper ALLOWED_HOSTS
- Consider using nginx as reverse proxy

## Next Steps

1. Restart containers: `docker compose down && docker compose up --build`
2. Test login flow at http://localhost:5173
3. Verify session persists across page navigations
4. Check that no connection errors appear in logs
