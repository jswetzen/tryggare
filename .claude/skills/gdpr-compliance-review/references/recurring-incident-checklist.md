# Recurring Incident — Real Facts Leaking Into Generic Templates

This specific class of bug has happened **twice** in this project. Run this
checklist at the start of every review, before anything else, on every file
in File Map Section A (the files that are supposed to stay 100% generic).

## What happened, concretely

1. **Incident 1**: `docs/legal/TECHNICAL_ANNEX.md` (the public, generic
   template) had real, identifying business specifics hardcoded into it
   instead of staying generic — a real city, a real person's name, a real
   company name. It sat exposed on the public repo for roughly three days
   before being caught and purged via a git history rewrite.
2. **Incident 2**: A real, filled legal-review document (containing real
   infrastructure and company facts) was created as a working file but not
   added to `.gitignore` — it sat untracked in the working tree, one
   `git add -A`/`git add .` away from being committed to the public repo.

The common pattern: a generic template or scratch document **silently
accumulates real facts over multiple edits**, because each individual edit
looks reasonable in isolation (filling in a placeholder feels like normal
progress) and nobody re-reads the whole file for genericity before it's
committed or left in a public working tree.

## The sweep — run this every time

1. **List every file in File Map Section A** (the templates) plus anything
   newly added under `docs/legal/` this session.
2. **For each `{{PLACEHOLDER}}` in each file**: confirm it is still a
   placeholder, or if filled in, that the value is generic (not a specific
   real name, city, address, org number, phone number, price, or hostname).
3. **Grep for known real-fact fragments** that have leaked before, so a
   regression is caught immediately rather than requiring a fresh read:
   company/personal names, a specific city, specific street address, a
   specific phone number pattern, specific internal hostnames used for the
   operator's own infrastructure (these change over time — ask the user what
   the current real facts are if you need to check for their specific
   presence, since they're deliberately not written into this shared skill
   file).
4. **Check `git status` for untracked files under `docs/legal*`** — anything
   real-content but not yet gitignored is a live leak risk, not a
   hypothetical one. Cross-check the untracked file list against whatever
   real-draft `.gitignore` entries currently exist to confirm coverage, and
   flag anything real-content that doesn't match an ignore pattern.
5. **Check recent commit history on `docs/legal/` files** for any commit that
   looks like a "genericize" or "purge" fix — if one exists, read the diff to
   understand exactly what leaked, since it's a strong signal of what
   pattern to watch for going forward (e.g. if a specific field like "storage
   backend" or "backup location" leaked once, check that field specifically
   on every subsequent review).
6. **Never write real facts directly into this skill file or its siblings**
   under `.claude/skills/`. This skill file is itself checked into the
   project and is exactly the kind of "generic document that could
   accumulate real facts" the pattern warns about — keep it fact-free and
   ask the user for current real values when a check genuinely requires them.

## Severity

Treat any confirmed leak found by this sweep as the **highest-severity
finding** in the review, above any DPA/DPIA/code correctness issue — a public
data leak of real business/personal identifiers is a bigger and more urgent
problem than any documentation gap, and (depending on what leaked) may itself
be a reportable incident under the org's own `BREACH_NOTIFICATION_PROCESS.md`.
