# Supervised Check-In Feature - Implementation Tasks

**Feature:** Add support for supervised check-ins where children with guardians present don't require explicit checkout but can still be checked into subsequent sessions.

**Date Started:** 2025-12-11

---

## Recent Completion (2025-12-12)

**E2E Test Database Configuration Fixed:**
- Fixed E2E authentication tests that were failing due to database mismatch
- Reconfigured tests to use live development PostgreSQL database instead of isolated SQLite
- All 4 authentication tests now pass successfully
- See `docs/E2E_DATABASE_CONFIGURATION.md` for details

---

## Design Decisions Summary

- **Data Model:** Add `supervised` boolean field to `CheckInRecord` model
- **Session Validation:** Block supervised check-in to new session only if BOTH `is_active=True` AND `end_time > now()` (Option D)
- **Print Queue:** Show supervised check-ins only from active sessions (not past sessions)
- **Checkout Page:** Show supervised children with "Supervised" badge, allow manual checkout
- **UI Placement:** Per-child supervised checkbox in family check-in flow
- **No Checkout Requirement:** Supervised children can transition to new session after old session ends without explicit checkout
- **Migration:** No backfill needed for existing data

---

## Phase 1: Backend Implementation ✅ COMPLETED (2025-12-12)

### 1.1 Database Model Changes

- [x] Add `supervised` field to `CheckInRecord` model in `backend/checkins/models.py:7-65`
  ```python
  supervised = models.BooleanField(
      default=False,
      help_text="Child is supervised by guardian, no explicit checkout required",
      verbose_name=_("Supervised")
  )
  ```
- [x] Add database index for supervised field (optional, for query optimization)
- [x] Create and run migration: `uv run python backend/manage.py makemigrations`
- [x] Apply migration: `uv run python backend/manage.py migrate`
- [x] Verify migration with: `uv run python backend/verify.py`

### 1.2 Serializer Updates

- [x] Add `supervised` to `CheckInRecordSerializer` fields in `backend/checkins/serializers.py`
- [x] Update validation logic in `CheckInRecordSerializer.validate()` (lines 37-53) to handle supervised session transitions:
  ```python
  def validate(self, data):
      child = data.get("child")
      session = data.get("session")

      if child and session:
          # Check for active check-in to SAME session
          same_session = CheckInRecord.objects.filter(
              child=child,
              session=session,
              check_out_time__isnull=True
          ).exclude(id=self.instance.id if self.instance else None)

          if same_session.exists():
              raise serializers.ValidationError(
                  _("This child is already checked in to this session.")
              )

          # Check for active check-ins to OTHER sessions
          other_sessions = CheckInRecord.objects.filter(
              child=child,
              check_out_time__isnull=True
          ).exclude(session=session).select_related('session')

          for record in other_sessions:
              # Standard check-ins always block
              if not record.supervised:
                  raise serializers.ValidationError(
                      _("Child has active check-in to another session.")
                  )

              # Supervised: only block if BOTH is_active AND end_time not passed
              if record.session.is_active and record.session.end_time > timezone.now():
                  raise serializers.ValidationError(
                      _("Child still in active supervised session.")
                  )

      return data
  ```

### 1.3 View Logic Updates

- [x] Update `check_in` view in `backend/checkins/views.py:32-127` to:
  - Accept `supervised` parameter from request data
  - Pass `supervised` to `CheckInRecord.objects.create()` (line 80-85)
  - Include `supervised` in audit log details (line 95-106)

- [x] Update session overlap validation in `check_in` view (lines 63-72):
  ```python
  # Check for same-session active check-in
  existing = CheckInRecord.objects.filter(
      child=child, session=session, check_out_time__isnull=True
  ).first()

  if existing:
      return Response(
          {"error": _("Child is already checked in to this session")},
          status=status.HTTP_400_BAD_REQUEST,
      )

  # Check for other-session active check-ins
  other_sessions = CheckInRecord.objects.filter(
      child=child,
      check_out_time__isnull=True
  ).exclude(session=session).select_related('session')

  for record in other_sessions:
      # Standard check-ins always block
      if not record.supervised:
          return Response(
              {"error": _("Child has active check-in to another session")},
              status=status.HTTP_400_BAD_REQUEST,
          )

      # Supervised: only block if BOTH conditions true
      if record.session.is_active and record.session.end_time > timezone.now():
          return Response(
              {"error": _("Child still in active supervised session")},
              status=status.HTTP_400_BAD_REQUEST,
          )
  ```

- [x] Update print queue filtering in `print_queue` view (lines 343-530):
  ```python
  # In get_queryset() or filter logic (around line 354-356)
  queryset = CheckInRecord.objects.filter(
      label_printed=False,
      models.Q(
          # Standard check-in still active
          check_out_time__isnull=True,
          supervised=False
      ) | models.Q(
          # Supervised check-in in active session only
          supervised=True,
          check_out_time__isnull=True,
          session__is_active=True,
          session__end_time__gt=timezone.now()
      )
  ).select_related('child', 'session', 'check_in_staff')
  ```

- [x] Verify `check_out` view works with supervised records (no changes needed, but test it)
- [x] Verify `undo` view works with supervised records (no changes needed, but test it)
- [x] Verify `active` view (lines 322-327) includes supervised check-ins correctly

### 1.4 WebSocket Updates

- [x] Update WebSocket broadcast in `check_in` view (lines 109-124) to include `supervised` field:
  ```python
  async_to_sync(channel_layer.group_send)(
      "checkins_broadcast",
      {
          "type": "checkin_broadcast",
          "message": {
              "type": "child_checked_in",
              "child_id": str(child.id),
              "family_id": str(child.family.id),
              "record_id": str(record.id),
              "supervised": record.supervised,  # NEW
          },
      },
  )
  ```

- [x] Verify WebSocket consumer in `backend/checkins/consumers.py` forwards the supervised field (likely no changes needed)

### 1.5 Backend Testing

- [x] Write test: Standard check-in works as before (no supervised flag)
- [x] Write test: Supervised check-in creates record with `supervised=True`
- [x] Write test: Supervised check-in to ended session allows check-in to new session
- [x] Write test: Supervised check-in to active session (is_active=True, end_time in future) blocks new check-in
- [x] Write test: Supervised check-in with is_active=True but end_time passed allows new check-in
- [x] Write test: Supervised check-in with is_active=False but end_time in future allows new check-in
- [x] Write test: Standard check-in always blocks new check-in regardless of session status
- [x] Write test: Print queue shows supervised from active sessions only
- [x] Write test: Print queue excludes supervised from ended sessions
- [x] Write test: Checkout works for supervised records
- [x] Write test: Undo works for supervised records within 5-minute window
- [x] Write test: WebSocket message includes supervised field
- [x] Run full test suite: `uv run python backend/manage.py test` (27 tests, all passing)
- [x] Run verification: `uv run python backend/verify.py` (all checks passed)

---

## Phase 2: Frontend Implementation ✅ COMPLETED (2025-12-12)

### 2.1 Type Definitions

- [x] Add `supervised` field to `CheckInRecord` type in `frontend/src/lib/api/types.ts` or `frontend/src/lib/checkin/types.ts`
  ```typescript
  export interface CheckInRecord {
      id: string;
      child: string;
      session: string;
      check_in_time: string;
      check_out_time: string | null;
      picked_up_by: string | null;
      supervised: boolean;  // NEW
      // ... other fields
  }
  ```

- [x] Add `supervised` field to Child type if needed for local state tracking (not needed - handled via supervisedState record)

### 2.2 Check-In Page Updates

- [x] Add state to track supervised checkbox per child in `frontend/src/routes/checkin/+page.svelte`:
  ```typescript
  let supervisedState = $state<Record<string, boolean>>({});
  ```

- [x] Update `checkInChild()` function (line 385) to pass supervised parameter:
  ```typescript
  const checkInRecord = await checkinApi.checkIn({
      child: childId,
      session: activeSession.id,
      supervised: supervisedState[childId] || false,  // NEW
  });
  ```

- [x] Update `checkInFamily()` function (line 440) to pass supervised per child:
  ```typescript
  const checkInRecords = await Promise.all(
      childIdsToCheckIn.map((childId) =>
          checkinApi.checkIn({
              child: childId,
              session: activeSession.id,
              supervised: supervisedState[childId] || false,  // NEW
          })
      )
  );
  ```

- [x] Update WebSocket handler `handleWebSocketMessage()` (around lines 165-302) to handle supervised field (no changes needed - field is part of the record):
  ```typescript
  if (message.type === 'child_checked_in') {
      const { child_id, family_id, supervised } = message;
      // Update local state with supervised status if needed
      // (likely no changes needed, but verify)
  }
  ```

### 2.3 FamilyCard Component Updates

- [x] Add supervised checkbox UI to `FamilyCard.svelte` child rows (around line 145-173):
  ```svelte
  <!-- In the child row, before or after ChildCheckInButton -->
  {#if !child.checkedIn && child.ticket !== 'none'}
    <div class="flex items-center gap-2 text-sm">
      <input
        type="checkbox"
        id="supervised-{child.id}"
        bind:checked={supervisedState[child.id]}
        class="rounded border-slate-300"
      />
      <label for="supervised-{child.id}" class="text-slate-600 cursor-pointer">
        {$_('checkin.guardianPresent')}
      </label>
    </div>
  {/if}
  ```

- [x] Pass `supervisedState` as prop to FamilyCard from parent page:
  ```typescript
  // In checkin/+page.svelte
  <FamilyCard
    {family}
    bind:supervisedState={supervisedState}
    // ... other props
  />
  ```

- [x] Update FamilyCard props interface to accept `supervisedState`

### 2.4 Checkout Page Updates

- [x] Update checkout record display in `frontend/src/routes/checkout/+page.svelte` to show supervised badge
- [x] Add badge rendering (find the checkout table/list rendering, likely around line 100+):
  ```svelte
  {#each filteredCheckIns as record}
    <div class="checkout-row">
      <div class="child-info">
        {record.child_name}
        {#if record.supervised}
          <span class="px-2 py-0.5 ml-2 text-xs font-semibold bg-blue-100 text-blue-800 rounded">
            {$_('checkout.supervised')}
          </span>
        {/if}
      </div>
      <!-- ... rest of checkout UI -->
    </div>
  {/each}
  ```

- [x] Verify checkout functionality works for supervised records (allow manual checkout - verified working)

### 2.5 Translation Strings

- [x] Add translation keys to `frontend/src/lib/i18n/locales/en.json`:
  ```json
  {
    "checkin": {
      "guardianPresent": "Guardian present",
      // ... existing keys
    },
    "checkout": {
      "supervised": "Supervised",
      // ... existing keys
    }
  }
  ```

- [x] Add same keys to Norwegian translation `frontend/src/lib/i18n/locales/nb.json`:
  ```json
  {
    "checkin": {
      "guardianPresent": "Foresatt til stede",
      // ... existing keys
    },
    "checkout": {
      "supervised": "Under tilsyn",
      // ... existing keys
    }
  }
  ```

### 2.6 Frontend Testing

- [x] Manual test: Check-in child with supervised checkbox checked (✅ verified with Playwright)
- [x] Manual test: Check-in child without supervised checkbox (standard) (✅ verified with Playwright)
- [ ] Manual test: Bulk family check-in with mixed supervised/standard
- [ ] Manual test: Supervised child in ended session can check into new session (backend feature)
- [ ] Manual test: Supervised child in active session blocked from new session (backend feature)
- [x] Manual test: Supervised badge appears on checkout page (✅ verified with Playwright - blue badge visible)
- [x] Manual test: Supervised child can be manually checked out from checkout page (✅ verified working)
- [x] Manual test: Undo supervised check-in within 30 seconds (✅ verified with Playwright)
- [ ] Manual test: WebSocket updates show supervised status across multiple stations
- [ ] Manual test: Print queue shows supervised children from active sessions only (backend feature)

---

## Phase 3: Integration Testing

### 3.1 Development Environment Testing

- [ ] Restart development containers: `echo "restart" > restart.txt`
- [ ] Verify backend server starts without errors (check `web.log`)
- [ ] Verify frontend dev server starts (check `frontend.log`)
- [ ] Test full user flow:
  - [ ] Log in as admin
  - [ ] Create/select active session
  - [ ] Check in child with "Guardian present" checked → Supervised check-in
  - [ ] Check in another child without checkbox → Standard check-in
  - [ ] Verify both appear in print queue
  - [ ] End session
  - [ ] Verify supervised child disappears from print queue
  - [ ] Verify supervised child can check into new session without checkout
  - [ ] Verify standard child blocked from new session until checkout

### 3.2 Production Environment Testing

- [ ] Trigger production rebuild: `echo "restart" > restart.txt`
- [ ] Wait for build to complete (check `build.prod.log`)
- [ ] Run verification script: `./verification.sh --test`
- [ ] Test same user flows as dev environment on production (localhost:8080)
- [ ] Verify static file serving works
- [ ] Verify WebSocket connections work

### 3.3 Multi-Station Testing

- [ ] Open check-in page in two browser windows/tabs
- [ ] Check in supervised child in window 1
- [ ] Verify window 2 receives WebSocket update with supervised status
- [ ] Verify supervised badge appears correctly in both windows
- [ ] Check out supervised child in window 1
- [ ] Verify window 2 updates immediately

---

## Phase 4: Documentation & Cleanup

- [ ] Update `IMPLEMENTATION_PLAN.md` to mark supervised check-in feature complete
- [ ] Document supervised check-in feature in user-facing docs (if any)
- [ ] Update `PROJECT_SPECIFICATION.md` if needed
- [ ] Move this file to `ARCHIVED_TASKS/CURRENT_TASKS_SUPERVISED_CHECKIN_<date>.md`
- [ ] Create git commit with clear message describing the feature
- [ ] Consider creating documentation in `docs/` folder explaining:
  - What supervised check-in is
  - When to use it
  - How session transitions work
  - Edge cases and limitations

---

## Rollback Plan

If issues arise during implementation:

1. **Database rollback:** `uv run python backend/manage.py migrate checkins <previous_migration_number>`
2. **Code rollback:** `git revert <commit_hash>` or `git reset --hard <previous_commit>`
3. **Frontend state:** Clear localStorage in browser if needed
4. **Production:** Restore from backup if database changes were applied

---

## Notes & Decisions Log

- **2025-12-11:** Initial planning completed
- **2025-12-11:** Decided on Option D for session validation (both is_active AND end_time must be true to block)
- **2025-12-11:** Decided on per-child supervised checkboxes in family check-in flow
- **2025-12-11:** Decided supervised children appear in print queue only during active sessions
- **2025-12-11:** Decided supervised children visible on checkout page with badge, can be manually checked out

---

## Success Criteria

- [ ] Supervised check-ins can be created via UI
- [ ] Supervised children can transition to new session after old session ends (both is_active=False OR end_time passed)
- [ ] Standard check-ins still block session transitions as before
- [ ] Print queue shows supervised children only from active sessions
- [ ] Checkout page displays supervised badge correctly
- [ ] Manual checkout works for supervised children
- [ ] WebSocket updates include supervised status
- [ ] All existing tests pass
- [ ] New tests cover supervised check-in scenarios
- [ ] No regressions in standard check-in/checkout functionality
