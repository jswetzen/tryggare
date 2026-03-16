# Planning.Center Check-ins Import

## Goal

Support importing families and children from Planning.Center so churches using that platform
can use this check-in system.

## Priority

Low — this enables a specific use case (church trial) but is not needed for the festival workflow.

## What Planning.Center provides

Planning.Center has a Check-Ins product with an API. Key resources:
- `EventTime` — a session/slot
- `Person` — the checked-in individual
- `Household` — family grouping
- API docs: https://developer.planning.center/docs/#/apps/check-ins

## Implementation sketch

1. Add `planning_center` as an `ImportSource` choice in the imports app
2. Create `PlanningCenterFetcher` that authenticates via OAuth or Personal Access Token
3. Map Planning.Center data model to our Family/Child/Ticket model:
   - `Household` → `Family`
   - `Person` (child) → `Child`
   - `EventTime` → `Session` or `Event`
4. Add frontend support in the import wizard for Planning.Center source type

## Open questions

- Does the church need live sync or one-time import?
- Do they use Check-Ins for age-group ticketing or just attendance?
- Personal Access Token is simpler than OAuth for a small deployment

## Related

- See existing `ImportSource` pattern in `backend/imports/`
- FestivalPro fetcher is in `importer.py` as reference
