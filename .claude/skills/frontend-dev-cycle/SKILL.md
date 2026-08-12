---
name: frontend-dev-cycle
description: Build-and-critique loop for frontend work — implement one increment, then judge it in parallel with a design critic and context-free user personas, gate the revision plan, and decide whether to ship or loop. Use when polishing or building a UI surface and you want reflection rather than one agent's unchecked opinion of its own work.
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

Then confirm the browser probe is alive:

```bash
cd backend && uv run python ../scripts/ux_probe.py start
```

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

### 2. Critique — all in parallel, in a single message

Spawn together, so they judge the same build and you wait once:

- **`fe-designer`** — the surface that changed. One deliberate Opus spend per round.
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

### 3. Compile

Turn the reports into a revision plan. This is a **diff against the current increment**, not
a re-derivation of the feature.

- Merge findings the same way from different seats — a designer's "the ticket select has no
  label" and a persona's "I couldn't tell what I was picking" are one item, and the fact that
  two seats hit it is evidence of severity.
- Mark each item blocking or polish. Be honest; a plan where everything is blocking is a plan
  with no priorities.
- When two critics want opposite things, **pick one and say why**. Do not average them.
- Drop findings you are choosing not to act on, explicitly, with a reason. Silent drops are
  what the next gate exists to catch.

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

## Reporting to the user

After each increment, keep it short: what changed, what the personas hit, what you chose not
to fix and why, and any product question that surfaced. The user has not seen any of the
reports either.

## Recording

When an increment ships, record it in knowitall (`kind="task"`,
`anchors=[{"kind":"project","name":"tryggare"}]`): what changed, which findings drove it,
what was deliberately declined, and any product question raised. Note the commit if one was
made. Skip the play-by-play of the loop itself — it is not useful later.
