# Conference Child Management System - Design Specification

## Overview
A web application for managing children at conferences with check-in, check-out, label printing with QR codes, and child information lookup.

---

## Data Model

### Children
- First name
- Last name
- Birthdate

- Allergies (text field)
- Notes (free text field for medical/other info)
- Associated parents/guardians (multiple)
- Family grouping
- **QR token** (UUID, unique, indexed) - generated on first check-in
- **Last participation date** (auto-updated on any check-in)

### Parents/Guardians
- Name
- Phone number(s)
- Email address(es)
- Relationship type: Mom / Dad / Other (free text)
- Can be associated with multiple children (families)
- **Last participation date** (auto-updated when any child checks in)

### Admin Users

- Username
- Password (hashed)
- Name (for audit logging)
- Created date
- Last login date
- Active status (for disabling accounts)

### Events
- Event name
- Multi-day capable
- Contains multiple sessions

### Sessions
- Part of an event
- Can be:
  - Open to all (no ticket required)
  - Require tickets
- **One child can only be checked into ONE session at a time (system enforced)**
- **Multiple sessions can be active simultaneously**

### Tickets/Passes
- **Event Pass**: Full multi-day access to all sessions
- **Session Ticket**: Access to specific session(s)
- **No Ticket**: For open sessions


### Check-In/Check-Out Records
- Child ID
- Session ID
- Check-in timestamp
- Check-out timestamp (nullable)
- **Staff member ID** (references Admin Users - who performed action)

- Person who picked up child (optional, free text)

- All database operations logged

---


## Core Features & Workflows

### 1. Check-In Flow

**Session Selection**
- If multiple sessions are active:
  - System displays session selector (required choice)
  - Shows session name, time, event association
  - Clear indication of which session is being selected
- If only one session is active:
  - Auto-selects that session (no UI selector needed)

**New Family (First-Time)**
1. Staff searches by name - family not found
2. Staff adds new family:
   - Parent/guardian details (name, phone, email, relationship)
   - All children details (names, birthdate, allergies, notes)
   - Ticket/pass information
3. Staff selects session (if multiple active)
4. Check in selected children (can be individual or multiple)
5. System validates:
   - Child not already checked into ANY session
   - Has appropriate pass/ticket for selected session
6. **QR token generated** (if first time for this child)
7. System auto-sends to label printer (or displays QR for stub)
8. Labels print with QR codes
9. **Last participation date updated** for child and all associated parents
10. Complete

**Returning Family**
1. Staff searches by last name
2. System shows all children in family with current check-in status
3. Staff selects session (if multiple active)
4. Staff selects which children to check in
5. System validates:
   - **Child not currently checked into ANY session**
   - Has appropriate pass/ticket for selected session
6. Labels auto-print (using existing QR token)
7. **Last participation date updated** for child and all associated parents
8. Complete

**Validation Rules:**
- **CRITICAL: A child can only be checked into ONE session at a time**
- If child is already checked in to a different session:
  - Show error: "Child is already checked into [Session Name]. Please check out first."
  - Offer link to view current check-in or quick check-out
- Individual children can be checked in separately (not all-or-nothing)
- Late arrivals allowed
- Multiple events possible per day with separate sessions
- System shows current session child is checked into (if any)


### 2. Label Printing
- Automatic print after check-in
- Labels include:
  - Child's name
  - QR code (unique per child via QR token, links to info page)
- **QR URL format**: `/qr/[uuid-token]` (e.g., `/qr/abc-def-123-456`)
- **Reprint capability:**
  - Available from QR code info page
  - Available from check-in search/edit page

### 3. QR Code Information Page
**Accessed by scanning child's label**
- **URL pattern**: `/qr/[uuid-token]`
- **Publicly accessible** (no authentication required for read-only view)
- **Security**: UUID tokens (cryptographically secure) prevent guessing

**Display (Read-Only):**
- Child's name
- Birthdate/age
- Allergies (highlighted if present)
- Notes
- Parent/guardian contact information
- **Current check-in status:**
  - If checked in: Show session name, check-in time
  - If not checked in: Show "Not currently checked in"

**Actions Available:**
- **Check-out button** (if currently checked in)
  - One-click checkout from current session

  - No session selection needed (only one possible)
- **Undo accidental checkout** (if recently checked out)
- **Link to Edit page** (requires admin login, redirects to auth if not logged in)

- **Link to Print page** (reprint label)

### 4. Check-Out Flow

**From QR Code Page**
1. Scan child's QR code
2. See current check-in status
3. Tap "Check Out" button

4. Optional: Note who picked them up
5. System records checkout with timestamp and staff member
6. Complete

**From Check-Out Station**
1. Staff searches for family
2. System shows all children from that family with check-in status
3. For checked-in children, displays which session they're in
4. Staff selects which children to check out (can be partial)
5. Optional: Note who picked them up
6. System records checkout with timestamp and staff member
7. **Last participation date remains** (not updated on checkout)
8. Complete

**Rules:**
- Can only check out from the session child is currently in
- No session selection needed (child can only be in one session)
- Partial family pickups allowed
- Who picked up is optional but recommended to note

- Time limit exists but not system-enforced (not critical)

- Undo accidental checkout feature available (time-limited)

---

## User Interface Components

### 1. Check-In Station (Laptop)

- Search functionality (by last name, first name)
- Family view (all children grouped)
- **Session selector** (dropdown/radio buttons if multiple active)
- Check-in status indicators:
  - "Not checked in"
  - "Checked in to [Session Name]" (with timestamp)
- Add/edit family and child details
- Mobile-friendly but optimized for laptop

### 2. Label Printer Station (Laptop)
- Connected to Brother label printer (future)
- Receives auto-print jobs from check-in
- Manual reprint capability
- **MVP: Displays QR code on screen or generates PDF**

### 3. QR Code Info Pages (Mobile-Friendly)
- **Publicly accessible pages** (no login required for viewing)
- Secure URLs using UUID tokens (`/qr/[uuid]`)

- Read-only information display
- Shows current session if checked in
- Action buttons:
  - **Check out** (if checked in) - requires admin login to confirm
  - **Undo checkout** (if recently checked out)
  - **Edit** (requires admin login, redirects if needed)
  - **Print** (reprint label)

### 4. Check-Out Station (Laptop)
- Search functionality
- Family view with check-in status
- Shows which session each child is in (if checked in)
- Checkout controls (individual selection)
- Optional pickup person field

### 5. Admin Dashboard (New)
- View all current check-ins across all active sessions
- Session management (start/end sessions)
- User management (add/remove admin users)
- Search and edit families/children
- View last participation dates for data management
- Audit log view (who did what, when)

---

## Technical Requirements

### Authentication & Access Control
- **Admin users only** - stored in database
- Login required to access system (except QR info pages - read only)
- **Initial setup**: Seed script creates first admin account
- **Admin management**: 
  - Add new admin users
  - Deactivate admin users
  - View admin activity log
- **No password reset flow** (admin must be reset manually by another admin)
- Session timeout after 8 hours of inactivity
- **Staff attribution**: All check-ins/check-outs logged with admin user ID

### QR Code Security Model
- **Token generation**: UUID v4 generated on child's first check-in

- **Token storage**: Indexed field in Children table (`qr_token`)
- **URL format**: `/qr/[uuid-token]` (no child ID exposed)

- **Access control**:
  - Read-only view: Public (no auth)
  - Actions (check-out, edit): Require admin login
  - Action endpoints redirect to login if not authenticated
- **Token persistence**: Never changes (same QR code for life of record)

### Session Management Rules
- **Multiple active sessions allowed** (overlapping is OK)
- **One child = one session maximum** (system enforced at check-in)
- Check-in validation query: `isChildCurrentlyCheckedIn(childId)` returns session ID or null
- Session selector UI appears when `activeSessionCount > 1`
- Default selection: Most recently started session (if only one active, auto-select)

### Internationalization (i18n)
- Built-in from the start
- All UI text translatable
- Support for multiple languages
- Date/time formatting per locale

### Theming System
- Light/dark mode built-in
- Theme switching capability
- Easy adaptation to new themes in code
- Consistent design tokens/variables
- Custom branding support

### Network & Hosting
- Internet required OR local network server (IP-based access)
- Web server with database (avoid cloud service lock-in)
- All stations connect to same server

### Data Management
- Database logging of all operations via Prisma middleware
- Check-in/check-out timestamps visible in system
- **Staff member tracking**: All actions attributed to logged-in admin
- Support for multiple events
- Child/family data persists across events (for returning families)
- **Last participation date tracking**:
  - Auto-updated on check-in for child and associated parents

  - Visible in admin dashboard for data management
  - Used to identify inactive records (manual review/cleanup)

### GDPR Compliance
- **Legitimate Interest basis** (no explicit consent required)
- Store only necessary PII
- Audit trail of data access/modifications
- **Data Retention Approach:**
  - Track last participation date for each family/child
  - Admin can view records by last participation date
  - Manual data deletion / erasure available (Django Admin action and the
    `FamilyViewSet` `erase` API action, both logged)
  - Export family data before deletion (CSV/JSON) — implemented via the
    `export` API action and Django Admin export actions
  - Audit log for all deletions
  - **Optional automated cleanup**: the `anonymize_expired_data` management
    command anonymises records inactive past `DATA_RETENTION_DAYS`. It is
    operator-opt-in (run via cron); there are no in-app retention warnings.
  - See `docs/legal/` for privacy-policy, ToS, LIA, DPA and breach-process
    templates.

### Time & Session Management
- Events have date and time ranges
- Sessions have specific date and time ranges

- **Multiple sessions can be active simultaneously**
- **Session selection required** on check-in if multiple active
- **One child per session** (system enforced, not UI suggestion)
- Clear indication of currently active sessions
- Session start/end times enforced

### Offline/Failure Mode
- No offline capability
- If network/internet fails, all access is lost

### Capacity
- No limits on number of children per session

---

## Future Considerations (Not in Initial Scope)

- Data import functionality
- Photo support for children
- Separate emergency contacts
- Custody/authorization rules
- Payment processing integration
- Capacity limits per session
- Offline mode
- Password reset flow for admins
- Advanced GDPR features (automated retention warnings)
- Mobile native apps

---

## Printer Integration Details
*To be determined in separate design session*
- Brother label printer model (specific model TBD)
- Web integration approach
- QR code generation library: **qrcode** npm package (confirmed)
- Label template design
- **MVP approach**: Display QR on screen or generate PDF download

---

## Open Questions for Next Session

1. Specific Brother printer model and connectivity
2. Label size and template layout
3. Pre-registration workflow (if needed)
4. Reports/statistics requirements
5. Undo checkout time window (how long is "recent"?)
6. Admin account limit (max number of staff users)

---

## Summary of Key Decisions

✅ Individual check-ins allowed (not all-or-nothing)  
✅ Late arrivals permitted  
✅ Multi-day event support with session tracking  
✅ Multiple events per day possible  
✅ **Multiple active sessions allowed simultaneously**  
✅ **One child can only be checked into ONE session at a time (enforced)**  
✅ **Session selection required on check-in if multiple active**  
✅ **Check-out works from any session (no selection needed - child only in one)**  

✅ Check-in status visibility  
✅ Partial family pickups allowed  
✅ **QR pages show single current session (if checked in)**  
✅ **QR URLs use UUID tokens for security (`/qr/[uuid]`)**  
✅ **QR info pages publicly accessible (read-only)**  
✅ **Actions from QR pages require admin login**  
✅ Single contact type (no separate emergency)  
✅ Free text notes field for medical info  
✅ Birthdate tracked  
✅ No photos initially  
✅ Relationship types: Mom/Dad/Other  
✅ All database operations logged  
✅ **Staff member attribution for all actions**  
✅ Reprint from QR info page  
✅ Undo accidental checkout  
✅ **Admin user management (add/deactivate, no password reset)**  
✅ **Seed script for initial admin account**  
✅ Local hosting preferred (avoid cloud lock-in)  
✅ Multiple events supported for returning families  
✅ No capacity limits  
✅ **Last participation date tracking (manual review, no automated warnings)**  
✅ **QR tokens generated on first check-in, persist forever**  

---

## Changes from v1.0

### Major Changes
- **Session Management**: Clarified that multiple active sessions are allowed, but child can only be in one at a time
- **Session Selection**: Required on check-in if multiple active sessions exist
- **Check-out Simplified**: No session selection needed (child only in one session)
- **QR Security Model**: Added UUID token strategy, public read-only access
- **Admin Users**: Added database-backed admin user management with audit trail
- **Staff Attribution**: All actions now logged with staff member ID
- **GDPR Simplification**: Removed automated retention warnings, kept last participation date for manual review
- **QR Token Persistence**: Tokens generated once and never change

### Minor Changes
- Added "last participation date" to data model
- Clarified QR URL format and security approach
- Added admin dashboard to UI components
- Specified session selector UI behavior
- Added validation error messages for check-in conflicts
- Clarified that last participation date updates on check-in only

---

*Last Updated: November 12, 2025*  
*Version: 2.0*
