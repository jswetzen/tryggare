The Conference Child Management System has a detailed specification in the file PROJECT_SPECIFICATION.md. TECHNICAL_DESIGN.md specifies the technical details and a high-level implementation plan is in IMPLEMENTATION_PLAN.md.

Update IMPLEMENTATION_PLAN.md to check off items that are done. Also keep CURRENT_TASKS.md up-to-date as you complete items.

## Development Environment

The docker compose file is running on the host, you're connected to a podman container, but with host networking so you can access the running servers. The server is set up to watch for changes to `restart.txt` - execute `./restart.sh` to trigger a rebuild and restart. It can take 30 seconds or more, but this way you can test out changes directly. The live container logs from podman are available in `web.log` and `frontend.log`.

**Restart Mechanism**:
- **Recommended**: Use `./verification.sh` for automated restart and verification
  - Touches `restart.txt` to trigger restart
  - Waits for restart completion (monitors web.log)
  - Verifies server health
  - Optionally runs Selenium tests with `--test` flag
- **Legacy**: `./restart.sh` touches `restart.txt` (manual verification needed)
- Podman containers detect the file change and restart
- **Production containers** (`docker-compose.prod.yml`) do NOT use this mechanism - they require manual rebuild

- **Backend**: backend directory with Django, 'web' container
- **Frontend**: frontend directory with SvelteKit

IMPORTANT: *Never* kill a process you have started.
You risk stopping critical services or Claude Code by accident.
Instead, if there's a risk a process won't finish you should execute it with a timeout.

## Quick Development Testing Workflow

After adding new functionality, follow these steps to keep everything working:

1. **Backend Changes**
   ```bash
   cd /workspace/check-ins/backend
   # If models changed
   uv run python manage.py makemigrations
   uv run python manage.py migrate
   # Run quick verification
   uv run python verify.py
   # Restart and verify (recommended)
   cd /workspace/check-ins
   ./verification.sh
   # Or restart and run tests
   ./verification.sh --test
   ```

2. **Frontend Changes**
   ```bash
   # Restart and verify server (recommended)
   ./verification.sh
   # Or restart and run tests
   ./verification.sh --test
   # Manually test the changed UI flows
   # Verify i18n works (check both English and Swedish if applicable)
   ```

3. **Selenium E2E Tests** (After login/auth/UI changes)
   ```bash
   # Run tests without restarting
   ./verification.sh --no-restart --test
   # Or run specific test file
   cd /workspace/check-ins/backend
   uv run python test_selenium_full_flows.py
   # Also run test_auth.py if auth-related
   uv run python test_auth.py
   ```

4. **Fix Any Errors**
   - Backend: Check `/workspace/check-ins/web.log`
   - Frontend: Check `/workspace/check-ins/frontend.log`
   - Selenium: Check test output and screenshots in `/tmp/`

**For comprehensive testing workflows, see [VERIFICATION_GUIDE.md](./VERIFICATION_GUIDE.md)**

## Task Completion Checklist

Before considering an implementation phase complete, make sure to:
- Write tests that cover your new functionality
- IMPORTANT: Run `uv run python backend/verify.py` for backend changes
- Run the full test suite: `uv run python manage.py test` (for production testing)
- Update CURRENT_TASKS.md so everything that you actually finished is checked off
- Commit all your changes to git with clear commit messages

