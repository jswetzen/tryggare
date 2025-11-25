# Current Tasks - UI/UX Redesign with Tailwind CSS

## Overview
Implementing a modern, responsive UI design based on the react-design.js mockups, adapted for SvelteKit with Tailwind CSS. The design features a responsive top navigation with hamburger menu, cleaner session indicators, and improved component structure.

## Design Principles
- **Mobile-first responsive design** - Hamburger menu on small screens
- **Minimal session indicator** - Less prominent, moved to top of page
- **Clean component hierarchy** - Reusable Svelte components with Tailwind
- **Professional color scheme** - Blue/slate palette from design mockups
- **Accessibility** - ARIA labels, keyboard navigation, proper contrast

## Phase 1: Setup & Infrastructure

### 1.1 Tailwind CSS Setup
- [ ] Install Tailwind CSS and dependencies in frontend
- [ ] Configure `tailwind.config.js` with design tokens
- [ ] Set up PostCSS configuration
- [ ] Add Tailwind directives to app.css
- [ ] Test build with Tailwind classes

### 1.2 Component Architecture Planning
- [ ] Document component hierarchy from react-design.js
- [ ] Map React components to Svelte equivalents
- [ ] Plan prop interfaces and state management
- [ ] Identify reusable utility components

## Phase 2: Core Reusable Components

### 2.1 Layout Components
- [ ] `SessionIndicator.svelte` - Top session info (minimal, less prominent)
  - Event name and session name
  - Time display
  - Change session button (subtle)
- [ ] `PageHeader.svelte` - Page title with bottom border
- [ ] `SearchBox.svelte` - Blue-bordered search with label
- [ ] `TableHeader.svelte` - Section header with count

### 2.2 Interactive Components
- [ ] `TicketBadge.svelte` - Color-coded ticket status
  - Event Pass (green)
  - Session Ticket (blue)
  - No Ticket (red)
- [ ] `IconButton.svelte` - Action buttons with tooltips
  - Check-in (green)
  - Check-out (red)
  - Family check-in (blue)
  - Family check-out (orange)
  - Disabled states (gray)

### 2.3 Navigation Components
- [ ] `TopNav.svelte` - Responsive navigation
  - Desktop: Full horizontal menu with view switcher
  - Mobile: Hamburger menu
  - Session indicator integration at top
  - User info and logout
  - Language switcher

## Phase 3: Page Implementations

### 3.1 Check-In Page Redesign
- [ ] Update `frontend/src/routes/checkin/+page.svelte`
- [ ] Add SessionIndicator at top (minimal style)
- [ ] Implement PageHeader component
- [ ] Use SearchBox component
- [ ] Family/child table with new styling:
  - Alternating row colors (slate-50/slate-100)
  - Bold family names
  - Indented children rows
  - TicketBadge for each child
  - IconButton for actions
- [ ] "Add New Family" call-to-action box
- [ ] Mobile responsive layout

### 3.2 Check-Out Page Redesign
- [ ] Update `frontend/src/routes/checkout/+page.svelte`
- [ ] SessionIndicator at top
- [ ] PageHeader component
- [ ] SearchBox component
- [ ] Checked-in children table:
  - Family grouping
  - Check-in time display
  - IconButton for checkout
  - "Picked up by" dropdown per family
- [ ] Mobile responsive layout

### 3.3 Layout & Navigation Update
- [ ] Update `frontend/src/routes/+layout.svelte`
- [ ] Replace current nav with TopNav component
- [ ] Implement responsive hamburger menu
- [ ] Move view switcher into top menu
- [ ] Make session info less prominent
- [ ] Test on various screen sizes

## Phase 4: Polish & Refinement

### 4.1 Responsive Design
- [ ] Test all pages on mobile (< 640px)
- [ ] Test tablet breakpoint (640-1024px)
- [ ] Test desktop (> 1024px)
- [ ] Ensure touch targets are 44px minimum
- [ ] Verify hamburger menu works smoothly

### 4.2 Visual Polish
- [ ] Verify color contrast meets WCAG AA
- [ ] Add hover states to all interactive elements
- [ ] Smooth transitions for menu and modals
- [ ] Loading states with proper styling
- [ ] Error messages with Tailwind styling

### 4.3 Accessibility
- [ ] Keyboard navigation for all actions
- [ ] ARIA labels for icon buttons
- [ ] Focus indicators visible
- [ ] Screen reader testing
- [ ] Mobile screen reader support

## Phase 5: Testing & Documentation

### 5.1 Cross-browser Testing
- [ ] Chrome/Chromium
- [ ] Firefox
- [ ] Safari (if available)
- [ ] Mobile browsers (iOS Safari, Chrome Android)

### 5.2 User Acceptance
- [ ] Test with real check-in workflow
- [ ] Test with real check-out workflow
- [ ] Verify QR page still works with new layout
- [ ] Get feedback on mobile usability

### 5.3 Documentation
- [ ] Update component documentation
- [ ] Document Tailwind configuration
- [ ] Add screenshots to README
- [ ] Document responsive breakpoints

## Design Reference

### Color Palette (from react-design.js)
- Primary Blue: `blue-600`, `blue-700`, `blue-900`
- Success Green: `green-600`, `green-700`
- Warning Orange: `orange-600`, `orange-700`
- Error Red: `red-600`, `red-700`
- Neutral Slate: `slate-50`, `slate-100`, `slate-200`, `slate-300`, `slate-500`, `slate-600`, `slate-700`

### Typography
- Page headers: `text-2xl font-bold text-blue-900`
- Section headers: `text-lg font-semibold text-slate-700`
- Labels: `font-semibold text-blue-900 text-sm`
- Body text: `text-slate-700 text-sm`

### Spacing & Layout
- Max content width: `max-w-3xl mx-auto` (check-in/out pages)
- Card padding: `p-5`
- Border radius: `rounded-md` or `rounded-lg`
- Shadows: `shadow-lg` for main containers

## Success Criteria
- [ ] All pages use Tailwind CSS (no custom CSS)
- [ ] Responsive design works on all screen sizes
- [ ] Hamburger menu functions properly on mobile
- [ ] Session indicator is minimal and at the top
- [ ] View switcher is part of top navigation
- [ ] All components reusable and well-documented
- [ ] No regression in functionality
- [ ] Improved visual appeal and usability

## Notes
- Previous i18n work archived to `CURRENT_TASKS_I18N_20251125.md`
- Can return to i18n implementation after UI redesign
- Design based on react-design.js mockups
- Adapted for SvelteKit instead of React
- Maintaining current backend Django implementation
