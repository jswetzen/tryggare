# Current Tasks

_Previous completed work archived to `docs/CURRENT_TASKS_archive_2026-03-16.md`_

---

## Login Page Localization - IN PROGRESS

**Started:** 2026-03-16

Audit and fix i18n on the login page; ensure Swedish is the default for unauthenticated users.
See `DEFERRED_TASKS/login_page_localization.md` for full notes.

### Tasks
- [ ] Audit `frontend/src/routes/login/+page.svelte` for hardcoded English strings
- [ ] Add missing translation keys to `messages/sv.json`, `en.json`, `nb.json`
- [ ] Verify Swedish is the default language for unauthenticated users
- [ ] Verify language picker accessible on login page (or Swedish default is sufficient)
- [ ] Run `make test-i18n` and `make test-auth` to confirm nothing broken
