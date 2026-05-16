# Open Source Launch Prep

Goal: Make this project ready to go public and get traction in the church/org community.

## Priority Order

### 1. Repo Cleanup (quick wins)
- [x] `.gitignore` the remaining untracked noise: `oom`, `import_examples.json`, `printer-client/` scratch files
- [x] Add `printer-client/` scratch files to `.gitignore` or commit the useful ones
- [x] Verify `.claude/` is gitignored (no personal permission configs in public repo)
- [x] Move `import_examples.json` to `prototypes/` or `.gitignore` it

### 2. Security Hardening
- [x] Change `SECRET_KEY` default from `"insecure-change-me"` to raise an error in prod settings
- [x] Add `SECURITY.md` — how to report vulnerabilities privately
- [x] Audit all `.env*.example` files to ensure no real values snuck in
- [ ] Update placeholder emails in `SECURITY.md` and `CODE_OF_CONDUCT.md` before publishing

### 3. OSS Governance Docs
- [x] `CONTRIBUTING.md` — fork, branch, PR, code style (Django PEP8, Svelte conventions), test requirements
- [x] `CODE_OF_CONDUCT.md` — use Contributor Covenant boilerplate
- [x] `CHANGELOG.md` — retroactive summary of major milestones (MVP, printer, i18n, Planning Center import)
- [x] Update `README.md` — add license badge, feature list, Contributing/License sections
- [ ] Add screenshot to README (shows the UI in action — highest-impact visual)

### 4. CI/CD
- [x] GitHub Actions workflow: run Django unit tests on every PR (`.github/workflows/test.yml`)
- [x] Lint: ruff for Python (included in test workflow)
- [x] Add issue templates (bug report, feature request)
- [x] Add PR template with checklist

### 5. Deployment Story
- [x] Coolify deployment guide (`docs/deploy-coolify.md`)
- [x] Document backup/restore of PostgreSQL database (in Coolify guide)
- [x] Document how to update (in Coolify guide)

### 6. Visibility / Marketing
- [ ] Record a 3-minute demo video showing: login → check in a child → label prints → check out
- [ ] Write a blog post: "Why we built our own child check-in instead of paying $X/month"
- [ ] Post in: r/churchtech, Planning Center community forums, church IT Facebook groups
- [ ] Add comparison to README: vs KidCheck, ProPresenter Check-In, Planning Center Check-Ins
- [ ] Consider a project landing page (GitHub Pages or simple static site)

## Notes

- Secrets situation is **clean**: `.env.prod` was never committed, no hardcoded secrets in tracked files
- `.claude/settings.local.json` has no secrets — just tool permissions — but should be gitignored before going public
- AGPL-3.0 is a good choice for church orgs that don't want SaaS forks
- Viral path for this niche is word-of-mouth in church communities, not Hacker News
