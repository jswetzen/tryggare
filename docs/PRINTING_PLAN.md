● Detailed Implementation Plan: Print Queue Improvements

  Overview

  Refactor print queue to support individual label printing with Brother QL-29mm thermal printer, with a recently-printed history for easy reprints.

  ---
  Backend Changes

  1. New HTML Print Template (backend/checkins/templates/print_label.html)

  Purpose: Single-label print page optimized for 29mm Brother QL-series

  Features:
  - CSS @page rules for 29mm (1.1") width continuous roll
  - Single label layout: child name, session, allergies (red/bold if present), QR code
  - Print-optimized styling (no margins, proper sizing)
  - QR code sized appropriately for small label

  Template context:
  - checkin: CheckInRecord object
  - qr_url: Full URL for QR code

  2. API Endpoint Changes (backend/checkins/views.py)

  a) New: GET /api/print-queue/{id}/print-page/

  - Returns HTML response (not JSON)
  - Renders print_label.html template
  - Single CheckInRecord by ID
  - Returns 404 if not found

  b) New: POST /api/print-queue/{id}/mark-printed/

  - Marks single check-in as printed
  - Sets label_printed=True, label_printed_at=now(), label_printed_by=request.user
  - Creates audit log entry
  - Returns updated record serialized
  - Returns 404 if not found or already checked out

  c) New: GET /api/print-queue/recently-printed/

  - Returns last 50 check-ins where label_printed=True
  - Ordered by check_in_time DESC
  - Uses same PrintQueueSerializer
  - Filtered to only checked-in (not checked out) records

  d) Modify: generate_pdf endpoint

  - Keep existing for backup/future use
  - No changes needed now

  3. URL Routing (backend/checkins/urls.py)

  Add routes:
  # In PrintQueueViewSet
  @action(detail=True, methods=['get'])
  def print_page(self, request, pk=None):
      ...

  @action(detail=True, methods=['post'])
  def mark_printed(self, request, pk=None):
      ...

  @action(detail=False, methods=['get'])
  def recently_printed(self, request):
      ...

  4. Django Tests (backend/test_print_queue.py - extend existing)

  Test: test_print_page_html_generation

  - Request /api/print-queue/{id}/print-page/
  - Assert 200 response
  - Assert content-type is text/html
  - Assert template contains child name, session name
  - Assert QR code URL present

  Test: test_mark_single_printed

  - Create unprintable check-in
  - POST to /api/print-queue/{id}/mark-printed/
  - Assert label_printed=True in response
  - Assert label_printed_by is current user
  - Assert label_printed_at is set
  - Assert audit log created

  Test: test_recently_printed_list

  - Create 60 check-ins, mark 60 as printed
  - GET /api/print-queue/recently-printed/
  - Assert returns exactly 50 items
  - Assert ordered by check_in_time DESC
  - Assert all have label_printed=True

  Test: test_recently_printed_excludes_checked_out

  - Create 10 check-ins, mark all printed
  - Check out 5 of them
  - GET /api/print-queue/recently-printed/
  - Assert returns only 5 (still checked in)

  Test: test_print_page_not_found

  - Request print page with invalid UUID
  - Assert 404 response

  Test: test_mark_printed_idempotent

  - Mark same check-in as printed twice
  - Assert both requests succeed (no error on re-marking)

  ---
  Frontend Changes

  1. New Print Label Page (frontend/src/routes/print-labels/[id]/+page.svelte)

  Purpose: Standalone print page for single label

  Features:
  - Fetches check-in data from API on mount
  - Calls backend /api/print-queue/{id}/mark-printed/ immediately on mount
  - Renders label layout matching backend template (or uses iframe to backend HTML page)
  - Auto-triggers window.print() after 500ms delay (let page render first)

  Alternative simpler approach:
  - Just redirect to backend /api/print-queue/{id}/print-page/ endpoint
  - Backend handles everything (HTML + CSS)
  - Frontend just opens URL in new window and calls mark-printed API

  2. Update Print Queue Page (frontend/src/routes/print-queue/+page.svelte)

  Changes to main queue section:

  - Remove: Bulk selection checkboxes
  - Remove: "Print Selected", "Print All", "Mark as Printed", "Select All", "Clear Selection" buttons
  - Add: "Print" button in actions column for each row
  - Keep: "View QR" button
  - Simplify: Action bar to just have "Refresh" button

  Add recently printed section:

  - Collapsible <details> element below main queue
  - Header: "Recently Printed (Last 50)" with count badge
  - Collapsed by default
  - Simplified table columns:
    - Child Name (bold) with parent names (smaller, below)
    - Actions: View QR | Print buttons
  - Fetch from /api/print-queue/recently-printed/ when expanded
  - "Refresh" button updates both sections

  Print button functionality:

  async function printLabel(checkinId: string) {
    // Open print page in new window
    const printUrl = `/api/print-queue/${checkinId}/print-page/`;
    window.open(printUrl, '_blank');

    // Mark as printed immediately
    try {
      await printQueueApi.markSinglePrinted(checkinId);
      await loadQueue(); // Refresh to remove from main queue
    } catch (e) {
      console.error('Failed to mark as printed:', e);
      // Don't block - user can still print
    }
  }

  3. API Service Updates (frontend/src/lib/api/services.ts)

  Add methods to printQueueApi:
  async markSinglePrinted(checkinId: string): Promise<PrintQueueItem> {
    const response = await fetch(`${API_BASE}/print-queue/${checkinId}/mark-printed/`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'X-CSRFToken': getCsrfToken() }
    });
    return response.json();
  }

  async getRecentlyPrinted(): Promise<PrintQueueItem[]> {
    const response = await fetch(`${API_BASE}/print-queue/recently-printed/`, {
      credentials: 'include'
    });
    return response.json();
  }

  getPrintPageUrl(checkinId: string): string {
    return `${API_BASE}/print-queue/${checkinId}/print-page/`;
  }

  4. i18n Updates (frontend/src/lib/i18n/locales/en.json)

  Add translations:
  {
    "printQueue": {
      "print": "Print",
      "recentlyPrinted": "Recently Printed (Last 50)",
      "recentlyPrintedCount": "Recently Printed ({count})",
      "printError": "Failed to print label",
      "noRecentlyPrinted": "No recently printed labels"
    }
  }

  ---
  Testing Strategy

  Backend Unit Tests (Django)

  File: backend/test_print_queue.py

  1. test_print_page_html_generation - HTML template renders correctly
  2. test_mark_single_printed - Single check-in marked printed with audit log
  3. test_recently_printed_list - Returns last 50, ordered correctly
  4. test_recently_printed_excludes_checked_out - Only active check-ins
  5. test_print_page_not_found - 404 for invalid ID
  6. test_mark_printed_idempotent - Can mark same item twice without error

  Frontend E2E Tests (Selenium)

  File: backend/test_print_queue_e2e.py

  Test: test_individual_print_button

  1. Navigate to print queue page
  2. Check in a child (appears in queue)
  3. Click "Print" button on row
  4. Assert new window opens with print page URL
  5. Wait 2 seconds (for mark-printed API call)
  6. Refresh queue page
  7. Assert child no longer in main queue
  8. Expand "Recently Printed" section
  9. Assert child appears in recently printed list

  Test: test_recently_printed_section

  1. Check in 5 children
  2. Mark all as printed via API
  3. Navigate to print queue page
  4. Assert recently printed section is collapsed
  5. Click to expand section
  6. Assert shows all 5 children
  7. Assert simplified layout (no session/time/allergies columns)
  8. Assert each has "Print" and "View QR" buttons

  Test: test_reprint_from_history

  1. Check in child, mark as printed
  2. Navigate to print queue page
  3. Expand recently printed section
  4. Click "Print" button on child in history
  5. Assert new window opens with print page
  6. Close new window
  7. Assert child still in recently printed list (not moved)

  Test: test_bulk_actions_removed

  1. Navigate to print queue page
  2. Check in multiple children
  3. Assert no checkboxes in table
  4. Assert no "Select All" button
  5. Assert no "Print Selected" button
  6. Assert no "Print All" button
  7. Assert no "Mark as Printed" button

  Test: test_print_page_content

  1. Check in child with allergies
  2. Navigate directly to /api/print-queue/{id}/print-page/
  3. Assert page contains child name
  4. Assert page contains session name
  5. Assert page contains allergy info (red/bold)
  6. Assert page contains QR code image
  7. Assert page has print-optimized CSS (@page rules)

  ---
  Implementation Order

  1. Backend API endpoints (views.py, urls.py)
  2. HTML print template (print_label.html with Brother QL-29mm CSS)
  3. Backend unit tests (Django tests)
  4. Frontend API service updates (services.ts)
  5. Frontend print queue page refactor (+page.svelte)
  6. i18n translations (en.json, de.json if needed)
  7. Frontend E2E tests (Selenium)
  8. Manual testing with actual Brother QL printer
  9. Update CURRENT_TASKS.md

  ---
  CSS Specifications for Brother QL-29mm

  @page {
    size: 29mm 90mm; /* Width x Length (length is content-dependent) */
    margin: 0;
  }

  body {
    margin: 0;
    padding: 2mm;
    font-family: Arial, sans-serif;
    width: 29mm;
  }

  .label {
    width: 25mm; /* Accounting for padding */
    text-align: center;
  }

  .child-name {
    font-size: 8pt;
    font-weight: bold;
    margin-bottom: 1mm;
  }

  .session-name {
    font-size: 6pt;
    margin-bottom: 1mm;
  }

  .allergies {
    font-size: 6pt;
    font-weight: bold;
    color: #cc0000;
    margin-bottom: 2mm;
  }

  .qr-code {
    width: 20mm;
    height: 20mm;
    margin: 0 auto;
  }

 