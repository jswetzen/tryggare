The Conference Child Management System has a detailed specification in the file PROJECT_SPECIFICATION.md. TECHNICAL_DESIGN.md specifies the technical details and a high-level implementation plan is in IMPLEMENTATION_PLAN.md.

Update IMPLEMENTATION_PLAN.md to check off items that are done. Also keep CURRENT_TASKS.md up-to-date as you complete items.

## Deployment Environments

**Two deployment modes exist. Determine which is running:**

### Production Deployment (docker-compose.prod.yml) - **LIKELY CURRENT**
- **Single container**: Django serves both API and built frontend static files
- **Access**: `http://localhost:8080` (both frontend and backend)
- **Database**: PostgreSQL on port 5433
- **Settings**: `config.settings.prod`
- **Restart**: Requires manual rebuild: `podman compose -f docker-compose.prod.yml --env-file .env.prod up -d --build`
- **Testing**: `./verification.sh --no-restart --test` (auto-detects production mode)

### Development Environment (docker-compose.yml)
- **Separate containers**: Frontend (SvelteKit dev server) and Backend (Django)
- **Access**: Frontend `http://localhost:5173`, Backend `http://localhost:8000`
- **Database**: PostgreSQL on port 5432
- **Settings**: `config.settings.local`
- **Restart**: `./verification.sh` (touches `restart.txt`, waits for reload)
- **Testing**: `./verification.sh --test`

**How to tell which you're running:**
```bash
# Check if production is accessible
curl -s http://localhost:8080 >/dev/null && echo "✓ Production (8080)" || echo "✗ Not running"

# Check if development is accessible
curl -s http://localhost:5173 >/dev/null && echo "✓ Development (5173)" || echo "✗ Not running"
```

**Backend & Frontend:**
- **Backend**: `backend/` directory with Django
- **Frontend**: `frontend/` directory with SvelteKit
- **Logs**: Available in `web.log` and `frontend.log`

IMPORTANT: *Never* kill a process you have started.
You risk stopping critical services or Claude Code by accident.
Instead, if there's a risk a process won't finish you should execute it with a timeout.

## Quick Testing Workflow

**After making changes:**

```bash
# Production deployment (most common)
./verification.sh --no-restart --test    # Tests only, no restart
# If you need to rebuild: podman compose -f docker-compose.prod.yml --env-file .env.prod up -d --build

# Development deployment (if using docker-compose.yml)
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
- Backend: Check `/workspace/check-ins/web.log`
- Frontend: Check `/workspace/check-ins/frontend.log`
- Selenium: Check screenshots in `/tmp/`

**For detailed testing workflows, see [VERIFICATION_GUIDE.md](./VERIFICATION_GUIDE.md)**

## Task Completion Checklist

Before considering an implementation phase complete, make sure to:
- Write tests that cover your new functionality
- IMPORTANT: Run `uv run python backend/verify.py` for backend changes
- Run the full test suite: `uv run python manage.py test` (for production testing)
- Update CURRENT_TASKS.md so everything that you actually finished is checked off
- Commit all your changes to git with clear commit messages

