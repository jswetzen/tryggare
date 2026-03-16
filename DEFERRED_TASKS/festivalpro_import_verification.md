# FestivalPro Import Verification

## What this is

Manual verification that the import pipeline produces correct results against real FestivalPro data.
This is an operational task, not a code change.

## Checklist

- [ ] Export a real event from FestivalPro
- [ ] Run import via the `/import` wizard
- [ ] Verify all families are created correctly
- [ ] Verify ticket types map correctly (EventTicket vs SessionTicket)
- [ ] Verify children with missing birthdates are imported (with null birthdate, no ticket)
- [ ] Verify duplicate bookings are handled idempotently (re-import produces no duplicates)
- [ ] Check the import summary for unexpected warnings
- [ ] Spot-check a few families in the check-in view

## Notes

- Parser handles duplicate `Ålder` keys (fixed 2026-03-04)
- Bookings with no mappable children are skipped (no empty families created)
- External booking IDs and ticket codes are stored for idempotency
