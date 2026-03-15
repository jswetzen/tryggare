# Future Tasks & Enhancements

This document contains deferred features from Phase 3 and planned work for Phase 4 and beyond.

---

## Phase 3 Deferred Items

These items were marked as optional or deferred during Phase 3 implementation. They can be added as enhancements when needed.

### Check-In Station Enhancements

#### Add Family Modal (from Day 2-3, Section 2.6) ✅ COMPLETED
- [x] Create `src/components/check-in/add-family-modal.tsx`
  - [x] Quick add form with minimal fields:
    - [x] Parent name (required)
    - [x] Phone number (required)
    - [x] Child first/last name (required)
    - [x] Child birthdate (required)
    - [x] Allergies (optional)
  - [x] Form validation
    - [x] Required field indicators
    - [x] Inline validation messages
    - [x] Submit disabled until valid
  - [x] Submit using `family.create` tRPC endpoint
    - [x] Loading state
    - [x] Error handling with toast
    - [x] Success: close modal, auto-select new family
- [x] Add "Not found? Add new family" button to check-in search page
- [x] Added English and Swedish translations for all modal fields

### QR Code Page Enhancements (from Day 4, Sections 3.4-3.5) ✅ COMPLETED

#### Check-Out from QR Page ✅ COMPLETED
- [x] Add check-out button to QR page
  - [x] Only show if child is currently checked in (authenticated staff only)
  - [x] Confirm dialog before check-out
  - [x] Use `checkOut.perform` tRPC endpoint
  - [x] Show success/error toast
  - [x] Update page state after check-out

#### Additional QR Page Actions ✅ COMPLETED
- [x] Undo button (if recently checked out)
  - [x] Only show if within undo window (5 minutes)
  - [x] Use `checkOut.undo` endpoint
- [ ] Edit child info button (admin only) - DEFERRED
  - [ ] Link to family edit page
- [ ] Reprint label button - DEFERRED
  - [ ] Regenerate and print QR code

### Check-Out Station Enhancements (from Day 5, Section 4.2) ✅ COMPLETED

#### Bulk Check-Out Features ✅ COMPLETED
- [x] "Pick Up All" quick button in family view
  - [x] Selects all checked-in children for a family
  - [x] Shows in header when 2+ children checked in
  - [x] Disabled when all children already selected
- [x] Show parent contact display in check-out view
  - [x] Parent names, phones, and emails displayed
  - [x] Already integrated in CheckedInChildrenView component

### Admin Panel Enhancements (from Day 6-7)

#### Session Management Modal (Section 5.2) ✅ COMPLETED
- [x] Create `src/components/admin/session-modal.tsx`
  - [x] Form fields:
    - [x] Session name (required)
    - [x] Event name (required)
    - [x] Start time (required, datetime picker)
    - [x] End time (required, datetime picker)
    - [x] Requires ticket (checkbox)
  - [x] Validation
    - [x] End time after start time
    - [x] Required fields
  - [x] Submit using `session.create` or `session.update`
  - [x] Success/error handling
- [x] Wire up "Create Session" button on sessions page
- [x] Wire up "Edit" button on session cards
- [x] Created `src/server/api/routers/event.ts` for event management
- [x] Integrated event creation with session creation
- [x] Added English and Swedish translations for all modal fields

#### Admin User Management Modal (Section 5.4) ✅ COMPLETED
- [x] Create `src/components/admin/create-admin-modal.tsx`
  - [x] Form fields:
    - [x] Username (required, unique validation, 3-50 chars)
    - [x] Password (required, min length 8, complexity requirements)
    - [x] Confirm password (must match)
    - [x] Name (required, max 100 chars)
  - [x] Validation
    - [x] Username format validation (alphanumeric, underscore, hyphen only)
    - [x] Password strength indicator (uppercase, lowercase, number)
    - [x] Password match validation
    - [x] Real-time password requirements display
  - [x] Submit using `adminUser.create` endpoint
  - [x] Success/error handling with toast
  - [x] Show/hide password toggle buttons
- [x] Wire up "Create User" button on users page

#### Family Detail & Edit Page (Section 5.6)
- [ ] Create `src/app/(authenticated)/admin/families/[id]/page.tsx`
  - [ ] Family overview section
    - [ ] Parents list with edit buttons
    - [ ] Children list with edit buttons
    - [ ] Last participation date display
  - [ ] Edit parent functionality
    - [ ] Inline editing or modal approach
    - [ ] Add new parent button
    - [ ] Remove parent button (with confirmation)
    - [ ] Use `parent.update`, `parent.create`, `parent.delete`
  - [ ] Edit children functionality
    - [ ] Inline editing or modal approach
    - [ ] Add new child button
    - [ ] Remove child button (with confirmation)
    - [ ] Regenerate QR code option
    - [ ] Use `child.update` endpoint
  - [ ] Check-in history section
    - [ ] Use `child.getCheckInHistory` for each child
    - [ ] Display in table/timeline format
    - [ ] Show session name, times, picked up by
  - [ ] Danger zone section
    - [ ] Delete family button (red, warning style)
    - [ ] Confirmation dialog with family name verification
    - [ ] Use `family.delete` endpoint

#### GDPR Data Review Page (Section 5.7)
- [ ] Create `src/app/(authenticated)/admin/gdpr/page.tsx`
  - [ ] Family listing by last participation
    - [ ] Use `family.getByLastParticipation` endpoint
    - [ ] Date filter dropdown (e.g., "2+ years", "1+ year", "6+ months")
    - [ ] Sort by oldest participation first
  - [ ] Family data table
    - [ ] Columns: Family name, Last participation, Children count, Checkbox
    - [ ] Pagination support
    - [ ] Select all checkbox in header
  - [ ] Bulk actions toolbar
    - [ ] Export selected as CSV button
    - [ ] Export selected as JSON button
    - [ ] Delete selected button (with confirmation)
    - [ ] Show count of selected families
  - [ ] Export functionality
    - [ ] Generate CSV file with all family data
    - [ ] Generate JSON file with all family data
    - [ ] Include parents, children, participation history
    - [ ] Trigger browser download
  - [ ] GDPR compliance notes
    - [ ] Documentation about data retention policies
    - [ ] Link to privacy policy
    - [ ] Audit log of deletions (future enhancement)

---

## Phase 4: Testing, Optimization & Deployment

**Duration:** 3-5 days
**Goal:** Comprehensive testing, performance optimization, and production deployment

### Day 1: End-to-End Testing

#### 4.1 E2E Test Setup
- [ ] Install Playwright for E2E testing
  - [ ] Configure Playwright with Next.js
  - [ ] Set up test database for E2E tests
  - [ ] Create test fixtures and helpers
  - [ ] Add CI/CD integration for E2E tests

#### 4.2 Core Workflow E2E Tests
- [ ] Check-in workflow test
  - [ ] Login as admin
  - [ ] Search for family
  - [ ] Select children
  - [ ] Complete check-in
  - [ ] Verify QR codes generated
  - [ ] Verify database records created
- [ ] Check-out workflow test
  - [ ] Search for checked-in family
  - [ ] Select children
  - [ ] Complete check-out
  - [ ] Verify undo functionality
  - [ ] Verify database records updated
- [ ] QR code workflow test
  - [ ] Access public QR page
  - [ ] Verify child information displayed
  - [ ] Test with invalid token (404)

#### 4.3 Admin Panel E2E Tests
- [ ] Session management workflow
  - [ ] Create new session
  - [ ] Activate session
  - [ ] Verify session in check-in flow
  - [ ] End session
  - [ ] Delete session
- [ ] User management workflow
  - [ ] Create new admin user
  - [ ] Login as new user
  - [ ] Deactivate user
  - [ ] Verify login fails
  - [ ] Reactivate user
- [ ] Family management workflow
  - [ ] Search for family
  - [ ] View family details
  - [ ] Edit family information
  - [ ] Delete family
  - [ ] Verify cascade deletion

#### 4.4 Edge Case Testing
- [ ] Multiple concurrent check-ins
  - [ ] Same child to different sessions (should fail)
  - [ ] Different children to same session (should succeed)
- [ ] Session state transitions
  - [ ] Activate multiple sessions
  - [ ] End all sessions
  - [ ] Try to check in with no active sessions
- [ ] QR code expiration/reuse
  - [ ] Check-out and check-in again (QR should work)
  - [ ] Invalid/tampered QR tokens
- [ ] User permissions
  - [ ] Inactive admin cannot login
  - [ ] Protected routes redirect to login
  - [ ] Session expiration handling

### Day 2: Performance Optimization

#### 4.5 Database Query Optimization
- [ ] Review Prisma query patterns
  - [ ] Check for N+1 query problems
  - [ ] Add necessary `include` statements
  - [ ] Optimize family search queries
  - [ ] Add database indexes where needed
- [ ] Implement query result caching
  - [ ] Configure tRPC cache settings
  - [ ] Add Redis for session caching (optional)
  - [ ] Review invalidation patterns

#### 4.6 Frontend Performance
- [ ] Bundle analysis
  - [ ] Run Next.js bundle analyzer
  - [ ] Identify large dependencies
  - [ ] Consider code splitting for heavy components
- [ ] Image optimization
  - [ ] Use Next.js Image component
  - [ ] Optimize QR code generation
  - [ ] Lazy load images where appropriate
- [ ] React performance audit
  - [ ] Profile with React DevTools
  - [ ] Add React.memo where beneficial
  - [ ] Optimize useEffect dependencies
  - [ ] Review re-render patterns

#### 4.7 Lighthouse & Accessibility Audit
- [ ] Run Lighthouse on all pages
  - [ ] Fix performance issues (target 90+)
  - [ ] Fix accessibility issues (target 100)
  - [ ] Fix best practices issues
  - [ ] Optimize SEO (add meta tags)
- [ ] Manual accessibility testing
  - [ ] Keyboard-only navigation test
  - [ ] Screen reader testing (NVDA/JAWS)
  - [ ] Color contrast validation
  - [ ] Touch target size validation

### Day 3: Security & Production Readiness

#### 4.8 Security Audit
- [ ] Review authentication flow
  - [ ] Session security (httpOnly cookies)
  - [ ] CSRF protection
  - [ ] Password hashing (bcrypt rounds)
  - [ ] Rate limiting on login
- [ ] Input validation audit
  - [ ] All tRPC inputs validated with Zod
  - [ ] SQL injection prevention (Prisma ORM)
  - [ ] XSS prevention (React escaping)
  - [ ] File upload validation (if added)
- [ ] Authorization checks
  - [ ] All tRPC procedures require auth
  - [ ] Public routes properly configured
  - [ ] No sensitive data in client bundles
- [ ] Environment variable security
  - [ ] No secrets in client-side code
  - [ ] Proper .env file handling
  - [ ] Secure key generation for JWT

#### 4.9 Production Configuration
- [ ] Environment setup
  - [ ] Production .env.production file
  - [ ] Database connection pooling
  - [ ] Configure CORS if needed
  - [ ] Set up error tracking (Sentry)
  - [ ] Configure logging (Winston/Pino)
- [ ] Build configuration
  - [ ] Optimize Next.js config
  - [ ] Configure CSP headers
  - [ ] Set up gzip/brotli compression
  - [ ] Configure CDN for static assets
- [ ] Docker setup (optional)
  - [ ] Create Dockerfile
  - [ ] Create docker-compose.yml
  - [ ] Multi-stage build optimization
  - [ ] Health check endpoints

#### 4.10 Monitoring & Observability
- [ ] Application monitoring
  - [ ] Set up error tracking (Sentry/Bugsnag)
  - [ ] Configure performance monitoring
  - [ ] Add custom metrics/events
  - [ ] Dashboard for key metrics
- [ ] Database monitoring
  - [ ] Query performance tracking
  - [ ] Slow query logging
  - [ ] Connection pool monitoring
- [ ] User analytics (privacy-friendly)
  - [ ] Page view tracking
  - [ ] Feature usage metrics
  - [ ] User flow analysis

### Day 4-5: Deployment & Documentation

#### 4.11 Database Migration Strategy
- [ ] Create production migration plan
  - [ ] Backup strategy
  - [ ] Migration rollback plan
  - [ ] Data seeding for initial admin user
  - [ ] Test migration on staging

#### 4.12 Deployment
- [ ] Choose hosting platform
  - [ ] Vercel (recommended for Next.js)
  - [ ] Railway
  - [ ] AWS/GCP/Azure
  - [ ] Self-hosted option
- [ ] Database hosting
  - [ ] PostgreSQL hosting (Railway/Supabase/AWS RDS)
  - [ ] Connection pooling setup
  - [ ] Backup configuration
  - [ ] Point-in-time recovery
- [ ] Deploy to staging
  - [ ] Run full E2E test suite
  - [ ] Manual QA testing
  - [ ] Performance testing
  - [ ] Fix any issues
- [ ] Deploy to production
  - [ ] Run migrations
  - [ ] Seed initial admin user
  - [ ] Verify all features work
  - [ ] Test from multiple devices

#### 4.13 User Documentation
- [ ] Create user guide
  - [ ] Check-in station workflow
  - [ ] Check-out station workflow
  - [ ] Admin panel usage
  - [ ] QR code system explanation
  - [ ] Troubleshooting section
- [ ] Create admin documentation
  - [ ] Session management guide
  - [ ] User management guide
  - [ ] Family management guide
  - [ ] GDPR compliance procedures
  - [ ] Backup and recovery procedures
- [ ] Create deployment documentation
  - [ ] Environment setup guide
  - [ ] Database setup guide
  - [ ] Deployment steps
  - [ ] Rollback procedures
  - [ ] Monitoring and maintenance

#### 4.14 Training Materials (Optional)
- [ ] Video tutorials
  - [ ] Check-in workflow demo
  - [ ] Check-out workflow demo
  - [ ] Admin panel tour
- [ ] Quick reference cards
  - [ ] Laminated cards for stations
  - [ ] Common troubleshooting steps
  - [ ] Contact information

---

## Phase 5: Post-Launch Enhancements (Optional)

These are potential future enhancements based on user feedback and additional requirements.

### Analytics & Reporting
- [ ] Dashboard analytics
  - [ ] Check-in/check-out trends over time
  - [ ] Popular session attendance
  - [ ] Family participation metrics
  - [ ] Volunteer hour tracking
- [ ] Export reports
  - [ ] CSV export of attendance by session
  - [ ] Family participation reports
  - [ ] Session summary reports

### Advanced Features
- [ ] Email notifications
  - [ ] Send check-in confirmation emails
  - [ ] Send QR codes via email
  - [ ] Session reminders
- [ ] SMS notifications (optional)
  - [ ] Check-in confirmations
  - [ ] Session reminders
  - [ ] Emergency alerts
- [ ] Multi-language support enhancements
  - [ ] Add more languages beyond English/Swedish
  - [ ] User preference storage
  - [ ] RTL language support
- [ ] Advanced session management
  - [ ] Recurring sessions
  - [ ] Session templates
  - [ ] Capacity limits per session
  - [ ] Waitlist functionality

### Mobile App (Future Consideration)
- [ ] React Native mobile app
  - [ ] QR code scanner built-in
  - [ ] Offline mode support
  - [ ] Push notifications
  - [ ] Faster check-in/check-out

### Integration Features
- [ ] Calendar integration
  - [ ] Export sessions to Google Calendar
  - [ ] iCal feed for sessions
- [ ] Badge printing integration
  - [ ] Direct printer integration
  - [ ] Custom badge templates
- [ ] Third-party authentication
  - [ ] OAuth integration (Google, Microsoft)
  - [ ] SSO support

---

## Technical Debt & Maintenance

### Code Quality Improvements
- [ ] Increase test coverage
  - [ ] Target 80%+ coverage
  - [ ] Add more unit tests
  - [ ] Add integration tests for edge cases
- [ ] Code documentation
  - [ ] JSDoc comments for complex functions
  - [ ] Component documentation
  - [ ] API endpoint documentation
- [ ] Refactoring opportunities
  - [ ] Extract common patterns into hooks
  - [ ] Consolidate duplicate code
  - [ ] Improve type safety

### Dependency Management
- [ ] Regular dependency updates
  - [ ] Security patches
  - [ ] Version upgrades
  - [ ] Breaking change migrations
- [ ] Monitor bundle size
  - [ ] Keep track of bundle growth
  - [ ] Remove unused dependencies
  - [ ] Optimize large dependencies

### Performance Monitoring
- [ ] Set up performance budgets
  - [ ] Bundle size limits
  - [ ] Lighthouse score thresholds
  - [ ] Response time targets
- [ ] Regular performance audits
  - [ ] Quarterly Lighthouse audits
  - [ ] Database query performance review
  - [ ] Frontend performance profiling

---

*Future Tasks Created: November 14, 2025*
*Compiled from: Phase 3 deferred items + IMPLEMENTATION_PLAN.md Phase 4*
