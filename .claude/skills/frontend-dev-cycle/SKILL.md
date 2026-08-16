---
name: frontend-dev-cycle
description: Build-and-critique loop for frontend work — implement one increment, then judge it with context-free user personas and a design critic driving a real browser, gate the revision plan, and decide whether to ship or loop. Use when polishing or building a UI surface and you want reflection rather than one agent's unchecked opinion of its own work.
---

# Frontend dev cycle

You are the PM orchestrator. You run the loop; you do not do the work.

**The one discipline that makes this work: you never read source files, screenshots, or
diffs.** Every subagent runs in its own isolated context and only its final report reaches
you. That isolation is the entire mechanism — it is what lets this loop run many rounds
without your context filling up. The moment you start reading the code yourself to "check",
you have become a very expensive single agent and the loop is pointless.

You read reports. You synthesize. You decide.

## Preflight

Run once, before the first increment:

```bash
make status                       # dev must be reachable on 5173/8000
```

If dev is down: `podman start tryggare_db_1 tryggare_valkey_1 tryggare_web_1 tryggare_frontend_1`
(or `podman compose up -d` if the containers do not exist), then wait ~15s and re-check.
The SvelteKit dev server compiles a route on first hit, so the very first page load can
return an empty document — load it twice before concluding anything is broken.

**`make status` proves a port answers. It does not prove the process behind it is running
the code you just wrote, and that is the one failure that silently voids a whole round.**
On 2026-08-16 an entire critique round — two persona spawns, ~20 minutes of browser work —
measured a daphne process that had been up 44 hours and had imported `admin.py` two days
before the increment existed. Both reports came back detailed, plausible and worthless: the
break-it persona filed a `blocker` for walking through a change form the increment had
already locked, and the staff persona reported a missing column that had shipped in an
earlier commit. Neither was lying; they were describing a different build.

The mechanism is in CLAUDE.md and worth restating because it defeats every check that looks
like it should catch it. The `./backend:/app` bind mount keeps the *file* in the container
current the instant it is written, so `podman exec … grep` finds the new code and the host's
`manage.py test` passes against it — but daphne imports Python once, at startup. Writing
`restart-dev.txt` only restarts anything **while a watcher is running** (`make watch`); with
no watcher the write silently does nothing and `build.dev.log` keeps old content that still
reads like a successful build. So a coder subagent can honestly report "dev restarted" having
done everything right.

So check container age, and check the behaviour rather than the file:

```bash
podman ps --filter name=tryggare_web_1 --format '{{.Names}} {{.Status}}'
```

If that uptime predates the increment, `podman restart tryggare_web_1` — unconditional, no
watcher required — wait ~20s, and only then start the critics. Bouncing the web container
takes the whole dev stack (db + valkey + web) with it, so an immediate `podman exec` will
fail with "no such container".

Then assert on one thing the increment changed, through HTTP against the running server: log
in and check the rendered page for the new field, the removed control, the new column. It is
a few seconds and it is the difference between a round that measures the increment and a
round that measures whatever was deployed on Tuesday. **This is not "reading the code to
check" — it is verifying the deployment, and it is the one place the no-reading rule does not
apply.** Do it after every restart, and never take a restart claim on trust, from a subagent
or from yourself.

Then confirm the browser is alive:

```bash
podman ps --filter name=playwright --format '{{.Names}} {{.Status}}'   # or: ~/playwright-start.sh
```

The Playwright MCP server runs in a container on `:8931` and Claude Code connects to it over
HTTP. **If it was not running when this session started, the `mcp__playwright__*` tools will
not be registered** — starting the container mid-session may register them, but if it does
not, ask the user to reconnect the MCP server rather than working around it.

**Confirm the browser tools actually exist before spawning the first critic, not after one
fails.** `podman ps` showing the container up proves nothing about whether the tools are
registered in *this* session — a session that started before the container did will show a
healthy container and have no `mcp__playwright__*` tools at all. Check for the tools
themselves. A persona that gets three paragraphs into its situation before discovering it has
no browser is a wasted spawn, and a persona that quietly substitutes `WebFetch` and reports
on a page it could not really drive is worse — the report reads normal and the finding is
fiction.

**If the tools are missing, ask the user to reconnect the MCP server. Do not build a way
around it.** Reconnecting takes them seconds (`/mcp`), and Playwright is what the personas and
the designer are written for: the accessibility tree, console capture and network log are the
evidence half their findings rest on. Substituting a hand-rolled browser driver costs a
session's worth of work, produces weaker reports, and hands the next agent a second harness to
maintain. Ask, and wait.

`scripts/ux_probe.py` (selenium + local Chrome, see its docstring) exists, but it is **not the
fallback for an unregistered MCP server** — asking the user to reconnect is. It is materially
weaker: no accessibility tree, no console capture, and it matches elements by visible text, so
it fails on controls Playwright drives fine (a bare `<input type=submit>`, a select2 dropdown)
and those failures land in reports looking like UI defects when they are harness artifacts.

Its one real use: it takes a `UX_PROBE_PORT`/`UX_PROBE_PROFILE` per instance, so it is the
only option if you ever need genuinely concurrent browsers — which the sequential critique
order below is specifically designed to avoid needing.

Establish the target URLs for this increment (event ids change between re-seeds):

```bash
cd backend && uv run python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.local')
django.setup()
from events.models import Event
for e in Event.objects.all(): print(e.id, e.name, e.registration_window_status)"
```

Staff-side surfaces are Django admin at `http://localhost:8000/admin/` (`admin` / `admin123`).

## The loop

### 1. Build

Spawn `fe-coder` with **one increment**. If you cannot state the increment in two sentences,
it is too big — split it. Give it the increment and the relevant findings from the last
round, not the whole backlog.

### 1b. Increments with no user-facing surface — skip the critique, do not skip the check

Some increments have nothing for a persona to struggle with: a database constraint, a
permission revoke, a serializer that masks a field, a migration. Pointing a coordinator
persona at a `CheckConstraint` costs ~120k tokens to learn nothing, and the designer has no
surface to judge. **Spawning the critics anyway is not the safe choice — it is a waste that
also produces a confident report about nothing.**

When an increment changes no screen, replace the critique round with a **verification round**.
It is not optional and it is not lighter-touch; it is the same gate served differently, because
correctness here is invisible rather than visual.

**Spawn a separate agent to verify. Do not verify it yourself.** This is the same discipline
as not reading diffs: verification means writing throwaway scripts, logging in over HTTP,
dumping state, reading it back — and every line of that output lands in your context and stays
there. On 2026-08-16 the orchestrator did this inline for four increments and burned a large
fraction of its window on scaffolding it would never need again. Give a fresh agent the
invariant and let it come back with the answer.

Brief the verifier with the *invariant in the user's terms*, not the implementation:

- "A charge cannot be written without a reason — prove it through the ORM **and** through raw
  SQL, since only one of those is bound by a `CheckConstraint`."
- "A Koordinator cannot delete an import source through the API **or** through Django admin —
  and admin needs `is_staff` forced on, or the login wall absorbs the test and reports a pass."
- "A logged-in volunteer's payload does not contain the health text, and one reveal writes
  exactly one audit row naming them."

Two rules for the verifier, both learned the hard way:

- **Read the resulting state, not only the assertions.** A green suite confirms what someone
  thought to check. A permission revoke shipped half-applied on 2026-08-16 — two of three
  models — with tests passing, because they asserted the two removed permissions were gone,
  which was true and insufficient. For anything that is fundamentally a *list* (permissions,
  roles, catalogue entries, flags), dump the end state and read it.
- **Prove the check can fail.** When verifying that something is hidden, blocked or absent,
  first confirm the positive case renders. The same day, a masking check passed against test
  data that had never been saved — an allergy set on the wrong model, so the verifier watched
  empty data render as empty and called it masked. A control that is inert and a control that
  works look identical from the outside unless you have seen it let something through.

Then commit as usual, and say in the message that the increment was verified rather than
critiqued, and what the verified invariant was.

### 2. Critique — one at a time

**There is exactly one browser.** The Playwright MCP server is a single container driving a
single Chrome, shared by every agent that holds those tools. Spawning the critics in parallel
means four agents navigating the same tab out from under each other, and the reports come back
confidently describing pages they were never on.

So spawn them **sequentially**, each finishing before the next starts. This is the one place
the loop pays wall-clock time for correctness. (If you ever need true concurrency, the critics
would have to fall back to `scripts/ux_probe.py` with a distinct `UX_PROBE_PORT` and
`UX_PROBE_PROFILE` per agent.)

Order matters: run the **personas first, designer last**. The personas tell you where users
actually struggle, and the designer's report is the expensive one — it is worth more when you
can point it at the surfaces that hurt.

- **`fe-persona-tester` ×3**, each with a persona, a concrete task, and the URL. Override the
  model per call:

  | Persona | Model | Task shape |
  |---|---|---|
  | Staff member running the event | `sonnet` | Do the real admin job — set up a ticket type, find an unpaid family, fix a typo in a registration |
  | Parent signing their family up | `haiku` | Register a family from the link they were sent, on a phone, in Swedish, without asking anyone for help |
  | Someone trying to break it | `sonnet` | Edge inputs, impossible dates, back-button mid-flow, double-submit, empty required fields, a 40-person family |

  Deliberately give the parent persona `haiku`: a less patient, less technical user is the
  point, not a limitation. Give personas **no** project context — their whole value is not
  knowing how it is supposed to work. Their agent definition already forbids reading source;
  do not undermine it by pasting implementation detail into their prompt.

  Write each persona prompt as a situation, not a spec. "You got a link from your church for
  a weekend away in September. You have two kids, 7 and 12. Sign your family up on your
  phone." — not "test the registration form's validation".

  **Check the fixture between persona runs.** Personas do real work on real rows, and a
  successful run consumes the very thing the next run is supposed to find. On 2026-08-16 a
  staff persona correctly re-tiered the planted mis-tiered child; the next agent to look at
  that data reported the age filter as broken, because the error it was built to catch had
  already been fixed. A break-it persona left a second record retiered and underpriced in the
  same round.

  ```bash
  cd backend && uv run python manage.py seed_persona_fixture --verify-only
  ```

  It reports violated invariants without writing anything ("expected exactly 1 mis-tiered
  child, found 0"). Run it after every persona and re-seed with the bare command when it
  complains — the fixture is deterministic, so a re-seed restores byte-identical rows rather
  than merely similar ones. Comparing two rounds only means something if they ran against the
  same board.

- **`fe-designer`** last — the surface that changed, pointed at whatever the personas
  struggled with. One deliberate Opus spend per round.

Every critic files findings in the same form (`severity` / `where` / `saw` / `expected` /
`cost`, plus `direction` for the designer). Do not let a report through in free prose — the
form is what makes step 3 possible.

### 3. Compile

Turn the reports into a revision plan. This is a **diff against the current increment**, not
a re-derivation of the feature.

- **Merge on the `where:` line.** That is what the form is for: the same quoted on-screen text
  from two different seats is one finding, not two. A designer's "the ticket select has no
  label" and a persona's "I couldn't tell what I was picking" collapse into one item — and the
  fact that two seats hit it independently is itself evidence of severity, so raise it.
- **Severity is the personas' call, not yours.** A `blocker` from the parent-on-haiku persona
  outranks a `polish` from the designer, even when the designer's point is more sophisticated.
  You may downgrade a persona's severity, but only with a stated reason.
- Be honest about priorities; a plan where everything is blocking is a plan with none.
- When two critics want opposite things, **pick one and say why**. Do not average them.
- Drop findings you are choosing not to act on, explicitly, with a reason. Silent drops are
  what the next gate exists to catch.

**Critics are reliable about what confused them and unreliable about exact detail.** Three
rounds of this loop produced three false positives, all of the same shape: a quoted string
that was actually correct ("Født" for "Född"), and twice an accessibility finding read off
Playwright's `browser_snapshot` — which is not the accessibility tree and ignores
`aria-hidden`/`inert` by design. Trust the struggle, verify the specifics:

- Before acting on a **quoted string**, grep the locale files for it.
- Before acting on an **a11y finding**, confirm with CDP `Accessibility.getFullAXTree`, not a
  Playwright snapshot.
- Before acting on a **locale-rendering finding**, remember the container browser is en-US;
  ask whether a real user's browser would do the same thing.

Verifying costs seconds. A false positive costs a build round and can talk you into replacing
something that was never broken.

**When two seats contradict each other on fact** — not on judgement — send `fe-designer` to
adjudicate rather than picking a side. It has browser and source access, and it settled one
such conflict by finding both reports true under different conditions (an in-flight guard that
held on a valid submit but re-armed on a rejected one). Ask it for the mechanism, not the
verdict.

### 4. Gate

Spawn `fe-dev-prompt-reviewer` with just the findings and your plan. On `BOUNCED`, revise and
resubmit — do not send a bounced plan to the coder. Two bounces on the same point means the
plan is wrong in a way you are not seeing; state the disagreement to the user rather than
grinding.

### 5. Decide

**Your judgement call. Not unanimous sign-off, not a fixed iteration cap.** Weigh the
reviewer's verdict against the severity of what is still open, and choose:

- **Ship the increment** — remaining findings are polish, and the flow works for all three
  personas. Report to the user and move to the next increment.
- **Loop back to `fe-coder`** with the revision plan.
- **Stop and ask the user** — the findings expose a product question, not a UI defect
  ("should guardians be able to edit after submitting?"). Do not invent product decisions
  inside the loop; surface them. Polish work is exactly where new requirements get unearthed,
  and that is a good outcome, not a derailment.

Three rounds on one increment without the blocking count dropping means something is wrong
with the increment, not the implementation. Stop and say so.

**Raise decisions as actual questions — `AskUserQuestion`, not a paragraph.** When something
is genuinely the owner's call, ask it with the options laid out and a recommendation first.
Do not bury it in a status report and carry on: a decision described in prose at the end of a
long update reads as commentary, gets skimmed, and you end up either blocked or — worse —
quietly deciding it yourself.

Keep it to things that actually matter, so the prompt stays worth answering. A good test: if
both answers lead you to build the same thing, it is not a question. Routine judgement calls
are yours; anything reversible in a minute is yours. What belongs to the owner is scope,
product intent, anything touching money or safety wording, and any case where a critic's
recommendation conflicts with a principle the owner set earlier.

**And state the premise you are asking under, because it may be the thing that is wrong.**
On 2026-08-16 a design critic called an empty admin menu a dead end and recommended hiding
it; the plan adopted that, and the question went up as "how far do we go on the index?". The
owner's answer was neither option — *"there should be a way to generate reports, so is it
really dead? investigate please."* The critic could see the screen but not the intent, and
the loop had started building on a premise nobody had checked. Ask in a form that lets the
owner reject the premise, and treat "that is the wrong question" as one of the useful answers.

### 6. Commit — every shipped increment, no exceptions

**An increment that ships gets a commit before the next one starts.** Not a batch at the end,
not "when it's all working". The commit is how the increment stops being something only you
remember.

This is not bookkeeping. You are the only one who reads the subagent reports — the user sees
your summaries and the diff, and nothing else. If ten increments land in one working tree, the
reasoning that produced them exists nowhere but your context, which is exactly the thing this
loop is designed to keep discarding. A commit per increment is what survives you.

It also keeps the boundaries recoverable. Ten increments deep, "which change added that
column?" is answerable by `git log` or not at all — reconstructing it from a 70-file working
tree is guesswork, and the guess gets baked in.

Write the message for someone who wasn't here:

- **What changed**, in one line anyone can scan.
- **Why** — the finding that drove it. Name the persona or critic seat if one did: "the parent
  persona couldn't tell which ticket she was picking" beats "improve select labelling".
- **What you declined**, when a report asked for something you chose not to do. Silent drops
  are invisible in a diff, and this is the only place they get recorded.
- **What is deliberately still open**, if the increment shipped with a known gap.

Keep the working tree clean between increments. If an unrelated fix happens mid-loop —
tooling, a stale doc, someone else's bug — commit it **separately**, and do it before the
increment lands rather than letting it ride along. A commit that mixes a UI increment with a
build fix is two commits nobody can revert independently.

Run the project's gates before committing, not after. A commit that fails CI is a commit
someone else has to bisect around.

## Reporting to the user

After each increment, keep it short: what changed, what the personas hit, what you chose not
to fix and why, and any product question that surfaced. The user has not seen any of the
reports either.

## Recording

The commit is the record. Step 6 already requires the increment's message to carry what
changed, the finding that drove it, what was declined and what is deliberately still open —
so a second write-up elsewhere is the same content in a place that can drift from the diff.
Put the reasoning in the commit message and keep it there.
