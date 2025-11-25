The Conference Child Management System has a detailed specification in the file PROJECT_SPECIFICATION.md. TECHNICAL_DESIGN.md specifies the technical details and a high-level implementation plan is in IMPLEMENTATION_PLAN.md.

Update IMPLEMENTATION_PLAN.md to check off items that are done. Also keep CURRENT_TASKS.md up-to-date as you complete items.

## Development Environment

The docker compose file is running on the host, you're connected to a podman container, but with host networking so you can access the running servers. The server is also set up so you can execute /workspace/restart.sh to rebuild and restart it! It can take 30 seconds or more, but this way you can test out any changes directly. Furthermore, web.log and frontend.log has the live container logs from podman.

- **Backend**: backend directory with Djanga, 'web' container.
- **Frontend**: frontend directorp with svelte.

IMPORTANT: *Never* kill a process without asking permission first.
You risk stopping critical services or Claude Code by accident.

## Django Backend Verification Workflow

After making backend changes, use the quick verification pattern:

```bash
cd /workspace/check-ins/backend

# If models changed
uv run python manage.py makemigrations
uv run python manage.py migrate

# Run verification script (combines model + API tests, ~500ms)
uv run python verify.py
```

See VERIFICATION.md for detailed testing patterns and best practices.

## Testing Methods (Priority Order)

1. **Django Test Client** (RECOMMENDED) - Fast, no server needed
   - Use `Client()` for API testing
   - Use `force_login()` for authentication
   - ~200ms per test

2. **Direct Model Testing** - Fastest for business logic
   - Import models directly after django.setup()
   - ~50ms per test

## Task Completion Checklist

Before considering an implementation phase complete, make sure to:
- Write tests that cover your new functionality
- IMPORTANT: Run `uv run python backend/verify.py` for backend changes
- Run the full test suite: `uv run python manage.py test` (for production testing)
- Update CURRENT_TASKS.md so everything that you actually finished is checked off
- Commit all your changes to git with clear commit messages

