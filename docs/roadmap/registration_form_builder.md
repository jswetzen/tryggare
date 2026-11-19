# Registration Form Builder (with optional AI assistant)

**Status:** Foundations built (form spec, event copy, event spec with export/validate/diff/apply). The setup checker beyond the spec's warnings, the editor and the assistant are not. Revised after an Opus review of the first draft.
**Priority:** Medium. Demand is unproven, so the first steps are cheap and use the existing models. First trial: one organization with an annual conference (see "Scope and first trial").

## Problem

Setting up a registration for an event is hard. Tickets, age-tiered prices, extras that belong to one session or one person, promo codes, family groups, and consent per person all have to be combined correctly. Organizers want help with this. Whether the help needs AI is an open question.

We do not know yet that setup effort is a bottleneck. The maintainer wants form-building support, and that want is real. The chat assistant is one possible shape, to be judged against cheaper ones.

## Non-goals

- Parent-facing builder. This is for organizers only.
- Automatic publishing. A human confirms before a form goes live.
- Letting a model compute prices, write HTML, or touch payments or attendee data.

## What exists today

- The parent registration form is a hand-written page (`frontend/src/routes/register/[eventId]/+page.svelte`). It renders from a read-only form spec (`backend/registrations/form_spec.py`, see `docs/form-spec-foundation-plan.md`); which person fields appear and are required still comes from code constants, not stored configuration.
- Pricing lives in `backend/registrations/pricing.py` (`calculate_total`, `calculate_discount`). It works on saved registrations and price snapshots. It is the single source of truth and must not be duplicated.
- `TicketType.capacity` is enforced for guest self-registration (`backend/events/models.py`).
- `Extra.session` gives session-scoped extras. Extras are deliberately never free text.
- `Registration.promo_code` is a single FK, so a registration takes at most one promo code.
- `duplicate_extra_to_event` (`backend/events/services.py`) already clones extras between events.
- An **event spec** exists (`backend/events/event_spec/`; design in `docs/event-spec-plan.md`): a typed JSON description of an event's setup (event, sessions, ticket types, extras with choices, promo codes), with rows referring to each other by key. The package offers `export`, `validate`, `diff` and `apply`. It is the authoring format for options B and D, and `copy_event` is built on it.
  - Interfaces (staff REST API and `manage.py event_spec`) and who may use them: see `docs/event-spec-plan.md`.
  - Validation layers: shape (pydantic), references, the model `clean()` rules, a going-live check, then warnings (setup checks, the start of option C).
  - Guards: apply is one transaction; it refuses a target that has registrations, tickets or check-ins, or whose registration is open; it never opens registration (an open window in a spec is an error); rows keep their ids when matched by key.
  - `copy_event` goes through the spec, so it refuses a source that breaks the validation rules (model `clean()` rules, negative prices, cross-event references) and drops a registration window that the move would leave open or already past (self-serve off; the admin says so). Ordering ties are a warning for a new event.
- Still missing: line items, `RegistrationGroup`, and waitlists (see `event_registration_ux_case_catalog.md` §1.4, §5.2, §4.3).
- Staff edit live rows in Django admin while sales are open (catalog §9.4). There is no draft or published state.

## Options

| Option | What it gives | Cost | Needs an LLM |
|---|---|---|---|
| A. Clone event config (ticket types, extras, promo codes) from a previous event | Most setup done for recurring events | Low | No |
| C. Setup checker on live rows | Flags gaps: an age tier with no price, a promo whose ticket types are all inactive, a hidden type no code unlocks, a ticket with no price | Low | No |
| B. Structured editor with live preview | Organizer edits a typed spec; preview matches live | High | No |
| D. Chat assistant that proposes config from natural language | Organizer describes the event; config is proposed, diffed, then applied | High | Yes |

Recommendation: start with A and C on the existing models, with no spec. They are cheap and they test demand. B and D depend on design work that only makes sense once demand is shown.

## Phasing

1. **Baseline.** Record how many custom setups happened in the last year and how long each took. Without this, nothing else can be measured.
2. **Setup checker (C).** Management command or admin view over live rows. No spec needed.
3. **Clone config (A).** Extend `duplicate_extra_to_event` to ticket types and promo codes.
4. **Pilot.** Use A and C on a real event. Compare time and missing pieces against the baseline.
5. **Decision gate.** If setups are rare, or A and C cover them, stop here.
6. **Shared basket function.** Refactor `pricing.py` into a pure function over a basket that both live checkout and preview call.
7. **Draft and publish.** Versioned event config, with rules for editing an event that already has registrations, sold tickets, and price snapshots. Ticket types, extras and choices are `PROTECT` once sold.
8. **Spec and editor (B).** Typed spec derived from the real models, editor with preview on the same code path as live.
9. **Eval harness.** Organizer prompts with expected configs, scored per provider and model.
10. **Assistant (D).** One provider first, proposes a draft, the diff is shown, a human applies it.
11. **Second provider adapter.**

## Design notes for B and D

### Pricing

No second pricing implementation. The spec's price rules must compile into the shared basket function from step 6. Pricing tests use real cases from the catalog. Avoid examples the models cannot express. The sibling discount is not expressible with `PromoCode` or `TicketType` and would need a schema change.

### Preview

Preview runs the same validation and pricing as live. A preview with submit disabled does not exercise the 48h verification TTL or the 7-day payment TTL (`registrations/models.py`). Preview must either run through the real registration state machine in a sandbox, or state clearly which TTL behavior it does not show.

### Validation is not correctness

Schema validation checks shape, not meaning. Safeguards:
- pricing tests with worked examples;
- a diff before publish, against the current live version (which requires the draft and publish model from step 7);
- an explicit human publish action.

Do not describe the system as "can't do anything wrong".

### The assistant (D)

- Its only output is tool calls against the spec. Each call is validated, and errors go back to the model as tool results so it retries.
- It runs with the organizer's permissions, scoped to one event.
- Its context contains event, ticket, and form configuration only.
- It receives the capability list, so it can say "not supported" rather than inventing a field.
- Pasted text is data. It changes config only through validated tool calls.

#### Personal data is forbidden (applies to D and feature requests)

No personal data may go into the builder or into a feature request: no names, personnummer, contact details, health or allergy information, or anything else about a child, parent, or staff member. This is a rule, not a filter. Enforced in three places:

1. **Notice to the organizer.** The builder UI and the feature-request form state the rule before the first input. The text is short and says what to remove, for example "Describe the form, not the people. Do not enter names, personnummer, contact details, or health information."
2. **System prompt.** The model is told never to accept, repeat, store, or act on personal data. If the organizer includes some, it must say so, refuse to use that part, and ask for the rule-level description instead. It never writes personal data into a tool call.
3. **Human review before submission.** A feature request is a draft until the organizer has seen the exact text that will be stored and confirmed it. The maintainer then reviews the request before any email is sent. Nothing is emailed or stored as a request without these two steps.

The prompt and notice are not a guarantee, since a model can miss something. The human review steps are the real control. As a backstop, a deterministic check on feature-request text can reject obvious patterns (email addresses, phone numbers, personnummer-like digit runs) before the draft is shown. This is a cheap extra, not a substitute for review.

#### Feature request content

See `feature_requests.md`: the record structure, the personal-data rules, the local record with manual GitHub export (replacing the earlier email-to-maintainer idea), and the assistant's `file_feature_request` tool.

### Providers (D only)

Two adapters cover the list:
1. Anthropic Messages API with tool use.
2. OpenAI-compatible chat completions with tool use. Covers OpenAI, OpenRouter, and Ollama.

Provider, base URL, model, and key come from settings or environment, never from source. Keys are encrypted at rest, never sent to the frontend, and never logged.

`docs/legal/DPA_NOTE.md` does not mention AI or LLM providers. It covers self-hosting, SaaS, and imports. A cloud provider needs its own check: what it receives, whether it retains or trains on it, and what happens to text organizers paste. This must be done before a cloud provider is enabled for real events.

Ollama tool-calling reliability depends heavily on the model. A provider or model is advertised only after it passes the eval.

## Scope and first trial

Decided: this is for the open-source release, and the first trial is one organization that runs an annual conference.

Consequences:
- **Annual setup fits option A.** A recurring conference is set up once a year, so cloning last year's ticket types, extras, and promo codes is the most likely first win. This is the strongest evidence so far for building A and C first.
- **Keys are per deployment.** Each self-hosted instance holds its own provider key, set in settings or environment. Per-organizer keys can wait until a hosted version exists. The trial org runs one deployment with one key.
- **Open source raises the bar for defaults.** The shipped code must not contain keys, provider endpoints tied to one vendor, or a default model that requires a paid key. Local Ollama must work out of the box for anyone who doesn't want a cloud provider.
- **Personal-data rules apply to every deployment**, not just the trial. The rule in "Personal data is forbidden" is part of the product, not site policy.

### Trial data source: FestivalPro

The trial org's last conference was registered in FestivalPro and brought in through the `/import` wizard (`backend/imports/`, `docs/roadmap/festivalpro_import_verification.md`). The import works, but configuring it is cumbersome: source setup, linking the event, and mapping the export to ticket types and extras. Option A's "clone last year's config" does not cover this, because last year's config lives in FestivalPro, not in this system.

Two consequences:
- **The baseline is the import setup, not a registration setup.** Time how long the trial org's FestivalPro import configuration takes, and what they had to fix by hand, as the first measurement.
- **A mapping helper is a candidate in its own right.** Suggesting how FestivalPro columns map to our ticket types, extras, and promo codes could be more useful than building the form builder. It must work only on column headers and the export's structure, never on row contents. The export is full of personal data, and the personal-data rule applies to any AI step that sees it.

### No one has built a form in Tryggare yet

Building a registration form in FestivalPro is painful. There is no measurement of building one in Tryggare, because no organizer has done it. Agents have built forms during testing, but agent difficulty says nothing about organizer difficulty: agents don't get confused the way a volunteer admin does, and they don't need the docs.

So the baseline needs two measurements, both by a real organizer:
- **FestivalPro:** the trial org's admin times how long their current conference form takes to build, and lists every point where they got stuck.
- **Tryggare:** the same admin builds the conference form in Tryggare on a dev or demo stack, timed, with the same notes. The stack holds no real personal data, and the rule in "Personal data is forbidden" applies to anything they type.

Only the Tryggare measurement says whether the form builder, the checker, or cloning would help. If the Tryggare run is already easy, the builder is not worth building. If it is stuck at the same places as FestivalPro, the stuck points become the first things to fix.

## Open questions

1. How long does building the conference form take in FestivalPro, and in Tryggare when a real organizer does it? These two timed runs are the baseline from phasing step 1, and the trial org can supply both.
2. Who pays for cloud model usage? For the trial, the org or the maintainer; for open-source deployments, each operator.
3. Does the trial org accept a cloud provider at all, given the data review in "Providers (D only)"? If not, D starts with Ollama only.

## Kill criteria

- If the baseline shows setups are rare, or the pilot shows A and C cover organizer needs, stop before B.
- If the eval shows no model, local or cloud, reaches an agreed accuracy bar, and cloud providers are ruled out by the data review, stop before D.
- Agree the thresholds before the eval runs. Twenty prompts is enough to catch gross failures, not to rank models.

## Related

- `event_registration_ux_case_catalog.md`: the cases any config must express, and the punch list of missing concepts.
- `registration_data_model_hardening.md`: done. Its remaining gaps are in the catalog.
- `staff_ui_plan.md`: the admin UI that B and C would sit in.
- `open_source_launch.md`: affects key and personal-data decisions.
