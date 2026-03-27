# Open Source Launch Prep

Goal: Make this project ready to go public and get traction in the church/org community.

## Priority Order

### 1. Repo Cleanup (quick wins)
- [ ] `.gitignore` the remaining untracked noise: `oom`, `import_examples.json`, `printer-client/` scratch files
- [ ] Add `printer-client/` scratch files to `.gitignore` or commit the useful ones
- [ ] Verify `.claude/` is gitignored (no personal permission configs in public repo)
- [ ] Move `import_examples.json` to `prototypes/` or `.gitignore` it

### 2. Security Hardening
- [ ] Change `SECRET_KEY` default from `"insecure-change-me"` to raise an error in prod settings (already correct in prod, but worth making explicit)
- [ ] Add `SECURITY.md` — how to report vulnerabilities privately
- [ ] Audit all `.env*.example` files to ensure no real values snuck in

### 3. OSS Governance Docs
- [ ] `CONTRIBUTING.md` — fork, branch, PR, code style (Django PEP8, Svelte conventions), test requirements
- [ ] `CODE_OF_CONDUCT.md` — use Contributor Covenant boilerplate
- [ ] `CHANGELOG.md` — retroactive summary of major milestones (MVP, printer, i18n, Planning Center import)
- [ ] Update `README.md` — add license badge, feature list with screenshots, "Deploy to..." button

### 4. CI/CD
- [ ] GitHub Actions workflow: run Django unit tests on every PR
- [ ] Optionally: lint (ruff for Python, eslint for Svelte)
- [ ] Add issue templates (bug report, feature request)
- [ ] Add PR template with checklist

### 5. Deployment Story
- [ ] One-click deploy option (Railway, Render, or Coolify) — biggest friction reducer for churches
- [ ] Document backup/restore of PostgreSQL database
- [ ] Document how to update (git pull + restart.txt pattern)

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
