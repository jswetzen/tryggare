# Conference Child Management System - Implementation Plan v2.0

## Overview
This implementation plan reflects the updated design specification v2.0, incorporating simplified session management (one child = one session max), UUID-based QR security, database-backed admin users, and streamlined GDPR compliance. The plan follows a phased approach optimized for LLM-generated code with the T3 stack (Next.js, TypeScript, tRPC, Prisma).

---

## Dependency Analysis

### Core Dependencies Flow
```
Database Schema (Prisma)
  ↓
Authentication (NextAuth + Admin Users)
  ↓
API Layer (tRPC)
  ↓
Core Business Logic (Session validation, QR tokens)
  ↓
UI Components (Check-in/out, QR pages)
  ↓
Integration Features (i18n, theming, logging)
```

### Key Design Decisions Impact

**One Child = One Session (Enforced)**
- Simplifies validation logic (single boolean check: "is child checked in anywhere?")
- No complex multi-session tracking needed
- Check-out always operates on the one current session

**UUID QR Tokens**
- Generated once on first check-in
- Public read-only access (no auth on QR info pages)
- Actions require admin login

**Database Admin Users**
- Staff attribution for all actions
- Audit trail built-in
- Seed script for initial setup

**Simplified GDPR**
- No automated warnings = less complexity
- Just display last participation dates in admin UI

---

## Phase 0: Requirements Validation (2-3 days)

### Goal
Validate design assumptions and prepare for development.

### Tasks
1. **UI Mockups** (1 day)
   - Check-in flow with session selector
   - Family view with status indicators
   - QR info page layout
   - Check-out interface
   - Admin dashboard structure

2. **Technical Validation** (1 day)
   - Confirm hosting environment (Docker support)
   - Database PostgreSQL version
   - Network accessibility requirements
   - Browser/device matrix for testing


3. **Stakeholder Review** (0.5 days)
   - Walk through mockups
   - Confirm session management model

   - Validate QR security approach
   - Review admin user workflow

4. **Data Seed Planning** (0.5 days)
   - Design sample data structure
   - Plan realistic test scenarios
   - Document edge cases

### Milestone
✅ Design validated, mockups approved, technical environment confirmed


---

## Phase 1: Project Setup and Foundation (2-3 days)

### Goal
Establish core infrastructure with proper data model and security foundation.

### Day 1: Project Initialization
1. **Initialize T3 Stack Project**
   ```bash
   pnpm create t3-app@latest conference-child-mgmt
   # Select: Next.js, TypeScript, tRPC, Prisma, Tailwind
   ```

2. **Add Additional Dependencies**
   ```bash
   pnpm add next-intl date-fns qrcode
   pnpm add -D @types/qrcode
   ```

3. **Configure Project Structure**
   - Set up feature-based folder organization
   - Configure path aliases in `tsconfig.json`
   - Set up environment variables template

4. **Docker Setup**
   - Create `docker-compose.yml` for local dev (app + PostgreSQL)
   - Add `.dockerignore`
   - Configure volume persistence
   - Document startup commands

### Day 2: Database Schema
1. **Define Prisma Schema**
   ```prisma
   model AdminUser {
     id            String   @id @default(cuid())
     username      String   @unique

     passwordHash  String
     name          String
     createdAt     DateTime @default(now())
     lastLogin     DateTime?
     isActive      Boolean  @default(true)
     
     checkIns      CheckInRecord[]
     checkOuts     CheckInRecord[] @relation("CheckOutStaff")
   }

   model Family {
     id                    String   @id @default(cuid())
     lastParticipationDate DateTime?
     
     parents               Parent[]
     children              Child[]
   }

   model Parent {
     id                    String   @id @default(cuid())
     name                  String
     phone                 String?
     email                 String?
     relationshipType      String   // "Mom", "Dad", or free text
     lastParticipationDate DateTime?
     
     familyId              String
     family                Family   @relation(fields: [familyId], references: [id])
   }

   model Child {
     id                    String    @id @default(cuid())
     firstName             String
     lastName              String
     birthdate             DateTime
     allergies             String?
     notes                 String?
     qrToken               String?   @unique // UUID, generated on first check-in
     lastParticipationDate DateTime?
     
     familyId              String
     family                Family    @relation(fields: [familyId], references: [id])
     checkIns              CheckInRecord[]

     
     @@index([qrToken])
     @@index([lastName])
   }

   model Event {
     id        String    @id @default(cuid())
     name      String
     startDate DateTime

     endDate   DateTime
     
     sessions  Session[]
   }

   model Session {
     id              String    @id @default(cuid())
     name            String
     startTime       DateTime
     endTime         DateTime
     isActive        Boolean   @default(false)
     requiresTicket  Boolean   @default(false)
     
     eventId         String
     event           Event     @relation(fields: [eventId], references: [id])
     checkIns        CheckInRecord[]
   }

   model Ticket {
     id          String  @id @default(cuid())
     type        String  // "EVENT_PASS", "SESSION_TICKET", "NONE"
     childId     String
     sessionId   String? // null for event pass
   }


   model CheckInRecord {
     id              String    @id @default(cuid())
     checkInTime     DateTime  @default(now())
     checkOutTime    DateTime?
     pickedUpBy      String?
     
     childId         String
     child           Child     @relation(fields: [childId], references: [id])
     
     sessionId       String
     session         Session   @relation(fields: [sessionId], references: [id])
     
     checkInStaffId  String
     checkInStaff    AdminUser @relation(fields: [checkInStaffId], references: [id])
     
     checkOutStaffId String?
     checkOutStaff   AdminUser? @relation("CheckOutStaff", fields: [checkOutStaffId], references: [id])
     
     @@unique([childId, sessionId, checkInTime])
     @@index([childId])
     @@index([sessionId])
   }

   model AuditLog {
     id          String   @id @default(cuid())
     timestamp   DateTime @default(now())
     userId      String
     action      String   // "CHECK_IN", "CHECK_OUT", "CREATE_FAMILY", etc.
     entityType  String   // "Child", "Family", "Session", etc.
     entityId    String
     details     Json?    // Additional context
     
     @@index([timestamp])
     @@index([userId])
   }
   ```

2. **Set up Prisma Middleware**
   - Audit logging middleware for all mutations
   - Auto-update last participation dates on check-in

3. **Create Initial Migration**
   ```bash
   pnpm prisma migrate dev --name init
   ```

4. **Create Seed Script**
   - First admin user (username: "admin", password: configurable via env)
   - 3 sample families with varied data
   - 2 events with 4 sessions each
   - Mix of checked-in/out states
   - Include expired data for testing

### Day 3: Authentication & Theme/i18n Setup
1. **Configure NextAuth.js**
   - Credentials provider with admin user validation
   - Session strategy (database or JWT)
   - 8-hour session timeout
   - Secure cookie settings

2. **Set up next-intl**
   - Configure locale detection
   - Create initial English translations file
   - Set up message loading
   - Add locale switching component

3. **Configure Theming**
   - Set up CSS variables for light/dark mode
   - Configure Tailwind for theme switching
   - Create theme provider component
   - Add theme toggle UI element

4. **Feature Flags Setup**
   - Environment variables for:
     - Printer integration (stub vs real)
     - Admin management (seed vs full CRUD)
   - Document flag usage

### Milestone
✅ Project initialized, database schema complete, auth working, Docker local dev running

---

## Phase 2: Core API & Business Logic (4-6 days)

### Goal
Build type-safe API layer with all business rules enforced.

### Day 1-2: Authentication & Admin Management APIs
1. **Admin User Management**
   - `adminUser.create` - Add new admin (requires existing admin auth)
   - `adminUser.list` - List all admins
   - `adminUser.deactivate` - Soft delete admin
   - `adminUser.updateLastLogin` - Track login times

2. **Session Management APIs**
   - `session.create` - Create new session
   - `session.list` - List all sessions (with filtering)
   - `session.getActive` - Get currently active sessions
   - `session.activate` - Start a session
   - `session.deactivate` - End a session

3. **Validation Helper Functions**
   - `isChildCheckedIn(childId)` → returns `sessionId | null`
   - `validateTicket(childId, sessionId)` → boolean
   - `getActiveSessionCount()` → number

### Day 3-4: Family & Child APIs

1. **Search & Retrieval**
   - `family.search` - Search by last name, first name, phone
   - `family.getById` - Get family with all relations
   - `family.getByLastParticipation` - For GDPR review
   - `child.getByQrToken` - For QR page lookups


2. **CRUD Operations**
   - `family.create` - Add new family with parents and children
   - `family.update` - Edit family details
   - `child.update` - Edit child details
   - `parent.update` - Edit parent details

3. **QR Token Management**
   - Auto-generate UUID token on first check-in
   - Ensure token uniqueness
   - Index for fast lookups

### Day 5: Check-In API
1. **Check-In Endpoint**: `checkIn.perform`
   - **Input**: 
     ```typescript
     {
       childIds: string[],
       sessionId: string,
       staffId: string
     }
     ```
   - **Validation Logic**:
     ```typescript
     for each childId:
       1. Check if child is currently checked in (any session)
          → if yes, throw error with session name
       2. Validate ticket/pass for selected session
          → if invalid, throw error
       3. Generate QR token if first check-in (null qrToken)
     ```
   - **On Success**:
     - Create CheckInRecord(s)
     - Update lastParticipationDate for child and parents
     - Trigger label print (stub: return QR data URLs)
     - Log action in AuditLog
   - **Response**: Array of QR data URLs for printing

2. **Check-In Validation Helper**
   ```typescript
   async function validateCheckIn(childId: string, sessionId: string) {
     const currentCheckIn = await prisma.checkInRecord.findFirst({
       where: {
         childId,
         checkOutTime: null // Not checked out = currently checked in
       },
       include: { session: true }
     })
     
     if (currentCheckIn) {

       throw new Error(`Child is already checked into ${currentCheckIn.session.name}`)
     }
     
     // Validate ticket...
   }
   ```

### Day 6: Check-Out API
1. **Check-Out Endpoint**: `checkOut.perform`
   - **Input**:
     ```typescript
     {
       childIds: string[],
       pickedUpBy?: string,
       staffId: string
     }
     ```
   - **Logic**:
     ```typescript
     for each childId:
       1. Find current check-in (checkOutTime = null)
       2. Update checkOutTime to now
       3. Set pickedUpBy if provided
       4. Set checkOutStaffId
       5. Log action
     ```
   - **Note**: No session selection needed (child only in one)

2. **Undo Check-Out Endpoint**: `checkOut.undo`
   - Find most recent check-out for child
   - Verify it was within last X minutes (configurable, default 10)
   - Set checkOutTime back to null
   - Log undo action

### Milestone
✅ All core APIs implemented, type-safe, business rules enforced, ready for UI integration

---

## Phase 3: UI Components & Workflows (6-8 days)

### Goal
Build complete user interfaces for all workflows with proper error handling.

### Day 1: Layout & Navigation
1. **Main Layout Component**
   - Header with admin name, logout button
   - Theme toggle

   - Language selector (next-intl)
   - Navigation menu

2. **Login Page**
   - Simple username/password form
   - Error handling for invalid credentials
   - Redirect to dashboard on success

3. **Admin Dashboard** (Home)
   - Current active sessions display
   - Quick stats (total checked in, by session)
   - Recent activity log
   - Quick action buttons (start check-in, check-out, manage)

### Day 2-3: Check-In Station UI
1. **Search Interface**
   - Search bar (last name, first name)
   - Real-time search results
   - "Not found? Add new family" button

2. **Family View Component**
   ```typescript
   interface FamilyViewProps {
     family: Family & { children: Child[], parents: Parent[] }
     currentCheckIns: Map<string, Session> // childId → current session
   }
   ```
   - Display all children with checkboxes
   - Status badges:
     - "Not checked in" (green)
     - "Checked in to [Session]" (blue, with time)
   - Parent contact info display
   - Edit family button

3. **Session Selector Component**
   - Dropdown or radio buttons for session selection
   - Only shows if `activeSessions.length > 1`
   - Auto-selects if only one active session
   - Shows session name, time, event

4. **Check-In Flow**
   - Select children (multiple allowed)
   - Select session (if needed)
   - Click "Check In" button
   - Validation errors displayed inline:
     - "Sarah is already checked into Workshop A. Check out first?"
     - Link to quick check-out or view current session
   - Success: Show QR codes for printing (stub: display on screen)

5. **Add Family Modal**
   - Form for parent details (dynamic add more parents)
   - Form for children details (dynamic add more children)
   - Ticket/pass selection per child
   - Submit creates family and returns to check-in

### Day 4: QR Code Info Page
1. **Public Route**: `/qr/[token]`
   - No auth required for GET
   - Lookup child by qrToken
   - 404 if token invalid

2. **Display Component**
   - Child name (large)
   - Age (calculated from birthdate)
   - Allergies (highlighted if present)
   - Medical notes
   - Parent contacts (name, phone, email)
   - Current status:
     - If checked in: "Checked in to [Session]" + time
     - If not: "Not currently checked in"

3. **Action Buttons**
   - **Check Out** (only if checked in)
     - Requires admin login (redirect if not)
     - Modal with optional "picked up by" field
     - One-click submit
   - **Undo Check Out** (only if recently checked out)
     - Shows time since check-out
     - One-click undo
   - **Edit** (requires admin login)
     - Redirects to edit page
   - **Reprint Label** (stub: download QR as PNG)

### Day 5: Check-Out Station UI
1. **Search Interface** (reuse from check-in)

2. **Family View for Check-Out**
   - Show only checked-in children
   - Display session name for each
   - Checkboxes for selection
   - "Pick up all" quick button

3. **Check-Out Form**
   - Selected children listed
   - Optional "Picked up by" text field
   - Submit button
   - Success confirmation

### Day 6-7: Admin Management UI
1. **Session Management Page**
   - List all sessions (past and future)
   - Filter by event, date
   - Active status indicators
   - Actions:
     - Start session (sets isActive = true)

     - End session (sets isActive = false)
     - Edit session details
     - Create new session

2. **Admin User Management Page**
   - List all admin users
   - Active status indicators
   - Actions:
     - Add new admin
     - Deactivate admin
     - View activity log

3. **Family/Child Search & Edit**
   - Advanced search (by name, phone, last participation)
   - Edit forms for family, parent, child
   - View check-in history
   - Manual data deletion with confirmation

4. **GDPR Data Review**
   - List families by last participation date
   - Sort/filter options
   - Bulk selection for export
   - Export as CSV/JSON
   - Delete with confirmation

### Day 8: Error Handling & Polish
1. **Error UI Components**
   - Toast notifications for success/error
   - Inline validation messages
   - Friendly error pages (404, 500)

2. **Loading States**
   - Skeleton screens for lists
   - Spinner for forms
   - Disabled states during submission

3. **Mobile Responsiveness**
   - Test all pages on mobile viewport
   - Adjust layouts for small screens
   - Touch-friendly button sizes

4. **Accessibility**
   - Keyboard navigation
   - ARIA labels
   - Focus management
   - Color contrast validation

### Milestone
✅ Complete UI implemented, all workflows functional, error handling robust, mobile-friendly

---

## Phase 4: Testing, Optimization & Deployment (4-6 days)

### Goal
Ensure system is production-ready with proper testing and deployment setup.

### Day 1-2: Integration Testing
1. **Critical Path Tests**
   - Full check-in flow (new family)
   - Full check-in flow (returning family)
   - Session selector logic (multiple active sessions)
   - Check-out from QR page
   - Check-out from station
   - Undo check-out
   - Admin user management

2. **Validation Tests**
   - Duplicate check-in prevention
   - Ticket validation
   - QR token generation and lookup
   - Session selection enforcement

3. **Concurrency Tests**
   - Multiple staff checking in simultaneously
   - Same child check-in attempts from different stations
   - Database transaction handling

4. **Edge Cases**
   - Invalid QR tokens
   - Expired sessions
   - Deactivated admin users
   - Empty search results

### Day 3: Performance & Optimization
1. **Database Optimization**
   - Verify indexes on:
     - `Child.qrToken`
     - `Child.lastName`
     - `CheckInRecord.childId`
     - `CheckInRecord.sessionId`
   - Test query performance with large datasets

2. **Frontend Optimization**
   - Implement React Server Components where appropriate
   - Add caching for frequent queries (active sessions)
   - Optimize image/QR generation
   - Bundle size analysis

3. **Load Testing**
   - Simulate 10 concurrent staff members
   - Stress test check-in with 50 children
   - Measure response times

### Day 4: Production Docker Setup
1. **Production Docker Configuration**
   - Multi-stage build for smaller image
   - Health checks for app and database
   - Environment variable management
   - Volume configuration for DB persistence
   - Network security settings

2. **Portainer GitOps Setup**
   - Configure webhook or polling
   - Test automatic deployment on git push
   - Set up stack in Portainer UI
   - Document deployment process


3. **Backup Strategy**
   - Database backup script
   - Scheduled backup task (cron or similar)
   - Backup restoration documentation

### Day 5: Security Audit
1. **Authentication Review**
   - Session security
   - Password hashing (bcrypt/argon2)
   - CSRF protection verification
   - Cookie security flags

2. **Authorization Review**
   - Verify all API endpoints require auth (except QR GET)
   - Check admin-only routes
   - Test unauthorized access attempts

3. **Data Protection**
   - SQL injection prevention (Prisma handles this)
   - XSS prevention (React handles this)
   - HTTPS configuration (document requirements)

### Day 6: Documentation & Handoff
1. **User Documentation**
   - Check-in station guide
   - Check-out station guide
   - Admin management guide
   - Troubleshooting guide

2. **Technical Documentation**
   - Deployment instructions
   - Environment variable reference
   - Database backup/restore procedures
   - Monitoring setup guide

3. **Training Materials**
   - Quick reference cards for staff
   - Video walkthrough of common tasks
   - FAQ document

### Milestone
✅ System tested, optimized, deployed, documented, ready for production use

---

## Phase 5: Future Enhancements (Post-MVP)

### Printer Integration
1. **Brother Printer Selection**
   - Evaluate models for network connectivity
   - Test label sizes and print quality
   - Determine driver requirements

2. **Server-Side Printing**
   - Node.js printing library integration
   - Network printer communication
   - Print queue management
   - Error handling (paper out, offline, etc.)

3. **Label Template Design**
   - Design label layout
   - QR code positioning and sizing
   - Font selection and sizing
   - Test with actual printer

### Additional Features
- Photo upload for children
- Advanced reporting dashboard
- Data import from CSV/Excel
- Mobile app (React Native)
- Offline mode with sync
- Password reset flow for admins
- Automated GDPR retention warnings

---

## Timeline Summary

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Phase 0: Requirements | 2-3 days | 2-3 days |
| Phase 1: Setup | 2-3 days | 4-6 days |
| Phase 2: Core API | 4-6 days | 8-12 days |
| Phase 3: UI | 6-8 days | 14-20 days |
| Phase 4: Testing & Deploy | 4-6 days | 18-26 days |
| **Total MVP** | **18-26 days** | **~4-5 weeks** |

### Resource Assumptions
- 1-2 developers (LLM-assisted)
- Dedicated QA/testing time
- Access to target environment for deployment testing

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Session logic complexity | Medium | Simplified to one-child-one-session, clear validation |
| QR security concerns | High | UUID tokens, public read-only, auth for actions |
| Concurrent check-ins | Medium | Prisma transactions, database constraints |
| Type safety gaps | Low | Full TypeScript + Prisma + tRPC stack |
| Deployment issues | Medium | Docker + Portainer tested early, Phase 1 |
| Missing printer | Low | Already mitigated with stub approach |

---

## Success Criteria

**MVP Complete When:**
- ✅ Admin can log in and manage users
- ✅ Staff can check in children with session selection
- ✅ System prevents duplicate check-ins (one session per child)
- ✅ QR codes generated and accessible publicly
- ✅ Staff can check out children from QR page or station
- ✅ All actions logged with staff attribution
- ✅ Last participation dates tracked
- ✅ Admin can view/edit/delete family data
- ✅ System deployed and accessible on network
- ✅ Mobile-friendly UI tested

- ✅ Documentation complete

**Quality Gates:**
- All critical path integration tests pass
- No type errors in production build
- Load test with 10 concurrent users successful
- Security audit complete with no high-severity issues
- Stakeholder acceptance testing passed

---

## Development Best Practices

### Code Quality
- Use TypeScript strict mode
- Follow Next.js App Router conventions
- Consistent error handling patterns
- Meaningful variable names
- Comments for complex business logic

### Git Workflow
- Feature branches for each phase
- Descriptive commit messages
- Pull request reviews (if team size allows)
- Tag releases for each phase milestone

### Testing Strategy
- Type safety as first line of defense
- Integration tests for critical paths
- Manual testing checklist for each feature
- Browser/device compatibility testing

### LLM Assistance
- Clear, specific prompts for code generation
- Review and understand generated code
- Iterate on generated code for edge cases
- Document any manual modifications

---

## Changes from v1.0

### Simplified
- ✅ Removed multi-session per child complexity
- ✅ Removed automated GDPR retention warnings
- ✅ Clearer session selection logic

### Added
- ✅ Phase 0 for requirements validation
- ✅ UUID QR token generation in data model
- ✅ Admin user management in Phase 2
- ✅ Staff attribution throughout
- ✅ Public QR page access with auth for actions
- ✅ Detailed error handling workflows
- ✅ Security audit in Phase 4

### Enhanced
- ✅ More realistic timeline (4-5 weeks vs 4-6 weeks)
- ✅ Clearer API specifications
- ✅ Better testing coverage
- ✅ Earlier Docker setup (Phase 1)
- ✅ Detailed validation logic examples

---

*Last Updated: November 12, 2025*  
*Version: 2.0*
