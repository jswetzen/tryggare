# Feature requests: structure and flow

**Status:** Design. Phase 0 (this format, filled in by hand) is in use: `docs/trials/2026-11-19-feature-requests.md`.
**Priority:** Medium. It is cheap, and it is how the form builder (`registration_form_builder.md`) learns what organizers can't express.

## Problem

When an organizer, or the assistant (option D in `registration_form_builder.md`), wants something the product can't express, the result today is a silent workaround. The 2026-11-19 agent trial (`docs/trials/2026-11-19-agent-ui-trial.md`) built a "13-17 only" add-on as an extra open to every child, and nobody would have heard about it. The gap should become a structured request that can be counted, deduplicated and acted on.

## Where requests come from

| Source | When | Who writes the text |
|---|---|---|
| `organizer` | They hit a gap in admin or the setup UI | The organizer, in a form with the personal-data notice |
| `assistant` | A brief, or part of one, can't be expressed against the spec | The model drafts; the organizer confirms |
| `validator` | The organizer marks a validator warning as "intended: the product can't do what I want" | Prefilled from the warning code; the organizer adds the need |
| `trial` / `eval` | A trial or eval run finds a gap or a misleading surface | The person or agent writing the trial report |
| `maintainer` | Triage, or a request split out of another | The maintainer |

## The record

```python
Source   = Literal["organizer", "assistant", "validator", "trial", "eval", "maintainer"]
Severity = Literal["blocks", "wrong_result", "risk", "friction", "cosmetic"]
Reach    = Literal["most_events", "some_events", "few_events"]
Layer    = Literal["validator", "model", "admin_ui", "public_form", "spec_example", "docs"]
Status   = Literal["draft", "confirmed", "triaged", "planned", "done", "declined", "duplicate"]

class Workaround(BaseModel):
    used: str = Field(max_length=400)   # what was built instead, generalised
    cost: Literal["none", "extra_steps", "wrong_result", "not_possible"]

class Evidence(BaseModel):
    kind: Literal["trial", "eval_case", "validation_code", "spec_path", "issue", "doc"]
    ref: str = Field(max_length=200)    # a path, code or doc anchor; never a value

class FeatureRequest(BaseModel):
    id: str                              # "FR-<n>" locally; the issue number once filed upstream
    title: str = Field(max_length=100)   # the need, not the fix
    source: Source
    problem: str = Field(max_length=600) # the organizer's need, generalised
    tried: list[str] = Field(max_length=5)          # each <= 300 chars
    workaround: Workaround | None
    desired: str = Field(max_length=600)
    touches: list[str]                   # controlled vocabulary, see below
    severity: Severity                   # worst outcome if unaddressed
    reach: Reach                         # how many events would hit it
    layers: list[Layer]                  # where a fix would live
    validator: Literal["existing", "new_warning", "no"]  # see below
    evidence: list[Evidence]
    brief_fragment: str | None = Field(None, max_length=300)  # assistant only, generalised
    dedupe_key: str
    duplicate_of: str | None = None
    seen: int = 1                        # bumped on each merged duplicate
    status: Status = "draft"
```

Meanings that are not obvious:

- **severity.** `blocks`: the brief can't be built at all. `wrong_result`: something was built but behaves differently from the brief (money, eligibility, door rules). `risk`: works today, but a plausible organizer action does damage, such as opening registration by accident or picking another event's row. `friction`: extra steps or guessing. `cosmetic`: no effect on the result.
- **validator.** `existing`: a current code already flags it. `new_warning`: the spec already holds the data, so a warning in `_validate.py` could catch it with no model change. `no`: needs a model, UI or doc change first.
- **brief_fragment.** The part of the organizer's brief the assistant could not express, rewritten as a rule ("an add-on for one age band, bought on top of the pass"), never quoted.
- **Local-only fields.** `created_at`, the confirming user, and the event the request came from are stored on the instance and never exported.

### Controlled vocabulary (`touches`)

Requests are only countable if they name things the same way. `touches` takes prefixed terms:

| Prefix | Source of truth | Example |
|---|---|---|
| `cap:` | `CAPABILITIES` in `backend/events/event_spec/schema.py`, supported and unsupported ids | `cap:family_groups` |
| `code:` | validator issue codes in `event_spec/_validate.py` | `code:registration_open` |
| `field:` | `Model.field` | `field:Extra.applies_to` |
| `spec:` | spec path with `[]` instead of indices | `spec:ticket_types[].requires_ticket_type` |
| `admin:` | an admin surface | `admin:copy_event` |
| `new:` | a proposed capability id, not yet in `CAPABILITIES` | `new:extra_eligibility` |

A `new:` id that recurs is promoted into `CAPABILITIES["unsupported"]`, so the assistant can name it in its next "not supported" answer. That makes the unsupported list and the request log the same vocabulary. A request that uses a validator code says why the organizer could not just fix the warning.

### Deduplication

`dedupe_key` is one primary `touches` term, plus `#<slug>` when one term covers several needs, e.g. `new:extra_eligibility#age-window`. A new request whose key matches an open one is merged: `seen` goes up, its evidence is appended, and its free text is kept as a comment for the maintainer, not merged into the original. The key travels with the export, so upstream issues can carry a `fr:<dedupe_key>` label and be found before a duplicate is filed.

## Personal data is forbidden

The rule and its three controls (notice, system prompt, human review) are in `registration_form_builder.md`, "Personal data is forbidden". The structure adds:

- **No row values anywhere.** Evidence is a path or code (`spec:extras[].session`), never the value at that path. There is no field for an event id, a registration reference, or a row's content.
- **Shapes, not data.** Free text describes the setup's shape: "a child pass for ages 13-17", not birthdate bounds; "two weeks before the start", not a date; "a family of one adult and one child", not a family. Event and ticket names are config, not personal data, but they identify an organization, so they are generalised too.
- **Vocabulary first.** Anything a `touches` term can say goes there, which shrinks the free text.
- **Deterministic check before the draft is shown.** Free text is rejected if it contains an email address, a phone number, a personnummer-like digit run, an ISO date, a UUID, or a registration-reference-like token. For the assistant, the rejection is a tool error and it rewrites. A backstop, not the control: human review still is.
- **Export strips local-only fields.**

## Where requests go

**Chosen: a local model with an admin view as the record, plus a manual export to the GitHub issue form.** Nothing leaves the instance unless a person copies it out.

- A self-hosted instance must not phone home by default, so automatic GitHub posting or email is out. This replaces the "optional email to the maintainer" in `registration_form_builder.md`, "Feature request content", which should then point here.
- The local list is useful on its own. An operator sees what their organizers keep missing, and `seen` turns ten silent workarounds into one counted request.
- Export is an admin action, "Copy as GitHub issue". It renders the record as markdown in the issue form's sections and offers a prefilled `github.com/.../issues/new` link that the operator's own browser opens. The server makes no request.
- An opt-in direct submit can come later if operators ask for it; it would be off by default.

## How the assistant files one

One tool, next to the spec tools:

```json
{
  "name": "file_feature_request",
  "input": {
    "title": "string <= 100",
    "problem": "string <= 600",
    "brief_fragment": "string <= 300",
    "tried": ["string <= 300"],
    "workaround": {"used": "string <= 400", "cost": "none|extra_steps|wrong_result|not_possible"},
    "desired": "string <= 600",
    "touches": ["cap:...|code:...|field:...|spec:...|new:..."],
    "severity": "blocks|wrong_result|risk|friction|cosmetic"
  }
}
```

The tool validates shape, runs the deterministic check, and computes `dedupe_key` and `reach` itself. On success it returns a draft id and any open request with the same key. The model calls it when a capability is `unsupported`, when it had to choose a workaround, or when the organizer rejects a validator warning as unfixable. It still builds the closest valid setup, so the request records the workaround instead of replacing it.

The organizer sees a card in the conversation: the personal-data notice, the exact text that will be stored, the workaround that was built into their event and what it costs ("the workshop is offered to every child"), and "Joins an existing request seen 3 times" when there is a match. Buttons: confirm, edit, discard. Nothing is stored as `confirmed` without that click.

## Phasing

0. **Markdown only (now).** Requests are written in this format as YAML blocks in a markdown file, by hand or by an agent writing a trial report. Change `.github/ISSUE_TEMPLATE/feature_request.md` into an issue form with the same sections: problem, tried, workaround and its cost, desired, touches, severity, evidence, and a personal-data notice at the top. No code.
1. **Vocabulary.** Add recurring `new:` ids to `CAPABILITIES["unsupported"]`. Add the `new_warning` items to `_validate.py`. Fix `example.json`.
2. **Admin "check this event".** It shows warnings (`staff_ui_plan.md`). Each warning gets a "this is intended: the product can't do it" link that opens a prefilled request.
3. **Model and admin view.** A `FeatureRequest` table, an organizer form with the notice and the check, list and merge views, and the export action.
4. **Assistant tool.** `file_feature_request` above, with evals that include briefs the spec can't express. The expected output is a request, not an invented field.

## Open questions

1. Who may file: any staff user with event-change rights, or Administrator only?
2. Language. Organizers will write in Swedish, but upstream issues are in English. Does the export translate (assistant), or does the operator?
3. Should a dismissed validator warning be stored on the event, so the checker stops repeating it, independently of any request?
4. Who curates `new:` ids upstream, and at what `seen` count across issues is one promoted to `CAPABILITIES`?
5. Rate limits per user and per day, and whether `draft` requests that are never confirmed expire.
