The Conference Child Management System has a detailed specification in the file PROJECT_SPECIFICATION.md. TECHNICAL_DESIGN.md specifies the technical details and a high-level implementation plan is in IMPLEMENTATION_PLAN.md.

Update IMPLEMENTATION_PLAN.md to check off items that are done. Also keep CURRENT_TASKS.md up-to-date as you complete items.

If you really have to write on-the fly documentation or markdown summaries, store them under docs/
Any tools and scripts you create for ad-hoc testing shall be stored under agent-tools/

## Deployment Environments

**Two deployment modes exist. Both should be running:**

### Production Deployment (docker-compose.prod.yml)
- **Single container**: Django serves both API and built frontend static files
- **Access**: `http://localhost:8080` (both frontend and backend)
- **Database**: PostgreSQL on port 5433
- **Settings**: `config.settings.prod`
- **Auto-rebuild**: This command is running on the host in this repository with nushell: `watch restart.txt { || podman compose -f docker-compose.prod.yml --env-file .env.prod up -d --force-recreate --build | save -f build.prod.log }`
- **Manual rebuild**: No podman access, the only way is to write to `restart.txt`.
- **Testing**: `./verification.sh --test` (checks build logs, disk space, then runs tests)

### Development Environment (docker-compose.yml)
- **Separate containers**: Frontend (SvelteKit dev server) and Backend (Django)
- **Access**: Frontend `http://localhost:5173`, Backend `http://localhost:8000`
- **Database**: PostgreSQL on port 5432
- **Settings**: `config.settings.local`
- **Auto-rebuild**: This command is running on the host in this repository with nushell: `watch restart.txt { || podman compose up -d --force-recreate --build | save -f build.dev.log }`
- **Restart**: Hot reloading should cover most code changes, but if you have to restart, trigger the auto-rebuild by writing to `checks-ins/restart.txt`.
- **Note**: `backend/config/settings/local.py` overrides `STATIC_URL = "/static/"` to avoid conflicts with `MEDIA_URL` in dev mode

**Backend & Frontend:**
- **Backend**: `backend/` directory with Django
- **Frontend**: `frontend/` directory with SvelteKit
- **Logs**:
  - Backend runtime: `web.log`
  - Frontend dev server: `frontend.log`
  - Development builds: `build.dev.log` (captured from podman compose)
  - Production builds: `build.prod.log` (captured from podman compose)

## Full test running

```bash
# Production deployment test
./verification.sh --no-restart --test    # Tests only, no restart
./verification.sh --test                 # Restart + tests
```

**Backend model changes:**
```bash
cd /workspace/check-ins/backend
uv run python manage.py makemigrations
uv run python manage.py migrate
uv run python verify.py  # Quick verification
```

**Debugging failures:**
- Backend runtime: Check `/workspace/check-ins/web.log`
- Frontend dev: Check `/workspace/check-ins/frontend.log`
- Production builds: Check `/workspace/check-ins/build.prod.log`
- Selenium tests: Check screenshots in `/tmp/`
- Build errors: The verification script now automatically checks build.prod.log for:
  - "no space left on device" → Run `podman system prune -a`
  - "Build command failed" → Check full log with `less build.log`
  - Frontend build failures → Look for npm/vite errors in build.log

**For detailed testing workflows, see [VERIFICATION_GUIDE.md](./VERIFICATION_GUIDE.md)**

## Task Completion Checklist

Before considering an implementation phase complete, make sure to:
- Write tests that cover your new functionality
- IMPORTANT: Run `uv run python backend/verify.py` for backend changes
- Run the full test suite: `uv run python manage.py test` (for production testing)
- Update CURRENT_TASKS.md so everything that you actually finished is checked off
- Commit all your changes to git with clear commit messages

## Playwright for Manual Testing

Playwright browser automation is available for testing and validation:
- **Use case**: Manually test frontend flows, login, navigation, form submissions
- **Access**: Use `mcp__playwright__browser_*` tools to interact with the browser
- **Example**: Navigate to `http://localhost:5173`, fill forms, click buttons, take screenshots
- **Credentials**: `admin:admin123` for testing login flows
- **Note**: Useful when testing from remote/mobile devices isn't practical due to CORS/CSRF restrictions

