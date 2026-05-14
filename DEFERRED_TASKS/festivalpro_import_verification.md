# FestivalPro Import Verification

## What this is

Manual verification that the import pipeline produces correct results against real FestivalPro data.
This is an operational task, not a code change.

## Checklist

- [x] Export a real event from FestivalPro
- [x] Run import via the `/import` wizard
- [x] Verify all families are created correctly
- [x] Verify ticket types map correctly (EventTicket vs SessionTicket)
- [x] Verify children with missing birthdates are imported (with null birthdate, ticket still created)
- [x] Verify duplicate bookings are handled idempotently (re-import produces no duplicates)
- [x] Check the import summary for unexpected warnings
- [x] Spot-check a few families in the check-in view

## Notes

- Parser handles duplicate `Ålder` keys (fixed 2026-03-04)
- Bookings with no mappable children are skipped (no empty families created)
- External booking IDs and ticket codes are stored for idempotency
- Extra guardian fields that are JSON arrays (e.g. `["Mark ", ""]`) are now parsed correctly (fixed 2026-03-17)
- Children with missing/unparseable birthdates are imported with `birthdate=None` and a ticket is still created (changed 2026-03-17)
- When two children share a prefix, the FestivalPro export only provides one ETicket code — both children get the same code. This is a data limitation, not a parser bug (verified 2026-03-19)

## Additional tasks
- [x] There is no way to change the event that an import is linked to after creation
- [x] The import source (which has the event connection) is conflated in the UI with the FestivalPro Import Source, it needs a refactor
- [x] What I had to do was to set the event manually

Both resolved 2026-05-13: Added event selector to the sources form (create + edit), with visual section separation between "Source Settings" and provider-specific configuration. Event column also added to the sources table.
