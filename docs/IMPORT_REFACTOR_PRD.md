# PRD: Import Source Refactor

**Status:** Ready for implementation  
**Scope:** Refactor only — no new provider logic  

---

## Background

The current import system was built around a single external booking platform (FestivalPro). The abstractions reflect this: `ImportProvider` stores credentials and URLs, `EventImportConfig` stores the per-event field mappings, and the import engine assumes FestivalPro's data shape throughout.

A second import source (Planning Center) needs to be added. Planning Center has a proper API, a different data shape, no manual prefix mapping, and will initially be used to import families only — not tied to a specific event.

Rather than bolt Planning Center onto the existing FestivalPro-shaped model, this refactor establishes a clean provider abstraction first. The goal is a model where each import source has a type, type-specific configuration lives in an extension model, and the import engine dispatches to provider-specific logic. Planning Center is **not** implemented in this refactor — only the structural foundation for it.

---

## Goals

- Replace `ImportProvider` + `EventImportConfig` with a unified `ImportSource` model
- Make FestivalPro-specific logic explicit and contained (parser, fetcher, field mappings)
- Allow an import source to be scoped to an event (with tickets) or to families only (no event)
- Restructure the import wizard UI so provider-specific steps are delegated to provider components
- No change to the import reconciliation logic or `ImportRun` behaviour beyond the FK rename

---

## Out of Scope

- Planning Center provider implementation
- Credential sharing across multiple events (accepted limitation for now)
- Async import execution
- Any changes to `parser.py` internals or the FestivalPro parsing logic

---

## Data Model

### `ImportSource` (replaces `ImportProvider` + `EventImportConfig`)

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `name` | CharField | Human-readable label, e.g. "SK26 2026 – FestivalPro" |
| `provider_type` | CharField | Choices: `festivalpro`, `planningcenter` |
| `event` | FK → Event, nullable | If set: event-scoped import with tickets. If null: family-only import |
| `credentials` | BinaryField, nullable | Encrypted, same mechanism as current `ImportProvider.credentials` |
| `created_at` | DateTimeField | |
| `updated_at` | DateTimeField | |

`ImportSource` carries no provider-specific configuration fields directly. Those live in extension models.

### `FestivalProImportSource` (replaces `EventImportConfig` fields)

One-to-one extension of `ImportSource`. Only exists for sources where `provider_type = festivalpro`.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `source` | OneToOneField → ImportSource | |
| `login_url` | URLField | |
| `export_url` | URLField | |
| `export_body` | TextField | Raw form-encoded POST body, no credentials |
| `field_mappings` | JSONField | Maps prefix keys to `full_event`, session UUID, or `ignore`. Refreshed each sync |

### `ImportRun` (updated FK only)

`config` FK renamed to `source`, now pointing to `ImportSource` instead of `EventImportConfig`. No other changes to this model.

### Models removed

- `ImportProvider`
- `EventImportConfig`

---

## Backend Changes

### Module restructuring

The current `imports/` app gains a `providers/` subpackage:

```
imports/
  providers/
    __init__.py
    base.py          # Abstract base class / protocol for providers
    festivalpro.py   # fetch_from_provider(), parse logic delegation
```

`importer.py` grows a dispatch step: given an `ImportSource`, it instantiates the correct provider and delegates fetch + parse to it. The reconciliation logic (family/child/ticket creation) remains in `importer.py` and is provider-agnostic.

### `base.py`

Defines the interface all providers must implement:

```python
class ImportSourceProvider:
    def fetch(self, source: ImportSource) -> dict:
        """Fetch raw data and return parsed booking dict."""
        raise NotImplementedError

    def requires_event(self) -> bool:
        """Return True if this provider requires an event FK on the source."""
        raise NotImplementedError
```

### `festivalpro.py`

Moves `fetch_from_provider()` from `importer.py` into this module, wrapping it as a `FestivalProProvider` that implements the base interface. No logic changes — this is a move, not a rewrite.

### `run_import()` signature change

```python
# Before
def run_import(raw_json: dict, config: EventImportConfig, user) -> ImportRun

# After
def run_import(raw_json: dict, source: ImportSource, user) -> ImportRun
```

`ImportRun.config` FK becomes `ImportRun.source`.

### Serializers

- `ImportProviderSerializer` → `ImportSourceSerializer`
- `EventImportConfigSerializer` absorbed into `ImportSourceSerializer` (FestivalPro-specific fields nested or provided via a separate `FestivalProImportSourceSerializer`)
- `ImportRunListSerializer` / `ImportRunSerializer`: `config` field renamed to `source`

### URL changes

| Old | New |
|---|---|
| `GET/POST /api/imports/providers/` | `GET/POST /api/imports/sources/` |
| `GET/PUT/DELETE /api/imports/providers/<id>/` | `GET/PUT/DELETE /api/imports/sources/<id>/` |
| `GET /api/imports/events/<event_id>/config/` | Removed — config is now on the source |
| `PATCH /api/imports/events/<event_id>/config/provider/` | Removed — source is created directly with event FK |
| `POST /api/imports/events/<event_id>/run/` | `POST /api/imports/sources/<source_id>/run/` |
| `GET /api/imports/events/<event_id>/history/` | `GET /api/imports/sources/<source_id>/history/` |
| `POST /api/imports/discover-prefixes/` | Unchanged (generic, takes raw JSON string) |
| `POST /api/imports/events/<event_id>/discover-prefixes/` | `POST /api/imports/sources/<source_id>/discover-prefixes/` |

---

## UI Changes

### Naming

All user-facing references to "Provider" are renamed to "Import Source" (or "Source" in compact contexts). The `/import/providers` route becomes `/import/sources`.

### Wizard restructuring

The current import wizard (`/import/[eventId]/+page.svelte`) is split into:

- **Shell component** (`/import/[sourceId]/+page.svelte`): owns step state, history panel, and results step (step 3). These are provider-agnostic.
- **Provider step components**: step 1 (upload/fetch) and step 2 (mapping) are delegated to a provider-specific component. The shell renders the correct component based on `source.provider_type`.

For this refactor, only the FestivalPro step component is implemented — it is a direct extraction of the existing step 1 and step 2 UI with no logic changes. A Planning Center step component stub may be added as an empty placeholder.

### Import source management

The providers list page (`/import/sources`) continues to work as before. Creating a new source now includes a `provider_type` selector. FestivalPro sources show the login URL, export URL, export body, and credentials fields. Other provider types show a placeholder.

### Entry point change

The current entry point is event-first: `/import` lists events, each event links to its import wizard. After the refactor, the entry point is source-first: `/import/sources` lists all import sources (with their associated event name if scoped, or "Family import" if not). This is a minor navigation change — the event list page at `/import` can remain as a convenience shortcut for event-scoped sources.

---

## Migration

A data migration is required to move existing data:

1. Create `ImportSource` record for each existing `ImportProvider` record, with `provider_type = festivalpro` and the same credentials
2. Create `FestivalProImportSource` record for each existing `EventImportConfig`, linked to the corresponding `ImportSource`, carrying over `login_url`, `export_url`, `export_body`, and `field_mappings`
3. Set `event` FK on each `ImportSource` from the corresponding `EventImportConfig.event`
4. Update all `ImportRun.config` FKs to point to the new `ImportSource` records
5. Drop `ImportProvider` and `EventImportConfig` tables

---

## What Is Not Changing

- `parser.py` and all FestivalPro parsing logic — treated as a black box
- `encryption.py` — unchanged
- `ImportRun` model fields beyond the FK rename
- The reconciliation logic in `importer.py` (family/child/ticket creation)
- All existing tests — test fixtures will need FK updates but test logic is unchanged

