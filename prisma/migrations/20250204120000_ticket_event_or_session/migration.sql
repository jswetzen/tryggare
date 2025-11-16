-- Add support for linking tickets directly to events
ALTER TABLE "tickets"
  ADD COLUMN "event_id" TEXT;

-- Attempt to backfill event passes (session_id IS NULL) by looking at the child's
-- current active check-in and copying that session's event. If we can't
-- determine the event, the column will remain NULL and will require manual
-- follow-up before applying the constraint.
WITH child_current_event AS (
  SELECT DISTINCT ON (cir.child_id)
    cir.child_id,
    s.event_id
  FROM "check_in_records" cir
  JOIN "sessions" s ON s.id = cir.session_id
  WHERE cir.check_out_time IS NULL
  ORDER BY cir.child_id, cir.check_in_time DESC
)
UPDATE "tickets" t
SET "event_id" = cce.event_id
FROM child_current_event cce
WHERE t.child_id = cce.child_id
  AND t.session_id IS NULL
  AND t.event_id IS NULL;

-- Enforce referential integrity and indexing for the new column
ALTER TABLE "tickets"
  ADD CONSTRAINT "tickets_event_id_fkey" FOREIGN KEY ("event_id") REFERENCES "events"("id") ON DELETE CASCADE ON UPDATE CASCADE;

CREATE INDEX IF NOT EXISTS "tickets_event_id_idx" ON "tickets"("event_id");

-- Ensure there is an index on session_id to support lookups with the new constraint
CREATE INDEX IF NOT EXISTS "tickets_session_id_idx" ON "tickets"("session_id");

-- Require exactly one of event_id or session_id to be populated
ALTER TABLE "tickets"
  ADD CONSTRAINT "tickets_require_event_or_session"
  CHECK (
    ((CASE WHEN "event_id" IS NULL THEN 0 ELSE 1 END) +
     (CASE WHEN "session_id" IS NULL THEN 0 ELSE 1 END)) = 1
  );
