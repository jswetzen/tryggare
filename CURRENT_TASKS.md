# Phase 2 Implementation Checklist: Core API & Business Logic
**Duration:** 4-6 days
**Goal:** Build type-safe API layer with all business rules enforced

---

## Day 1-2: Authentication & Admin Management APIs ✅ COMPLETE (from Phase 1)

### 1.1 Admin User Management APIs ✅
- [x] `adminUser.create` - Add new admin (requires existing admin auth)
- [x] `adminUser.list` - List all admins (with active filter)
- [x] `adminUser.getById` - Get admin by ID
- [x] `adminUser.deactivate` - Soft delete admin
- [x] `adminUser.reactivate` - Reactivate admin
- [x] `adminUser.updateLastLogin` - Track login times
- [x] Validation: Min 8 char passwords
- [x] Validation: Unique usernames
- [x] Protection: Cannot deactivate self

### 1.2 Session Management APIs ✅
- [x] `session.create` - Create new session with event
- [x] `session.list` - List all sessions (with filtering by event/active)
- [x] `session.getActive` - Get currently active sessions
- [x] `session.getActiveCount` - Count active sessions
- [x] `session.activate` - Start a session
- [x] `session.deactivate` - End a session
- [x] `session.update` - Update session details
- [x] `session.delete` - Delete session (protected if has check-ins)
- [x] Validation: End time after start time
- [x] Validation: Event exists

### 1.3 Validation Helper Functions
- [x] Check if child is checked in (via `child.getCurrentCheckIn`)
- [x] Get active session count (via `session.getActiveCount`)
- [x] Validate check-in (via `checkIn.validate`)
- [ ] Ticket validation (deferred - tickets not in MVP scope)

---

## Day 3-4: Family & Child APIs ✅ COMPLETE

### 2.1 Family Search & Retrieval ✅
- [x] `family.search` - Search by last name, first name, phone
  - [x] Multi-field search (children, parents)
  - [x] Case-insensitive search
  - [x] Limit parameter (default 20, max 100)
  - [x] Ordered by lastParticipationDate
- [x] `family.getById` - Get family with all relations
  - [x] Include parents (ordered by name)
  - [x] Include children (ordered by last name, first name)
- [x] `family.getByLastParticipation` - For GDPR review
  - [x] Find families before specified date
  - [x] Include null dates (never participated)
  - [x] Limit parameter (default 50, max 100)
  - [x] Ordered by oldest first
- [x] `family.list` - Paginated family listing
  - [x] Offset and limit parameters
  - [x] Return total count

### 2.2 Child APIs ✅
- [x] `child.getByQrToken` - For QR page lookups
  - [x] Include family and parents
  - [x] Include current check-in status
  - [x] 404 if token not found
- [x] `child.getById` - Get child with family
- [x] `child.update` - Edit child details
  - [x] firstName, lastName, birthdate
  - [x] allergies, notes (nullable)
- [x] `child.generateQrToken` - Generate/get QR token
  - [x] Auto-generate UUID if not exists
  - [x] Return existing if already has token
  - [x] Return isNew flag
- [x] `child.getCheckInHistory` - View check-in history
  - [x] Include session details
  - [x] Include staff names
  - [x] Ordered by most recent
  - [x] Limit parameter (default 20, max 100)
- [x] `child.getCurrentCheckIn` - Check current check-in status
  - [x] Return null if not checked in
  - [x] Include session details
- [x] `child.delete` - Delete child
  - [x] Protected: Cannot delete if has check-in history

### 2.3 Parent APIs ✅
- [x] `parent.getById` - Get parent with family
- [x] `parent.create` - Add parent to existing family
  - [x] Validate family exists
  - [x] Required: name, relationshipType
  - [x] Optional: phone, email
- [x] `parent.update` - Edit parent details
  - [x] name, phone, email, relationshipType
  - [x] Email validation (or empty string)
- [x] `parent.delete` - Delete parent
  - [x] Protected: Cannot delete last parent in family

### 2.4 Family CRUD Operations ✅
- [x] `family.create` - Add new family with parents and children
  - [x] Nested creation (parents and children in one call)
  - [x] Min 1 parent required
  - [x] Min 1 child required
  - [x] Validation: Email format (or empty)
  - [x] Returns created family with all relations
- [x] `family.update` - Edit family details
  - [x] Update lastParticipationDate
- [x] `family.delete` - Delete family
  - [x] Protected: Cannot delete if children have check-in history
  - [x] Cascades to parents and children

### 2.5 QR Token Management ✅
- [x] Auto-generate UUID token on first check-in
- [x] Ensure token uniqueness (database unique constraint)
- [x] Index on qrToken for fast lookups (in schema)
- [x] Token returned in check-in response

---

## Day 5: Check-In API ✅ COMPLETE

### 3.1 Check-In Endpoint: `checkIn.perform` ✅
- [x] **Input validation**:
  - [x] childIds: Array of strings (min 1)
  - [x] sessionId: String
  - [x] staffId: Auto-extracted from session context
- [x] **Validation logic** (per child):
  - [x] Verify child exists
  - [x] Check if child is currently checked in (any session)
  - [x] If yes, throw error with session name
  - [x] Verify session exists and is active
  - [x] Generate QR token if first check-in (null qrToken)
- [x] **On success**:
  - [x] Create CheckInRecord(s)
  - [x] Auto-update lastParticipationDate (via middleware)
    - [x] Child.lastParticipationDate
    - [x] Family.lastParticipationDate
    - [x] All Parents.lastParticipationDate
  - [x] Log action in AuditLog (via middleware)
  - [x] Return QR tokens for each child
- [x] **Batch operation support**:
  - [x] Handle multiple children in single call
  - [x] Return validation errors per child
  - [x] Fail entire operation if any validation fails
- [x] **Response format**:
  - [x] success: boolean
  - [x] checkIns: Array of results
  - [x] count: Number of successful check-ins
  - [x] Each result includes: childId, childName, qrToken

### 3.2 Check-In Helper Endpoints ✅
- [x] `checkIn.getCurrentCheckIns` - Get all currently checked-in children
  - [x] Optional sessionId filter
  - [x] Include child with family and parents
  - [x] Include session details
  - [x] Include check-in staff name
  - [x] Ordered by most recent
- [x] `checkIn.validate` - Pre-validate check-in without performing
  - [x] Check session active
  - [x] Check child exists
  - [x] Check not already checked in
  - [x] Return validation result with reasons

### 3.3 Business Rules Enforced ✅
- [x] Child can only be checked into ONE session at a time
- [x] Session must be active to accept check-ins
- [x] QR tokens are UUIDs (RFC 4122)
- [x] Clear error messages for validation failures

---

## Day 6: Check-Out API ✅ COMPLETE

### 4.1 Check-Out Endpoint: `checkOut.perform` ✅
- [x] **Input validation**:
  - [x] childIds: Array of strings (min 1)
  - [x] pickedUpBy: Optional string
  - [x] staffId: Auto-extracted from session context
- [x] **Validation logic** (per child):
  - [x] Find current check-in (checkOutTime = null)
  - [x] If not found, throw error with child name
- [x] **On success**:
  - [x] Update checkOutTime to now
  - [x] Set pickedUpBy if provided
  - [x] Set checkOutStaffId
  - [x] Log action in AuditLog (via middleware)
- [x] **Batch operation support**:
  - [x] Handle multiple children in single call
  - [x] Return validation errors per child
  - [x] Fail entire operation if any validation fails
- [x] **Response format**:
  - [x] success: boolean
  - [x] checkOuts: Array of results
  - [x] count: Number of successful check-outs
  - [x] Each result includes: childId, childName, checkOutTime, pickedUpBy, sessionName

### 4.2 Undo Check-Out Endpoint: `checkOut.undo` ✅
- [x] **Input**: checkInRecordId (string)
- [x] **Logic**:
  - [x] Find check-in record by ID
  - [x] Verify child is checked out (checkOutTime not null)
  - [x] Verify check-out was within last 5 minutes
  - [x] Set checkOutTime back to null
  - [x] Clear pickedUpBy
  - [x] Clear checkOutStaffId
  - [x] Log undo action (via middleware)
- [x] **Error handling**:
  - [x] 404 if record not found
  - [x] Error if not checked out
  - [x] Error if outside 5-minute window

### 4.3 Check-Out Helper Endpoints ✅
- [x] `checkOut.getRecent` - Get recent check-outs (last 24 hours)
  - [x] Optional sessionId filter
  - [x] Limit parameter (default 50, max 100)
  - [x] Include child with family and parents
  - [x] Include session name
  - [x] Include check-out staff name
  - [x] Add canUndo flag (true if within 5 minutes)
  - [x] Ordered by most recent
- [x] `checkOut.getStats` - Session statistics
  - [x] sessionId input
  - [x] Return: totalCheckIns, totalCheckOuts, currentlyCheckedIn
  - [x] Calculate check-out rate percentage

### 4.4 Business Rules Enforced ✅
- [x] Can only check out children currently checked in
- [x] Undo limited to 5-minute window
- [x] Optional pickup person tracking
- [x] Clear error messages for validation failures

---

## Phase 2 Completion Criteria

### Core Functionality ✅
- [x] All 5 routers implemented (family, child, parent, checkIn, checkOut)
- [x] 25 tRPC endpoints created
- [x] All endpoints are protected procedures (auth required)
- [x] Comprehensive input validation with Zod schemas
- [x] Type-safe across entire API layer
- [x] Business rules enforced in all operations

### Data Integrity ✅
- [x] Cannot delete entities with check-in history
- [x] Cannot check in child to multiple sessions
- [x] Cannot check out child not checked in
- [x] Last parent protection
- [x] Session must be active for check-ins
- [x] QR token uniqueness enforced

### Middleware Integration ✅
- [x] Audit logging working (all CRUD operations logged)
- [x] Participation dates auto-updated (child → parents → family)
- [x] User context properly set in tRPC procedures
- [x] Error handling throughout

### Code Quality ✅
- [x] TypeScript compilation clean (no errors)
- [x] All 113 existing tests passing
- [x] Clear error messages with proper TRPCError codes
- [x] Consistent naming conventions
- [x] Well-documented endpoints

### Testing Status
- [x] Existing tests passing (113 → 210 tests)
- [x] Comprehensive router tests ✨ NEW
  - [x] Family router (21 tests) - search, CRUD, GDPR compliance
  - [x] Child router (23 tests) - QR tokens, history, check-in status
  - [x] Parent router (15 tests) - CRUD, last parent protection
  - [x] Check-in router (29 tests) - validation, batch operations, QR generation
  - [x] Check-out router (29 tests) - undo, stats, recent check-outs
- [ ] Integration tests for end-to-end workflows (Phase 3)
- [x] Edge case coverage (comprehensive)

---

## Phase 2 Milestone: ✅ COMPLETE

**Status:** Phase 2 Core API & Business Logic is fully implemented and tested!

**Ready for:**
- Phase 3: UI Components & Workflows
- Frontend integration with tRPC hooks
- End-to-end testing with real workflows

**What's Working:**
- Complete family management (search, CRUD, GDPR)
- Child management with QR token generation
- Parent management with protections
- Full check-in flow with validation
- Full check-out flow with undo capability
- Session management from Phase 1
- Admin user management from Phase 1
- Authentication and middleware from Phase 1

---

*Phase 2 Checklist Created: November 14, 2025*
*Based on: IMPLEMENTATION_PLAN.md Phase 2*
