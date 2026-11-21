# Event assistant: a chat on the preview page that drafts an event setup

Implementation plan. Builds on `docs/event-spec-plan.md` (spec, validation, apply),
`docs/setup-checker-plan.md` (warnings), `docs/form-spec-foundation-plan.md` (the spec-driven register page and
its `?preview=1` reload) and the `assistant` app on `feat/llm-provider` (provider config, `agent.py`, `tools.py`).
Roadmap context: `docs/roadmap/registration_form_builder.md`, "The assistant (D)".

## Goals

- An organizer describes the event in chat; the assistant proposes a complete spec; the real public registration
  page, in preview mode, re-renders from that draft; the organizer applies or discards it.
- The preview is **the existing public registration page**, not a copy of it. No second renderer, no iframe.
- A floating, minimizable chat on that page: polished, on-brand, keeps its place across reloads.
- Setup is **purely AI-driven in this UI**. There is no manual editor. Manual changes happen in Django admin
  (which stays the place for event structure, per `docs/roadmap/staff_ui_plan.md`).
- Every guard that exists today stays: validation, staff permissions, empty-event rule, registration never
  opened by apply, no apply tool, personal-data rule.

## Non-goals

- A manual editor, or any form-field config UI, in the SvelteKit app.
- Editing events with registrations (apply refuses them, so the assistant does not run on them).
- Opening registration, pricing logic, patch operations.
- Dark mode: the design system defines none. The chat is light.
- A second provider adapter, an Anthropic adapter, cloud providers (needs the DPA check first, roadmap).
- Advertising the assistant before the eval passes (see Models).
- The external MCP server beyond keeping `mcp_server.py` working; it stays optional.
- Extracting components out of the register page, a `FormPreview` component, iframes, `postMessage`.

## Later (explicitly not in scope)

- **Split screen: preview plus Django admin in an iframe**, so an organizer can hand-edit next to the chat. Not
  needed to keep scope down: the assistant plus the existing "open admin in another tab" covers manual edits,
  and the reload hook works the same after an admin save. If built later it needs `X_FRAME_OPTIONS = "SAMEORIGIN"`
  (prod sets `DENY` in `config/settings/prod.py`; `XFrameOptionsMiddleware` is on in `base.py`) and a reload
  trigger on admin save. Nothing in this plan needs framing today.
- Optional FastMCP server entry point (`mcp_server.py` exists), separate plan.

## Built so far (on `feat/llm-provider`)

- `LLMProvider` row, admin and `/api/assistant/provider/` endpoints, guarded httpx client, key-origin check,
  Fernet-encrypted key, model picker.
- `assistant/tools.py`: plain transport-agnostic functions (`EventTools`: `get_capabilities`, `get_current_spec`,
  `validate_spec`, `diff_spec`, `propose_spec`) served as pydantic-ai `FunctionToolset` via `build_toolset`.
  `assistant/mcp_server.py` is the optional FastMCP wrapper; its dependencies (`fastmcp-slim[server]`,
  `pydantic-ai-slim[mcp]`) are in the optional `mcp` dependency group in `pyproject.toml`.
- `agent.py`: `instructions=SYSTEM_PROMPT`, usage limits (25 requests, 40 tool calls) and a 300 s deadline,
  provider failures collapsed to `ProviderError` codes. The prompt says to change only what was asked and never
  to invent values (dates, capacity, prices).
- New spec validators: `age_bounds_inverted`, `age_label_mismatch`, `discount_as_extra`.
- Guards: no apply tool, personal-data backstop in `validate_spec`/`diff_spec`/`propose_spec`, `Drafts` with
  stale detection, `apply_blockers`.
- Model eval findings so far: qwen invented capacity and registration dates before the "never invent values"
  prompt line, and put age bounds off by one; the validators and the prompt line address both. See Models for
  the context-size finding.
- `manage.py assistant_spike` (one-off runner, to be superseded by the eval command, step 7).

Not built: conversation storage, runner, WebSocket, new endpoints, any frontend, the eval set.

## Decided (by the owner)

| Decision | Why |
|---|---|
| No iframe. The preview is the public registration page in `?preview=1` mode; the chat is mounted on it | One renderer by decision in `form-spec-foundation-plan.md`; chat and page share one Svelte tree, so a draft update calls the reload code directly. |
| Floating, minimizable chat; state survives reload | The organizer needs to see the form while talking. |
| AI-driven only; manual changes in Django admin | Keeps the UI small; admin already works. |
| Plain pydantic-ai function tools; FastMCP wrapper optional (`mcp` dependency group) | One implementation of the tools. |
| Apply and discard are human buttons, never model tools | Roadmap: a human confirms before a form goes live. |
| Conversation stored in our DB, one per (event, user), with its draft | pydantic-ai keeps no state between runs; two organizers must not overwrite each other. |
| WebSocket over Channels for run progress | The repo already runs daphne, channels and valkey; runs take tens of seconds. |
| Apply uses the existing `PUT /api/events/<id>/spec/`, last write wins | One apply path, one set of guards. |
| Provider: Ollama at 192.168.1.60, no key | Chat text stays on the LAN. |

### Proposed defaults, not yet decided by the user

These four were proposed in the previous revision of this plan. They are defaults to build against, not
decisions; the owner confirms or changes each before step 8.

1. **Retention:** delete conversations idle for 30 days (`ASSISTANT_RETENTION_DAYS`, in the existing
   `run_scheduled_retention` job).
2. **PII check on chat text:** warn, do not block (inline warning with "Send anyway"), using `_pii_kind`.
3. **Per-user run rate limit:** one running conversation per user and 20 runs per hour (`ASSISTANT_RUNS_PER_HOUR`).
4. **Eval threshold to advertise a model:** 13 of 15 briefs and zero PII or injection failures.

## Architecture

```
 Browser: /register/<eventId>?preview=1&assistant=1  (the public page, SvelteKit)
 ┌──────────────────────────────────────────┐        Django / daphne
 │ +page.svelte (spec-driven form)          │  HTTP  GET /api/assistant/events/<id>/preview/
 │   loadSpec(): saved or draft spec  ◄─────┼───────►  (draft: apply + build_form_spec, rolled back)
 │   reloadSpec() keeps typed data          │
 │        ▲ onDraftUpdated(prop)            │   WS    ws/assistant/events/<id>/
 │ ┌──────┴───────────────────────────┐    │◄──────►  AssistantConsumer ─► runner.py ─► Ollama /v1
 │ │ AssistantHost (lazy import)      │    │          (auth, perms,       pydantic-ai   (guarded httpx)
 │ │  floating chat + review panel    │    │           one run at a time) FunctionToolset (tools.py)
 │ └──────────────────────────────────┘    │                  │
 └──────────────────────────────────────────┘          AssistantConversation (DB)
                                                       channel group assistant.<conversation_id>
```

- The run is an asyncio task started by the consumer, not awaited by it. A dropped socket does not kill it; it
  publishes to the group `assistant.<conversation_id>`, and any consumer for that conversation (reloaded tab,
  second tab) forwards. One run per conversation, enforced by `status`/`run_started_at` on the row.
- The WS carries progress only. Draft content, preview and conversation text come over HTTP, where DRF
  re-checks permissions on every request.
- Verified: `config/asgi.py` wraps `AllowedHostsOriginValidator(PrinterTokenAuthStack(URLRouter(...)))`, which
  includes `AuthMiddlewareStack`, so `scope["user"]` is the session user. The only consumer today is
  `checkins.consumers.CheckInConsumer` at `ws/checkins/` (`config/routing.py`). Valkey channel layer in `base.py`,
  in-memory in `local.py`, `test.py`, `unit.py`. `frontend/src/lib/stores/websocket.ts` is a singleton for
  `/ws/checkins/` only, so the assistant gets its own store. Same-origin cookies reach the WS as for check-in.

### Entry point (decided): `/events/[eventId]/setup` redirects to `/register/<eventId>?preview=1&assistant=1`

Two layers, each doing one job:

- **The mode switch is the query flag `assistant=1`** on the register page. `assistant=1` implies preview
  (`isPreview` is true when either flag is set), so the existing preview behaviour (window gates bypassed,
  submit disabled) applies unchanged and there is no second code path to keep in sync.
- **The URL people use is `/events/[eventId]/setup`**, a thin SvelteKit route that owns login and eligibility,
  then `goto(..., { replaceState: true })` to the register URL. Admin's change form links to it next to
  "Check setup".

Why not the bare flag as the only entry: `/register/*` is a public path. `hooks.server.ts` lists it in
`PUBLIC_PATHS` and `+layout.ts` returns `{ user: null }` for every `/register/` URL, so the page has no login
redirect, no user and no nav. A staff member who opens `?assistant=1` logged out would get a public form with
nothing happening. `/events/...` is a protected path: `+layout.ts` redirects an unauthenticated visitor to
`/login` for free, and the route can show a proper reason screen (no permission, registration is open or
registrations exist, assistant not enabled) instead of a half-working preview. It also gives the user the URL
name they asked for, and the flag still works if someone pastes it directly (the page then verifies on its own,
see Auth).

The route's `+page.ts` calls `GET /api/assistant/events/<id>/conversation/`: 200 redirects; 401 goes to login;
403, 409 (with the blocker list) and 503 render the reason list. The page itself re-verifies, so the route is
convenience, never the gate. Unknown: whether `/login` returns the user to the original URL (check in step 4;
if not, the route passes nothing and the user clicks the link again).

## Data model (`assistant/models.py`)

`AssistantConversation`, unique on `(event, user)`:

| Field | Notes |
|---|---|
| `id` | UUID. Names the channel group. |
| `event` | FK, `CASCADE`: deleting the event deletes its conversations. |
| `user` | FK to `AUTH_USER_MODEL`, `CASCADE`: deleting the account deletes the chat. |
| `messages` | JSON list, `ModelMessagesTypeAdapter.dump_python(msgs, mode="json")`; loaded with `validate_python`. |
| `draft` | JSON or null: `{"spec", "diff", "warnings", "base", "token", "version"}`. Last `propose_spec` wins. |
| `status`, `run_started_at` | `idle` / `running`. A run older than `RUN_DEADLINE_SECONDS` (300, `agent.py`) plus slack counts as dead and is reset on next connect. |
| `notice_accepted_at` | Set when the organizer confirms the personal-data notice; the consumer refuses `user_message` without it. |
| `created_at`, `updated_at` | `updated_at` drives retention. |

Rules:

- **System prompt is not stored in the history.** `agent.py` passes `instructions=SYSTEM_PROMPT`, not
  `system_prompt=`. With `instructions=` no `SystemPromptPart` is produced and the model gets the current
  instructions on every run even when `message_history` is non-empty (checked on pydantic-ai 2.71). Keep
  `instructions=`, never switch to `system_prompt=`, add a test that stored history has no `system-prompt` part,
  and null the `instructions` copy on each stored `ModelRequest` before saving.
- **Trim before reuse.** Replace tool-return content from earlier runs (`get_capabilities` schema plus example,
  `get_current_spec`) with a short stub when loading history, so stale output does not eat the context window
  (see Models). The history-processor API on 2.71 is unconfirmed (`Agent` takes `capabilities=`): confirm in step 1.
- The UI transcript is derived from `messages` (user prompts and final text parts), not from tool calls.
- **Retention:** proposed default 30 days idle (see Proposed defaults). Chat text can contain personal data
  despite the notice, so it is short-lived, not `DATA_RETENTION_DAYS`.
- **Deletion:** with the event and the user (cascade); on demand by "Clear conversation"
  (`DELETE /api/assistant/events/<id>/conversation/`: messages, draft and `status` reset, notice stays accepted),
  confirm step in-page, never a native `confirm()`.
- Admin: register read-only with message text excluded from list display; `gettext_lazy` on every label and
  entries in both `django.po` files (`make check-messages`).

## WebSocket protocol

Route `ws/assistant/events/<uuid:event_id>/`, added to `config/routing.py`; no new middleware.

Connect checks (any failure closes before `accept`; codes follow the existing 4401 convention):
4401 not authenticated, 4403 lacks the permissions below, 4404 no such event, 4409 event not eligible
(`apply_blockers` non-empty), 4503 provider not enabled.

Client to server (JSON, `type` discriminator, unknown types rejected):

```json
{"type": "user_message", "id": "c-17", "text": "Two-day youth camp, 12 to 17 year olds, 450 kr, lunch extra"}
{"type": "cancel"}
```

Server to client:

```json
{"type": "ready", "conversation_id": "…", "running": false, "draft_version": 3, "notice_required": true}
{"type": "run_started", "run_id": "r-9", "reply_to": "c-17"}
{"type": "tool_started", "run_id": "r-9", "call_id": "t-2", "tool": "validate_spec"}
{"type": "tool_finished", "run_id": "r-9", "call_id": "t-2", "tool": "validate_spec", "ok": false}
{"type": "text_delta", "run_id": "r-9", "text": "I have set up two age bands"}
{"type": "draft_updated", "run_id": "r-9", "draft_version": 4}
{"type": "run_finished", "run_id": "r-9"}
{"type": "run_failed", "run_id": "r-9", "reply_to": "c-17", "code": "timeout"}
{"type": "error", "code": "bad_request"}
```

- `run_failed.code` is one of `timeout`, `limit`, `model_error`, `provider_unreachable`, `auth_failed`,
  `cancelled`, `busy`, `notice_required`, `blocked`, `rate_limited` (runs per hour exceeded), `not_enabled`
  (provider switched off since connect). The client maps codes to i18n strings; no provider body, key or
  exception text goes over the wire (the server logs the code and exception type only).
- A refusal before a run exists (`busy`, `notice_required`, `blocked`, `rate_limited`, `not_enabled`) goes only to
  the sending connection, with `run_id: null` and `reply_to` set. Everything after `run_started` is published to
  every connection of the conversation. `error` answers a malformed frame (bad JSON, unknown `type`, missing
  `id`, empty or over 4000 character `text`) and is not tied to a run.
- `cancel` is honoured once `run_started` was sent; sent earlier it is remembered and applied at that point, so
  a run in setup never leaves its lock behind. The run is a task in the worker process and outlives the
  connection; `cancel` finds it in the same process only (one Daphne process, see Risks).
- Permission is re-checked before every tool call, not only between messages; a revocation ends the run with
  `blocked`. Notice acceptance is the HTTP endpoint (step 3); the consumer only refuses with `notice_required`.
- Tool events carry the tool name and `ok` only, never arguments or results (they contain the spec).
- `draft_updated` fires when `propose_spec` returns without a retry, after the draft is committed to the row.
  **The chat component calls the page's reload function directly** (a prop, see Frontend); the page then
  fetches the draft preview over HTTP.
- `text_delta` forwards `TextPartDelta` from the agent stream. Thinking parts are not forwarded. Local models
  may emit text only after tool calls; the UI must cope with progress events and no text until the end, and
  must not depend on partial tool-argument events (Ollama can deliver them in one piece).
- On `ready` with `running: true` the client shows the working state and waits; it never starts a second run.
- Reconnect: client backoff 1 s doubling to 15 s, then re-fetches the conversation over HTTP. Heartbeat is
  Daphne's.

## Backend modules and endpoints

| Module | Role |
|---|---|
| `assistant/consumers.py` | `AssistantConsumer`: connect checks, group join, dispatch, forwarding. |
| `assistant/runner.py` | `start_run(conversation, text)`: load history (strip, trim), build toolset and agent, stream, persist messages and draft, publish events, release the lock in `finally`. Task registry for `cancel`. |
| `assistant/tools.py`, `agent.py` | Existing. `Drafts` gets an `on_propose` callback so the runner persists the draft when proposed. |
| `assistant/permissions.py` | `can_use_assistant(user, event) -> (ok, issues)`: the one check used by consumer, views and runner. |
| `assistant/views.py` | Existing provider endpoints plus the ones below. |
| `registrations/form_spec.py` | `build_form_spec_from_draft(spec, event)`, see Draft-aware spec endpoint. |

Endpoints (DRF, session auth like `events/spec_views.py`, same error shape; every one calls
`can_use_assistant` per request and answers 401/403/409/503 as the WS codes do):

- `GET    /api/assistant/events/<id>/conversation/` transcript, `running`, `notice_accepted`, `draft_version`,
  and the availability verdict the `/setup` route reads.
- `POST   /api/assistant/events/<id>/conversation/notice/` accept the personal-data notice.
- `DELETE /api/assistant/events/<id>/conversation/` clear.
- `GET    /api/assistant/events/<id>/draft/` `{spec, diff, warnings, stale}` or 404; `stale` = event setup changed
  since the draft (`Drafts.is_stale`, `base_hash`).
- `DELETE /api/assistant/events/<id>/draft/` discard.
- `GET    /api/assistant/events/<id>/preview/` **the page's spec source**, see below.
- Apply is the existing `PUT /api/events/<id>/spec/` with the draft's spec; on 200 the client calls
  `DELETE …/draft/` and reloads. 409 or 400 is shown as the error list.

### Draft-aware spec endpoint

`GET /api/assistant/events/<id>/preview/` is staff-only and returns
`{source: "draft" | "saved", stale, form_spec, diff, warnings}`. `form_spec` is **exactly** the
`RegistrationFormSpec` shape of `GET /registrations/events/<id>/` (`Cache-Control: no-store`), so the page's
types, `formSpec.ts` helpers and `reconcileSelections` work unchanged. With no draft, `source` is `"saved"` and
`form_spec` is `build_form_spec(event)`.

Construction, chosen (rolled-back transaction, no drift):

```python
with transaction.atomic():
    before = {pk of every keyed row of the event}
    event, _diff, _warnings = event_spec.apply(draft["spec"], event)
    spec = build_form_spec(event)
    spec = _stabilise_ids(spec, event, before)
    transaction.set_rollback(True)
```

`build_form_spec` (`registrations/form_spec.py`) reads ORM rows (visible active ticket types, extras with
choices and gates, sessions, sold counts, window status), so reusing it through `apply` guarantees the preview
cannot drift from the public form. Costs: writes and row locks on one event per preview (short, serialised per
event), and the event must pass apply's preconditions, which the assistant already requires. Signal check: the
only `post_save` receiver is `events/signals.py` (session deactivation auto-checkout), which does nothing
without check-ins, and an eligible event has none. The rejected alternative, a hand-written converter spec to
form spec (about 120 to 150 lines duplicating shape logic, with a permanent parity test), stays rejected; revisit
only if previews are seen blocking a concurrent save.

**Unstable ids (decided: stable ids derived from spec keys).** `apply` matches rows by key, so rows that already
exist keep their real ids; but every row the draft *adds* gets a fresh `uuid4` on each rolled-back render. The
page's `reconcileSelections` matches by id, so each reload would clear a tester's selected ticket type or extra
and list it in the "cleared" notice, on every draft update. Fix, in `_stabilise_ids`: after `build_form_spec`,
for each row that did not exist before the apply (`keyed_rows(event)` gives `kind`, `parent`, `key`), compute
`uuid5(event.id, f"{kind}:{parent}/{key}")` and replace the row's real id with it everywhere it appears in the
spec (ticket type ids, `requires_ticket_type_id`, bundle `session_ids`, session ids, extra ids and
`session_id`, `ticket_type_ids`, choice ids). The replacement is a walk over the spec dict mapping string values
through `{real_id: stable_id}`; UUID strings are unique, so there are no false hits. Existing rows keep their real
ids, so a draft that edits an existing event stays consistent with the saved page. Consequences to accept and
test: ids from the draft preview are never valid for a submit (the rows do not exist, so a forged submit 400s;
a second reason, besides the closed window, that no draft preview can create a registration); and after Apply
the new rows get real ids, so selections on rows *added by that draft* are cleared once on the post-apply reload
(accepted, one-off). Rejected: skipping the reconcile notice alone, because the selections would still be
silently dropped, which is worse; it is used additionally, as a UX choice, see Frontend. Test: two consecutive
preview calls with one draft return identical `form_spec`; a preview equals the form spec of an event after a
real apply modulo the remapped ids; row counts are unchanged after a preview.

Limitation to state in the UI help, not fix: promo-code validation on the page (`validate_promo_code`) reads the
saved event, so a code the draft adds is "unknown" in the preview until applied.

## Auth and permissions

- **Who:** all of `VIEW_PERMISSIONS + REPLACE_PERMISSIONS` (`events/services.py`), the same bar as
  `EventTools.__init__`, so nobody can chat toward something they cannot apply.
- **How staff auth reaches the register page (verified, and the reason for the design):** the page is public.
  `PUBLIC_PATHS` in `hooks.server.ts` includes `/register`; `routes/+layout.ts` returns `{ user: null }` for
  every path starting `/register/` and never calls `/auth/check/`. Therefore nothing in the layout tells the page
  who is logged in. In assistant mode the page calls `GET /auth/check/` itself (the session cookie is the same
  origin; `apiClient` already sends it and the CSRF header). This is a UX check only. The real gates are
  server-side: the `/preview/` endpoint, every other assistant endpoint and the WS consumer each re-check
  authentication and permission. If the preview endpoint answers 401/403/409/503, the page falls back to the plain
  saved-spec preview with a small notice and mounts no chat.
- **Public bundle:** without `assistant=1` the page does exactly what it does today: same fetch, no auth call,
  no import. With it, the chat is a dynamic `import()` run only after the auth check shows a user *and* the
  preview endpoint returned 200. The chunk is static JS anyone can download, and holds no secrets or data; what
  protects anything is the server checks above. Test that the public render makes no request to `/auth/check/` or
  `/api/assistant/` and does not load the chunk.
- **Per-request re-check.** The consumer calls `can_use_assistant` at connect and on every `user_message`
  (permissions and `apply_blockers` can change while a tab stays open); every HTTP endpoint on each request. A
  user who loses permission mid-run: the runner re-checks between model requests (a `before_model_request`
  check or a per-tool guard) and aborts with `run_failed: blocked`.
- **Run only when the event passes apply preconditions:** `event_spec.apply_blockers(event)` empty (no open
  registration window, no registrations, issued tickets or check-ins). Otherwise 4409 / `blocked`.
- One conversation per (event, user), derived from `scope["user"]`, never from a client-supplied id.
- `LLMProvider.load().enabled` must be true, else 4503 and no chat is mounted.
- CSRF does not cover WS; origin is enforced by `AllowedHostsOriginValidator` already in `asgi.py`.
- **Framing:** not needed. The chat is part of the page, not embedded, so Django's `X-Frame-Options` is
  irrelevant to this plan (see Later for the iframe case).

### Preview on a draft whose window is closed or not open (verified)

The register page gates `not_open_yet`, `closed` and `not_configured` with `!isPreview &&` (landing screens in
`+page.svelte`, about l.2290-2314), so in preview, and therefore in assistant mode, the form renders whatever
`registration_window_status` the spec carries. A draft always has a non-open window (apply refuses an open one,
`registration_open_on_target`), so assistant mode depends on exactly this bypass. No change needed there; add
a page test for assistant mode with each status.

### Submit is blocked in assistant mode (verified, enforce with a test)

`handleSubmit` returns early on `if (isPreview) return;` (about l.1615) and the submit button is
`disabled={submitting || isPreview}` with a title (about l.3595). Because `isPreview` includes `assistant=1`,
both already apply. Behind them: the server rejects a submit unless `registration_window_status == OPEN`
(`submit_registration`), and draft-only ids do not exist server-side. Add a page test: in assistant mode the
button is disabled and a forced submit event calls `registrationApi.submit` zero times.

## Safety and review

Relied on:

- No apply tool; the model can only `propose_spec` (stores a draft, writes nothing to the event).
- Guarded httpx client (`guarded_http_client`): per-request origin check against the saved base URL, link-local
  addresses refused, no redirects, `trust_env=False`, response size cap.
- Key-origin check: the stored key is only sent to the origin it was saved for (`LLMProvider.key_for`).
- Personal-data backstop on spec arguments (`find_personal_data`), enforced in `validate_spec`, `diff_spec`,
  `propose_spec`. It does not scan the organizer's chat text; the chat-text warning is a proposed default (see
  above). The notice and human review stay the real control.
- Usage limits and deadline per run (25 requests, 40 tool calls, 300 s).
- Prompt: change only what was asked, never invent values; pasted text is data.
- **Accepted risk:** DNS rebinding between the per-request address check and the connection. LAN-only,
  staff-only, admin-configured provider; do not point the provider at an untrusted host.
- Prompt injection: the worst outcome is a bad draft, which is validated and needs a human click to apply.

## Frontend

Root: `frontend/src/lib/assistant/`. Route `src/routes/events/[eventId]/setup/+page.ts` (+ a small
`+page.svelte` for the reason list). The register page keeps being the only renderer.

| File | Role |
|---|---|
| `AssistantHost.svelte` | Lazy-loaded root mounted by the page: bubble <-> panel, composer, transcript, notice, review. Props: `eventId`, `onDraftUpdated`, `onApplied`, `source`, `stale`. |
| `assistantStore.ts` | Per-event socket and state (`connected`, `running`, `messages`, `toolStatus`, `draftVersion`, `error`), backoff reconnect, URL from the `VITE_PUBLIC_WS_BASE_URL` rule of `stores/websocket.ts`. Pure reducer for events, unit-testable without a socket. |
| `lib/api/assistantService.ts` | HTTP calls above through `client.ts` (CSRF and error extraction exist). |
| `ChatMessage.svelte`, `ChatComposer.svelte`, `ToolProgress.svelte`, `PersonalDataNotice.svelte` | Pieces of the panel. |
| `DraftReview.svelte` | Inside the chat: short text list of changes (from `diff`), warnings, stale notice, Apply and Discard. |

**State.** Server: conversation, draft. Client: `localStorage` `assistant.ui.<eventId>` with `{open: boolean}`
only (never message text); default closed on first visit; unread dot when a run finished while minimized.

**Apply flow.** `GET draft` shows what changes ("Ticket type 'Youth pass': added, 450 kr") and warnings; Apply =
`PUT /spec` with `draft.spec`; on success `DELETE draft`, then `onApplied` triggers the page reload, which now
returns `source: "saved"`. Stale draft: Apply stays enabled with "The setup changed since this draft"; last
write wins by decision. The preview itself shows no diff markers (they read as clutter in a form); the review
list is the "what exactly happens" check.

### Register page touch points (`src/routes/register/[eventId]/+page.svelte`, 3.6k lines; only these change)

1. **Imports (about l.16-54):** the spec-source function, the auth-check helper, nothing from `lib/assistant`
   statically (the chat is loaded with `import()`).
2. **`isPreview` (l.150):** `isPreview = preview === '1' || assistantRequested`. Add `assistantRequested`
   (`assistant === '1'`) and a `$state` `assistantMode` set true only once auth and the preview endpoint succeed.
   Add two small `$state`s for what the preview returned: `previewSource` and `previewStale`.
3. **Spec loading in `onMount` (l.769-778):** `registrationApi.getEvent(eventId)` becomes `loadSpec()`, a new
   function: in assistant mode it checks auth, then calls the draft-aware endpoint and falls back to `getEvent`
   on 401/403/409/503; otherwise it is `getEvent` exactly as today.
4. **`handleReloadSpec` (l.790-860):** rename to `reloadSpec(opts)` and make it callable from outside (passed as
   the chat's `onDraftUpdated`). Three edits inside: line `let next = await registrationApi.getEvent(eventId)`
   becomes `await loadSpec()`; `opts.quiet` (assistant mode) suppresses the "cleared" notice and the spinner
   state but still runs `reconcileSelections`; a `reloadQueued` flag so a draft update arriving while a reload
   runs triggers exactly one more reload instead of being dropped. The promo re-validation block stays.
5. **Preview banner (l.2568-2606):** wrap the "Reload form config" button and the `reloadFailed` /
   `reloadNotice` alerts in `{#if !assistantMode}`; in assistant mode render one slim strip with the Draft or
   Saved `Badge` (text, not colour alone) plus a "stale" hint. Public and plain-preview rendering is unchanged.
6. **Mount point (after the form, before `</main>` or after it):** `{#if assistantMode}` lazy host:
   `{#await import('$lib/assistant/AssistantHost.svelte') then m}<m.default .../>{/await}`. The host is
   `position: fixed`, so its place in the template does not affect layout.
7. **No edits needed:** window gates (l.2290-2314) and the submit guards (l.1615, l.3595), which already key on
   `isPreview`; `reconcileSelections` in `formSpec.ts` (stable ids make it correct as is).
8. **Tests (`page.test.ts`):** assistant mode renders with each window status, submit blocked, reload banner
   hidden, public render makes no assistant requests.
9. **i18n:** a handful of `register.*` keys (draft strip, fallback notice) in `en.json` and `sv.json`.

Also: `lib/auth/permissions.ts` is not extended. The server's 403 is the gate, so the frontend carries no copy
of the permission list to drift.

### i18n keys (`en.json` and `sv.json`, same change; Swedish says what is meant)

Namespace `assistant`. Wordmark is not translated and is not used here.

| Key | en | sv |
|---|---|---|
| `assistant.open` | Open assistant | Öppna assistenten |
| `assistant.minimize` | Minimize assistant | Minimera assistenten |
| `assistant.title` | Setup assistant | Hjälp med uppsättningen |
| `assistant.clear` | Clear conversation | Rensa konversationen |
| `assistant.clearConfirm` | Delete this conversation? The draft is removed too. | Ta bort konversationen? Utkastet tas också bort. |
| `assistant.notice.title` | Before you start | Innan du börjar |
| `assistant.notice.body` | Describe the form, not the people. Do not enter names, personnummer, contact details, or health information. | Beskriv formuläret, inte personerna. Skriv inte in namn, personnummer, kontaktuppgifter eller hälsouppgifter. |
| `assistant.notice.accept` | I understand | Jag förstår |
| `assistant.input.label` | Describe what you want | Beskriv vad du vill ha |
| `assistant.input.placeholder` | For example: a two-day camp for ages 12 to 17 | Till exempel: ett tvådagarsläger för 12 till 17 år |
| `assistant.send` / `assistant.cancel` | Send / Stop | Skicka / Avbryt |
| `assistant.working` | Working on it… | Jobbar på det… |
| `assistant.tool.<name>` | Reading the current setup… (one per tool) | Läser den nuvarande uppsättningen… |
| `assistant.draftUpdated` | Draft updated | Utkastet har uppdaterats |
| `assistant.piiWarning` | This looks like personal data. Remove it or describe the rule instead. | Det här ser ut som personuppgifter. Ta bort dem eller beskriv regeln i stället. |
| `assistant.error.<code>` | one per `run_failed.code` | en per kod |
| `assistant.unavailable.<reason>` | why the assistant cannot run here (open registration, registrations exist, not enabled, no permission) | varför assistenten inte kan köras här |
| `assistant.preview.draft` / `.saved` | Draft / Saved | Utkast / Sparat |
| `assistant.preview.promoNote` | Promo codes are checked against the saved setup. | Kampanjkoder kontrolleras mot den sparade uppsättningen. |
| `assistant.review.title` | What will change | Det här ändras |
| `assistant.review.apply` / `.discard` | Apply draft / Discard | Använd utkastet / Släng |
| `assistant.review.stale` | The setup changed after this draft was made. | Uppsättningen har ändrats sedan utkastet gjordes. |
| `assistant.review.applied` | Setup saved. Registration is still closed. | Uppsättningen är sparad. Anmälan är fortfarande stängd. |

Backend strings go in `backend/locale/{en,sv}/LC_MESSAGES/django.po`.

### Accessibility

- Bubble is a `<button>` with `aria-expanded` and `aria-controls`, visible focus ring, 44 px target.
- Panel is a non-modal `role="region"` with `aria-label`; the page behind stays usable (testers type into the
  form while the chat is open). No focus trap.
- Opening moves focus to the composer (or the notice's accept button). **Escape minimizes** and returns focus
  to the bubble. Enter sends, Shift+Enter inserts a newline; Send is disabled while empty.
- Transcript is `role="log"` with `aria-live="polite"` and `aria-busy` while streaming. A visually hidden status
  region announces "Working on it", then "Draft updated" or the error.
- The page's preview strip announces "Preview updated" politely after a reload and never steals focus. A reload
  must not move focus or scroll the form, and keeps typed values.
- `prefers-reduced-motion: reduce` disables the open/close transition and progress animation (scoped to the
  assistant, using `--motion-*` tokens; the repo has no such rule today).
- Mobile: panel is a full-height sheet (`100dvh`, `env(safe-area-inset-*)`) with a visible minimize button;
  composer stays above the on-screen keyboard.

## Visual design

The chat is judged on polish, not just function. This section is binding for the frontend steps.

**Mandate.** Read `docs/design-system/README.md`, `DESIGN_SYSTEM.md`, `HANDOFF.md` and
`frontend/src/lib/styles/tokens.css` before drawing anything. Build each increment through the
`frontend-dev-cycle` skill: `fe-coder` (Sonnet) implements one increment; the three `fe-persona-tester`
personas run (staff organizer, a less technical user on a phone, a break-it user); `fe-designer` (Opus)
critiques last and never edits. The orchestrator reads reports only. `blocker` or `friction` findings are fixed
before the step ships.

**Acceptance criteria** (the designer checks each; a failure is a finding):

1. Tokens only: no hard-coded colour, radius, shadow or font size; `npm run check:tokens` passes; spacing uses
   `--space-*`.
2. Radius rungs: bubble `rounded-pill`, panel and message cards `rounded-card`, composer, send and review
   buttons `rounded-button`. No `--radius-lg`.
3. Colour: `primary` is the assistant's accent. `success` only on the applied/saved state. No gradients, no
   sparkle or "AI" iconography, no emoji (✓ ✗ → only). Icons are inline SVG, stroke 2, `currentColor`, via
   `Icon.svelte`.
4. Type: Plus Jakarta Sans via existing classes; assistant and user text are distinct by alignment and a
   neutral tint, no avatars with faces; sentence case; tone per the design-system content rules.
5. Motion: `--motion-base` for open/close (opacity plus at most a 4 px translate), 1 to 2 px hover lift on the
   bubble, no springs, no per-character animation.
6. Elevation: panel `--shadow-md`, bubble `--shadow-sm`. **The panel must not cover the part of the form being
   tested:** at 1280 px the form (`max-w-2xl`, centred) and the panel sit side by side; the panel never overlaps
   the submit row or the preview strip.
7. States designed, not blank: first open (notice), empty chat (three short example prompts as buttons), working
   (tool progress line), error per code with retry, offline (reconnecting banner), blocked event (reason list),
   long Swedish strings wrap.
8. Viewports: 500 px and 1280 px; full sheet on mobile with an always-reachable minimize control; no horizontal
   scroll at either.
9. Dark mode: not applicable; the chat must not introduce one.

**Screenshot review.** Playwright per `CLAUDE.md` ("Playwright for Manual Testing", login `admin` / `admin123`,
`http://localhost:5173`). On the `dev` host the `frontend-dev-cycle` skill and `fe-designer` drive Claude in
Chrome instead (the Playwright container existed only on the retired `mikro-dev` VM); use what the host provides
and record which. Per step, screenshots at 500x900 and 1280x900, in `en` and `sv`: minimized, open and empty,
mid-run, draft ready with review list, error, blocked, after apply. Keep them under `agent-tools/` unless the
owner asks for `docs/screenshots/`. Preflight: restart `tryggare_web_1` before the round (daphne does not reload
code) and seed fixtures after it (demo mode reseeds hourly and changes event ids).

## Models

- Provider: Ollama at 192.168.1.60, OpenAI-compatible `/v1`, no key (`build_model` sends the placeholder `"none"`).
- **num_ctx failure (observed).** bonsai-2 failed with HTTP 500 "no user query found". Ollama's default
  `num_ctx` for `bonsai-2:27b` is 4096 and one run needs about 7k tokens (tool results such as `get_capabilities`
  push it over); Ollama truncates the user message and the chat template errors. No OpenAI-compatible parameter
  sets `num_ctx`, so the app cannot fix it; the model must be served with a bigger context
  (Modelfile `PARAMETER num_ctx`, or `OLLAMA_CONTEXT_LENGTH` on the server).
- **Required: a model with at least 16k context, 32k preferred.**
- Candidates, both measured on four prompts (one run each, so a tie; the eval decides):
  - `bonsai-2-32k:latest`: camp 72 s, unsupported request refused 27 s, personal data 106 s, Swedish 57 s with
    one stray Chinese character in the output.
  - `qwen3.5-9b-sluss32k`: works, 24 to 156 s.
- Admin help text for the model field states the 16k minimum. History trimming (above) keeps long chats inside
  it, and the eval has a long-conversation case that fails if the instructions are lost.
- **Optional:** when the model list loads, ask Ollama's `/api/show` for the model's context and warn in admin
  when it is under 16k. Detectable only on Ollama (other OpenAI-compatible servers have no such endpoint), and it
  reports the Modelfile's configured value, not necessarily what the server runs with; so it is a hint, not a
  guarantee. Skip if it costs more than a small view change.
- **Gate:** the assistant is advertised (chat mounted for all eligible staff, link in admin) only for a provider
  and model that passed the eval; until then it sits behind `LLMProvider.enabled` and is used by the owner only.

## Testing

Backend (`podman exec tryggare_web_1 uv run pytest tests/unit/` and `manage.py test`; one suite at a time):

- Unit, no network: pydantic-ai `TestModel` and `FunctionModel` (`agent_test_support.py`, `test_agent.py`):
  history round trip; no `system-prompt` part stored and `instructions` nulled; a changed prompt reaches an old
  conversation; trim stubs old tool returns; `propose_spec` persists the draft; a run that proposes nothing
  leaves the draft; limits and timeout map to `run_failed` codes with no body text.
- WS consumer tests with `channels.testing.WebsocketCommunicator`: unauthenticated 4401; no permission 4403;
  wrong event 4404; ineligible event 4409; disabled provider 4503; a full run yields `run_started`, `tool_*`,
  `text_delta`, `draft_updated`, `run_finished` in order; second `user_message` while running gets `busy`;
  permission revoked between messages is refused; a second communicator on the same conversation gets the same
  events.
- Endpoints: draft and preview are per user (another user gets 404, never the draft); a non-staff or
  unauthenticated user gets 401/403 and no spec; preview of a draft equals the form spec of an event after a
  real apply (ignoring remapped ids); two consecutive previews are identical (stable ids); preview leaves the DB
  unchanged (row counts); preview with no draft equals `GET /registrations/events/<id>/`; apply path unchanged.
- Retention command deletes only idle conversations; deleting event or user cascades; clear resets.
- Provider tests stay offline (transport injected into `guarded_http_client`).

Frontend (vitest in `tryggare_frontend_1`; no `+page.test.ts` names): store reducer for every event type;
reconnect and backoff with a fake socket; `AssistantHost` open, minimize, Escape, focus return, persisted
`open`, notice gating; `DraftReview` Apply, Discard, stale, error list; the register page: reload on
`onDraftUpdated` keeps typed data and does not clear selections of unchanged ids, queued reload runs once,
banner chrome hidden in assistant mode, submit blocked, fallback to saved on 403, no assistant requests on the
public render; `/setup` route redirect and reason screen; i18n parity (en and sv key sets equal); svelte-check.

**Eval set** (Ollama, real model, opt-in management command beside `assistant_spike`, never in CI): about 15
briefs in Swedish and English (the walkthrough event, age bands, bundle with sessions, promo code, gated extra,
unsupported request such as sibling discount, PII in the prompt, injected instruction in a pasted text, an edit of
an existing draft, a long conversation near the context limit, a brief with no dates or capacity to check that
nothing is invented, an age-range brief to check bounds). Deterministic pass criteria: ends with a valid draft
or an explicit "not supported"; no spec containing PII; instructions still obeyed after the long conversation;
no invented dates, capacity or prices; wall time recorded. Threshold to advertise a model: proposed default 13
of 15 and zero PII or injection failures (see Proposed defaults).

Persona test: after step 6, `fe-persona-tester` as an organizer who has never seen the tool sets up the
walkthrough event from the `/setup` link to Apply, on a phone-width viewport, in Swedish, no project context.

## Build order

Each step is shippable behind `LLMProvider.enabled`. **Owner model: Sonnet implements, Opus reviews read-only
(the gate), Sonnet fixes;** the gate must pass before the next step (Haiku only for the eval runs in step 7,
per the project notes). Give agents this file's path rather than restating it.

| # | Step | Owner model | Gate | Status |
|---|---|---|---|---|
| 0 | Provider, plain-function tools with optional MCP wrapper, validators, prompt, guards, first model findings | Sonnet | Opus review | **Done** (on `feat/llm-provider`; outstanding: confirm the history-processor API on pydantic-ai 2.71) |
| 1 | `AssistantConversation`, history store/load (strip, trim), `runner.py` with `TestModel`, retention setting and job hook, admin, cascade tests, `.po` entries. A management command can drive a run. | Sonnet | Opus review: history/prompt rules, retention and deletion, PII in stored data | **Built, awaiting review** (`runner.py`; history trimmed on load with a turn cap, no `ProcessHistory` needed; added `AssistantRun` for the rate limit and codes `rate_limited`, `not_enabled`) |
| 2 | `AssistantConsumer`, routing, `permissions.py`, protocol, tool-progress and text events, draft persistence on propose. | Sonnet | Opus review: auth, per-request re-check, one-run lock, no data leaks over WS. WS tests green | **Built, awaiting review** (`consumers.py`, `permissions.py`; runner gained streaming events, `start_run` and a per-tool permission guard; `draft_version` counter on the conversation; `clear_conversation` and `discard_draft` helpers for step 3) |
| 3 | HTTP endpoints: conversation, notice, clear, draft, and `/preview/` with apply, id stabilisation and rollback. | Sonnet | Opus review: rollback safety, per-user scoping, id stability. Parity and stability tests green | Open |
| 4 | Register page hooks: assistant flag and mode, `loadSpec`, `reloadSpec` refactor (quiet, queued), slim strip replacing banner chrome, i18n. Thin `/events/[eventId]/setup` route and admin "Open assistant" link. No chat yet; a debug button drives the reload. | Sonnet (`fe-coder`) | `frontend-dev-cycle` round; Opus review of the page diff (touch points 1-9 only, public render unchanged) | Open |
| 5 | Store, `AssistantHost`, notice, composer, tool progress, lazy mount and gating, i18n, a11y. | Sonnet (`fe-coder`) | Cycle round; designer criteria 1-9; screenshots at both viewports and languages | Open |
| 6 | `DraftReview`, apply and discard, stale handling, error list, post-apply reload. Persona test. | Sonnet (`fe-coder`) | Cycle round plus persona run end to end; Opus review of the apply flow | Open |
| 7 | Eval command and set; run on `bonsai-2-32k` and `qwen3.5-9b-sluss32k` (Haiku agent for the runs); record context size, token cost of `get_capabilities`, thresholds and results. | Sonnet writes, Haiku runs | Opus reviews the criteria; owner decides which model to advertise | Open |
| 8 | Advertise: chat mounted for all eligible staff, docs update (roadmap "Built" note, this file's status), owner confirms the four proposed defaults. | Sonnet | Owner sign-off; DPA note unchanged because the provider is on the LAN | Open |

## Risks

- **Local-model reliability.** Tool calling on Ollama varies by model; mitigated by the eval gate, retries
  (`AGENT_RETRIES`), and validation errors returned as tool results.
- **Context truncation** on Ollama: silent or a 500 (observed); needs a 16k+ model, trim, and an eval case.
- **GPU contention.** A run takes 25 s to 3 min on current candidates (read timeout 120 s, deadline 300 s); the
  one-run lock and the proposed rate limit bound it, and the UI shows progress and a Stop button.
- **Preview cost and locking.** Each draft preview applies and rolls back inside a transaction and locks the
  event briefly; swap to the pure converter only if it is seen to hurt.
- **Page regression.** Touching a 3.6k-line page; the change list is nine points and the existing `page.test.ts`
  is the net.
- **Reload while typing.** A draft update re-renders the form under a tester who is mid-entry; `reloadSpec`
  keeps typed data and selections of unchanged ids, but this is the first time the reload is automatic.
- **Stored chat text may hold personal data** despite the notice: short retention (proposed), clear button,
  input warning (proposed), no chat text in logs or admin list views.
- **Staleness and last-write-wins** can overwrite a colleague's admin edit; the review says so, and apply
  refuses open or non-empty events regardless.
- **Cancel and the one-run registry are per process:** a run is an asyncio task in the Daphne worker that started it. With several workers, `cancel` sent on a connection served elsewhere is ignored (the DB lock still prevents a second run). Revisit if the deployment ever runs more than one.
- **Dev only:** daphne does not hot-reload, so consumer changes need `podman restart tryggare_web_1`.
- DNS-rebinding window on the provider connection: accepted (Safety).

## Open questions (real unknowns)

1. **Which model wins**, `bonsai-2-32k` or `qwen3.5-9b-sluss32k`? One run each, tied. The eval (step 7) answers it.
2. **Token cost of `get_capabilities`** and of a typical run against 16k/32k: a whole run is about 7k, the share of
   `get_capabilities` is unmeasured; drives how hard history is trimmed.
3. **pydantic-ai 2.71 history-trimming API** (`Agent` has `capabilities=`, no `history_processors=`): confirm in
   step 1.
4. **Does `/login` return the user to `/events/<id>/setup`** after sign-in, or only to `/`? Check in step 4; if
   not, a small return-to parameter is needed.
5. **Is the automatic reload acceptable to testers mid-typing?** Only a persona round can say.
6. **The four proposed defaults** (retention days, warn-not-block PII text check, run rate limit and N,
   13/15 threshold) await the owner.
7. **Can Ollama's `/api/show` context be read through the configured provider URL** (optional model-list
   warning)? Unverified.
