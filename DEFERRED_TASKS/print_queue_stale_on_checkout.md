# Print Queue: Stale Entry on Checkout

## Problem

When a child is checked in, a print queue entry is created with status `pending`.
If the child is then checked out (before printing), the print queue entry remains in `pending` state.
This is misleading — the label should not be printed for a child who is no longer checked in.

## Expected behaviour

When a child is checked out, any `pending` print queue entries for that check-in should be
transitioned to a new `cancelled` (or `voided`) state so they no longer appear in the queue.

## Scope

- `printing/models.py` — add `cancelled` status to `PrintQueueEntry`
- `checkins/` checkout logic — on checkout, cancel pending print queue entries for that check-in
- Print queue view — filter out cancelled entries (or show them greyed out)
- Migration needed

## Priority

Low. In practice, labels are usually printed immediately on check-in via WebSocket push.
The stale entry is only an issue if printing is delayed or the printer is offline.
