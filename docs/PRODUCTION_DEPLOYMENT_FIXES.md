# Production Deployment Fixes - 2025-12-14

## Issues Found and Fixed

### 1. ✅ Dockerfile.prod - Permission Issues with .venv
**Problem**: The Django user couldn't access the Python virtual environment because dependencies were installed as root before switching to the non-root user.

**Fix**: Modified `/workspace/check-ins/backend/Dockerfile.prod`:
- Create the `django` user BEFORE installing dependencies
- Give ownership of `/app` to the `django` user
- Install dependencies AS the `django` user
- Use `--chown=django:django` on all COPY commands

### 2. ✅ DATABASE_URL Password Encoding
**Problem**: Passwords containing special characters (`/`, `+`, `=`) in URLs must be URL-encoded.

**Original password**: `JfrlLDq6Y7ESJ8Xi4L0SyKEcCeHiID3uc0/5AepuXzE=`
**URL-encoded**: `JfrlLDq6Y7ESJ8Xi4L0SyKEcCeHiID3uc0%2F5AepuXzE%3D`
- `/` → `%2F`
- `=` → `%3D`

**Fix**: Updated `docker-compose.prod.yml` to use URL-encoded passwords in DATABASE_URL and VALKEY_URL.

### 3. ⚠️ Database Volume Password Mismatch (NEEDS MANUAL FIX)

**Problem**: The PostgreSQL database volume (`pg_data_prod`) was created with an unknown password. The current configuration can't connect because the password doesn't match.

**Current Status**:
- Database is running and healthy
- Web container crashes on startup with: `FATAL: password authentication failed for user "postgres"`
- The existing volume has an old postgres password that doesn't match the new configuration

**Solutions** (choose one):

#### Option A: Reset the Database Volume (Recommended for test environment)
```bash
# Stop all production containers
podman compose -f docker-compose.prod.yml down

# Remove the database volume
podman volume rm check-in-prod_pg_data_prod

# Start fresh (will create new database with correct password)
podman compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

#### Option B: Use Strong Passwords (After volume reset)
Edit `.env.prod` to set strong passwords and update `docker-compose.prod.yml` to use them:

```yaml
# In docker-compose.prod.yml, replace hardcoded values with:
- DATABASE_URL=${DATABASE_URL}
- VALKEY_URL=${VALKEY_URL}

# In db-prod environment:
POSTGRES_PASSWORD: ${DB_PASSWORD}
```

Then ensure `.env.prod` has URL-encoded passwords as shown in section 2 above.

#### Option C: Keep Simple Passwords for Testing
If you just want to get it running for testing, the current `docker-compose.prod.yml` uses:
- Database password: `password`
- This will work AFTER resetting the volume (Option A)

## Files Modified

1. `/workspace/check-ins/backend/Dockerfile.prod` - Fixed permissions and user handling
2. `/workspace/check-ins/docker-compose.prod.yml` - Added hardcoded DATABASE_URL and VALKEY_URL with proper encoding
3. `/workspace/check-ins/.env.prod` - Updated with URL-encoded passwords (for reference)

## Current State

- ✅ Docker build completes successfully
- ✅ Containers start and restart properly
- ✅ Frontend build is working
- ✅ Dependencies install correctly as non-root user
- ❌ Database connection fails due to password mismatch with existing volume

## Next Steps

1. **Reset the database volume** using Option A above
2. **Wait for containers to start** (check with `podman compose -f docker-compose.prod.yml ps`)
3. **Check logs**:
   - Build: `tail -f build.prod.log`
   - Web: `tail -f web.prod.log`
   - DB: `tail -f db.prod.log`
4. **Test the deployment**: Visit `http://localhost:8080`

## Testing Checklist

After resetting the volume:
- [ ] Containers start without errors
- [ ] Database accepts connections
- [ ] Django migrations run successfully
- [ ] Static files are collected
- [ ] Web interface is accessible at http://localhost:8080
- [ ] Can log in with admin credentials
- [ ] Run E2E tests: `make test-e2e-prod`

## Security Note

The current `docker-compose.prod.yml` has **hardcoded credentials** for testing purposes. Before deploying to a real production environment:

1. Remove hardcoded values from `docker-compose.prod.yml`
2. Use environment variables from `.env.prod`
3. Generate strong, unique passwords
4. Ensure `.env.prod` is in `.gitignore` (it already is)
5. Consider using Docker secrets or a proper secrets management solution
