# Ticket Model Polymorphic Refactoring

**Date**: 2025-12-06
**Phase**: 3.7.2 - Backend Data Model Updates

## Overview

Refactored the Django ticket model from an ambiguous single-table design to a clear polymorphic approach with separate EventTicket and SessionTicket models.

## Problem Statement

The original `Ticket` model had several issues:

1. **Ambiguous Relationships**: Used a `type` field with three values ('EVENT_PASS', 'SESSION_TICKET', 'NONE')
2. **Nullable Session Field**: The `session` ForeignKey was nullable, making it unclear when it should be set
3. **No Type Safety**: No database-level enforcement that SESSION_TICKET must have a session
4. **Confusing EVENT_PASS Logic**: Unclear whether event passes should link to events or sessions
5. **"NONE" Type Anti-Pattern**: Children with no tickets had a "NONE" type ticket record instead of no record

## Solution

### New Model Structure

Created two new concrete models alongside the deprecated base `Ticket` model:

#### EventTicket
- Represents a pass for an entire event
- Grants access to all sessions within the event
- **Required fields**: child (FK), event (FK)
- **Unique constraint**: (child, event) - prevents duplicate event tickets

#### SessionTicket
- Represents a ticket for a specific session
- Grants access only to that session
- **Required fields**: child (FK), session (FK) - session is NOT nullable
- **Unique constraint**: (child, session) - prevents duplicate session tickets

### Key Design Decisions

1. **Keep Legacy Ticket Model**: Marked as deprecated but kept for backwards compatibility
2. **Separate Tables**: Each ticket type has its own table (event_tickets, session_tickets)
3. **Explicit Relationships**: EventTicket → Event, SessionTicket → Session (no ambiguity)
4. **No "NONE" Tickets**: Children without tickets simply have no ticket records
5. **Related Names**: `child.event_tickets`, `child.session_tickets` for clear querying

## Implementation Details

### Files Modified

1. **Models** (`/workspace/check-ins/backend/events/models.py`)
   - Added `EventTicket` model with unique_together constraint
   - Added `SessionTicket` model with unique_together constraint
   - Marked `Ticket` model as deprecated

2. **Serializers** (`/workspace/check-ins/backend/events/serializers.py`)
   - Created `EventTicketSerializer` with computed `ticket_type` field
   - Created `SessionTicketSerializer` with computed `ticket_type` field
   - Marked `TicketSerializer` as deprecated

3. **Views** (`/workspace/check-ins/backend/events/views.py`)
   - Created `EventTicketViewSet` with filtering support
   - Created `SessionTicketViewSet` with filtering support
   - Marked `TicketViewSet` as deprecated

4. **Admin** (`/workspace/check-ins/backend/events/admin.py`)
   - Added `EventTicketAdmin` with autocomplete fields
   - Added `SessionTicketAdmin` with autocomplete fields and event display

5. **URL Routes** (`/workspace/check-ins/backend/config/urls.py`)
   - Registered `/api/event-tickets/` endpoint
   - Registered `/api/session-tickets/` endpoint
   - Kept legacy `/api/tickets/` endpoint (marked deprecated)

6. **Settings** (`/workspace/check-ins/backend/config/settings/`)
   - Added `django_filters` to INSTALLED_APPS
   - Configured `DjangoFilterBackend` in REST_FRAMEWORK settings
   - Updated both base.py and local.py settings

7. **Dependencies** (`/workspace/check-ins/backend/pyproject.toml`)
   - Added `django-filter>=24.0,<25.0` for API filtering support

8. **Seed Data** (`/workspace/check-ins/backend/families/management/commands/seed_sample_data.py`)
   - Updated to use `SessionTicket` instead of deprecated `Ticket`

9. **Tests** (`/workspace/check-ins/backend/events/tests.py`)
   - Created comprehensive test suite (11 tests)
   - Tests for model creation, unique constraints, API endpoints, filtering

### Migrations Created

1. **0003_eventticket_sessionticket.py** (Schema Migration)
   - Creates `event_tickets` table
   - Creates `session_tickets` table
   - Adds indexes and unique constraints

2. **0004_migrate_old_tickets_to_polymorphic.py** (Data Migration)
   - Forward migration: Converts existing Ticket records to new models
     - EVENT_PASS → EventTicket (links to event via session.event)
     - SESSION_TICKET → SessionTicket (links to session)
     - NONE → Deleted (no ticket record created)
   - Reverse migration: Recreates old Ticket records (for rollback)
   - Uses `get_or_create` to avoid duplicates

## API Changes

### New Endpoints

#### GET/POST /api/event-tickets/
**Response Example:**
```json
{
  "id": "uuid",
  "child": "child-uuid",
  "child_name": "John Doe",
  "event": "event-uuid",
  "event_name": "Summer Conference",
  "ticket_type": "EVENT_PASS"
}
```

**Filtering:**
- `?child=<uuid>` - Filter by child
- `?event=<uuid>` - Filter by event

#### GET/POST /api/session-tickets/
**Response Example:**
```json
{
  "id": "uuid",
  "child": "child-uuid",
  "child_name": "John Doe",
  "session": "session-uuid",
  "session_name": "Morning Workshop",
  "event_name": "Summer Conference",
  "ticket_type": "SESSION_TICKET"
}
```

**Filtering:**
- `?child=<uuid>` - Filter by child
- `?session=<uuid>` - Filter by session

### Deprecated Endpoint

- `/api/tickets/` - Still functional but marked for removal in future version

## Database Schema

### event_tickets Table
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PRIMARY KEY |
| child_id | UUID | FK → families_children, NOT NULL |
| event_id | UUID | FK → events, NOT NULL |

**Indexes:**
- child_id
- event_id

**Unique Constraints:**
- (child_id, event_id)

### session_tickets Table
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PRIMARY KEY |
| child_id | UUID | FK → families_children, NOT NULL |
| session_id | UUID | FK → sessions, NOT NULL |

**Indexes:**
- child_id
- session_id

**Unique Constraints:**
- (child_id, session_id)

## Testing

### Test Coverage

Created comprehensive test suite in `/workspace/check-ins/backend/events/tests.py`:

**Model Tests (6 tests):**
- ✅ test_create_event_ticket
- ✅ test_create_session_ticket
- ✅ test_event_ticket_unique_constraint
- ✅ test_session_ticket_unique_constraint
- ✅ test_child_can_have_both_ticket_types

**API Tests (6 tests):**
- ✅ test_list_event_tickets
- ✅ test_create_event_ticket
- ✅ test_list_session_tickets
- ✅ test_create_session_ticket
- ✅ test_filter_tickets_by_child
- ✅ test_unauthenticated_access_denied

### Verification Results

```bash
$ uv run python manage.py test events.tests
Found 11 test(s).
Ran 11 tests in 2.145s
OK

$ uv run python verify.py
✅ ALL VERIFICATIONS PASSED!
Backend is ready to:
  ✓ Commit to git
  ✓ Deploy to production
  ✓ Integrate with frontend
```

## Benefits Achieved

1. **Type Safety**: Database enforces that session tickets must have a session
2. **Clear Semantics**: EventTicket vs SessionTicket is immediately understandable
3. **No Null Checks**: No more checking if `session` is null before using it
4. **Better Queries**: Easy to get all event tickets or all session tickets
5. **Unique Constraints**: Prevents duplicate tickets at database level
6. **Extensibility**: Easy to add new ticket types in future
7. **Clean API**: Separate endpoints for each ticket type
8. **Backwards Compatible**: Legacy Ticket model and API still work

## Migration Guide

### For Frontend Developers

Use the new endpoints instead of legacy `/api/tickets/`:

**Before:**
```javascript
// Old way - ambiguous
GET /api/tickets/?child=<uuid>&type=EVENT_PASS
```

**After:**
```javascript
// New way - clear and explicit
GET /api/event-tickets/?child=<uuid>
GET /api/session-tickets/?child=<uuid>
```

### For Backend Developers

Use the new models instead of the Ticket model:

**Before:**
```python
# Old way
Ticket.objects.create(
    child=child,
    type=Ticket.EVENT_PASS,
    session=some_session  # Confusing: event pass needs session?
)
```

**After:**
```python
# New way - crystal clear
EventTicket.objects.create(
    child=child,
    event=event  # Obvious: event ticket needs event
)

SessionTicket.objects.create(
    child=child,
    session=session  # Required, not nullable
)
```

## Rollback Procedure

If issues arise, the data migration is reversible:

```bash
# Rollback to before polymorphic models
python manage.py migrate events 0002_alter_event_options_alter_session_options_and_more

# This will:
# 1. Recreate old Ticket records from EventTicket/SessionTicket
# 2. Drop the event_tickets and session_tickets tables
```

**Note**: Some data loss may occur in rollback because:
- EventTickets need a session to recreate (picks first session of event)
- Tickets without sessions won't be recreated

## Future Work

1. **Remove Legacy Ticket Model**: After confirming all code uses new models (target: next major version)
2. **Update Child Serializer**: Add computed fields for ticket information
3. **WebSocket Updates**: Ensure real-time updates include ticket changes
4. **Ticket Validation**: Add business logic to validate ticket assignment rules
5. **Bulk Operations**: Add endpoints for bulk ticket assignment

## Conclusion

This refactoring significantly improves the clarity and maintainability of the ticket system. The polymorphic approach makes the data model match the business logic, reducing bugs and making the codebase easier to understand.

All tests pass, backwards compatibility is maintained, and the migration is reversible. The system is ready for production deployment.
