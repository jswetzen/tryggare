# Printing Implementation Plan - Manual Label Queue

## Overview
This plan details the implementation of a manual label printing queue as a first step toward full automatic printer integration. The goal is to provide a dedicated page where staff can see all checked-in children who need labels printed, and manually trigger print operations.

**Status**: Planning Phase
**Priority**: Medium (improves workflow before automatic printing)
**Estimated Effort**: 1-2 days

---

## Current State Analysis

### Existing Data Model
Based on the Django models in the system:

**CheckInRecord** (`backend/checkins/models.py`):
- `id` (UUID)
- `child` (ForeignKey → Child)
- `session` (ForeignKey → Session)
- `check_in_time` (DateTime)
- `check_out_time` (DateTime, nullable)
- `check_in_staff` (ForeignKey → AdminUser)
- `check_out_staff` (ForeignKey → AdminUser, nullable)
- `picked_up_by` (CharField, nullable)

**Child** (`backend/families/models.py`):
- `id` (UUID)
- `first_name`
- `last_name`
- `birthdate`
- `allergies`
- `notes`
- `qr_token` (unique, nullable - generated on first check-in)
- `last_participation_date`
- `family` (ForeignKey → Family)

### Current Printing Behavior
- **Check-in flow**: QR token is generated on first check-in
- **Current approach**: QR codes are displayed on screen (stub implementation)
- **Reprint capability**: Available from QR info page (shows QR in modal)
- **No tracking**: System doesn't track which labels have been printed

---

## Proposed Solution: Manual Printing Queue

### Core Concept
Add a new "Label Printing" page that shows:
1. All children currently checked in
2. Filter to show only those who need labels printed
3. Batch selection for printing multiple labels
4. Print button that triggers browser print dialog or generates printable PDF

### Key Features
1. **Print Status Tracking**: Track whether a label has been printed for each check-in
2. **Print Queue View**: Dedicated page showing unprintable check-ins
3. **Batch Printing**: Select multiple children and print all at once
4. **Manual Print Trigger**: Print button for individual or batch operations
5. **Print History**: Track when labels were printed and by whom

---

## Implementation Details

### Phase 1: Data Model Changes (2-3 hours)

#### 1.1 Update CheckInRecord Model
Add print tracking fields to `backend/checkins/models.py`:

```python
class CheckInRecord(models.Model):
    # ... existing fields ...

    # Print tracking fields (NEW)
    label_printed = models.BooleanField(
        default=False,
        verbose_name=_("Label Printed")
    )
    label_printed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Label Printed At")
    )
    label_printed_by = models.ForeignKey(
        "accounts.AdminUser",
        related_name="labels_printed",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("Label Printed By"),
    )

    class Meta:
        # ... existing meta ...
        indexes = [
            # ... existing indexes ...
            models.Index(fields=["label_printed"]),  # NEW: for filtering queue
        ]
```

**Migration**:
```bash
cd /workspace/check-ins/backend
uv run python manage.py makemigrations checkins
uv run python manage.py migrate
```

#### 1.2 Alternative Approach: Separate PrintLog Model
If we want more detailed history, create a separate model:

```python
class PrintLog(models.Model):
    """Track each time a label is printed"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    checkin_record = models.ForeignKey(
        CheckInRecord,
        related_name="print_logs",
        on_delete=models.CASCADE,
        verbose_name=_("Check-In Record")
    )
    printed_at = models.DateTimeField(auto_now_add=True)
    printed_by = models.ForeignKey(
        "accounts.AdminUser",
        related_name="print_actions",
        on_delete=models.PROTECT,
    )
    print_method = models.CharField(
        max_length=32,
        choices=[
            ("MANUAL", "Manual Print"),
            ("AUTO", "Automatic Print"),
            ("REPRINT", "Reprint"),
        ],
        default="MANUAL"
    )

    class Meta:
        db_table = "print_logs"
        indexes = [
            models.Index(fields=["checkin_record"]),
            models.Index(fields=["printed_at"]),
        ]
```

**Recommendation**: Start with approach 1.1 (boolean flag) for simplicity. Can add PrintLog later if detailed history is needed.

---

### Phase 2: Backend API Endpoints (2-3 hours)

#### 2.1 Print Queue Endpoint
**GET `/api/print-queue/`**

Returns all check-ins that need labels printed:

```python
# backend/checkins/views.py or new backend/printing/views.py

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

class PrintQueueViewSet(viewsets.ReadOnlyModelViewSet):
    """API for managing label print queue"""

    def list(self, request):
        """Get all unprintable check-ins"""
        # Query: checked in, not printed, not checked out
        unprintable = CheckInRecord.objects.filter(
            label_printed=False,
            check_out_time__isnull=True,  # Still checked in
        ).select_related(
            'child',
            'child__family',
            'session',
            'check_in_staff'
        ).prefetch_related(
            'child__family__parents'
        ).order_by('-check_in_time')

        serializer = PrintQueueSerializer(unprintable, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def mark_printed(self, request):
        """Mark one or more check-ins as printed"""
        checkin_ids = request.data.get('checkin_ids', [])

        if not checkin_ids:
            return Response(
                {'error': 'No check-in IDs provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update records
        updated = CheckInRecord.objects.filter(
            id__in=checkin_ids,
            check_out_time__isnull=True  # Only if still checked in
        ).update(
            label_printed=True,
            label_printed_at=timezone.now(),
            label_printed_by=request.user
        )

        return Response({
            'message': f'{updated} labels marked as printed',
            'count': updated
        })

    @action(detail=False, methods=['get'])
    def generate_pdf(self, request):
        """Generate printable PDF of labels"""
        checkin_ids = request.query_params.get('ids', '').split(',')

        checkins = CheckInRecord.objects.filter(
            id__in=checkin_ids
        ).select_related('child', 'session')

        # Generate PDF using reportlab or weasyprint
        pdf = generate_label_pdf(checkins)

        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="labels.pdf"'
        return response
```

#### 2.2 Serializer for Print Queue
```python
# backend/checkins/serializers.py

class PrintQueueSerializer(serializers.ModelSerializer):
    child_name = serializers.CharField(source='child.first_name', read_only=True)
    child_last_name = serializers.CharField(source='child.last_name', read_only=True)
    qr_token = serializers.CharField(source='child.qr_token', read_only=True)
    session_name = serializers.CharField(source='session.name', read_only=True)
    check_in_time = serializers.DateTimeField(read_only=True)
    parents = ParentSerializer(source='child.family.parents', many=True, read_only=True)

    class Meta:
        model = CheckInRecord
        fields = [
            'id',
            'child_name',
            'child_last_name',
            'qr_token',
            'session_name',
            'check_in_time',
            'parents',
            'label_printed',
        ]
```

#### 2.3 URL Configuration
```python
# backend/config/urls.py

from printing.views import PrintQueueViewSet

router.register(r'print-queue', PrintQueueViewSet, basename='print-queue')
```

---

### Phase 3: Frontend Print Queue Page (3-4 hours)

#### 3.1 Create Print Queue Service
```typescript
// frontend/src/lib/api/services.ts

export const printQueueApi = {
    async getQueue(): Promise<PrintQueueItem[]> {
        const response = await fetch('/api/print-queue/', {
            credentials: 'include',
        });
        if (!response.ok) throw new Error('Failed to fetch print queue');
        return response.json();
    },

    async markPrinted(checkinIds: string[]): Promise<void> {
        const response = await fetch('/api/print-queue/mark_printed/', {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ checkin_ids: checkinIds }),
        });
        if (!response.ok) throw new Error('Failed to mark as printed');
    },

    getPrintUrl(checkinIds: string[]): string {
        return `/api/print-queue/generate_pdf/?ids=${checkinIds.join(',')}`;
    },
};
```

#### 3.2 Create Print Queue Page Component
```svelte
<!-- frontend/src/routes/print-queue/+page.svelte -->

<script lang="ts">
    import { onMount } from 'svelte';
    import { printQueueApi } from '$lib/api/services';
    import type { PrintQueueItem } from '$lib/api/types';
    import { t } from '$lib/i18n/i18n';

    let queueItems: PrintQueueItem[] = [];
    let selectedIds = new Set<string>();
    let loading = false;
    let error = '';

    onMount(async () => {
        await loadQueue();
    });

    async function loadQueue() {
        loading = true;
        error = '';
        try {
            queueItems = await printQueueApi.getQueue();
        } catch (e) {
            error = $t('printQueue.loadError');
        } finally {
            loading = false;
        }
    }

    function toggleSelection(id: string) {
        if (selectedIds.has(id)) {
            selectedIds.delete(id);
        } else {
            selectedIds.add(id);
        }
        selectedIds = selectedIds; // Trigger reactivity
    }

    function selectAll() {
        selectedIds = new Set(queueItems.map(item => item.id));
    }

    function clearSelection() {
        selectedIds = new Set();
    }

    async function printSelected() {
        if (selectedIds.size === 0) {
            error = $t('printQueue.noSelection');
            return;
        }

        // Open print dialog or download PDF
        const url = printQueueApi.getPrintUrl(Array.from(selectedIds));
        window.open(url, '_blank');

        // Mark as printed after short delay (assuming user will print)
        setTimeout(async () => {
            try {
                await printQueueApi.markPrinted(Array.from(selectedIds));
                await loadQueue();
                clearSelection();
            } catch (e) {
                error = $t('printQueue.markError');
            }
        }, 2000);
    }
</script>

<div class="container mx-auto p-4">
    <h1 class="text-2xl font-bold mb-4">{$t('printQueue.title')}</h1>

    {#if loading}
        <p>{$t('common.loading')}</p>
    {:else if error}
        <div class="alert alert-error">{error}</div>
    {:else if queueItems.length === 0}
        <p class="text-gray-500">{$t('printQueue.empty')}</p>
    {:else}
        <!-- Action Bar -->
        <div class="flex gap-2 mb-4">
            <button
                class="btn btn-primary"
                on:click={printSelected}
                disabled={selectedIds.size === 0}
            >
                {$t('printQueue.printSelected')} ({selectedIds.size})
            </button>
            <button class="btn btn-secondary" on:click={selectAll}>
                {$t('printQueue.selectAll')}
            </button>
            <button class="btn btn-ghost" on:click={clearSelection}>
                {$t('printQueue.clearSelection')}
            </button>
            <button class="btn btn-ghost" on:click={loadQueue}>
                {$t('common.refresh')}
            </button>
        </div>

        <!-- Queue Table -->
        <div class="overflow-x-auto">
            <table class="table w-full">
                <thead>
                    <tr>
                        <th><input type="checkbox" on:change={selectAll} /></th>
                        <th>{$t('printQueue.childName')}</th>
                        <th>{$t('printQueue.session')}</th>
                        <th>{$t('printQueue.checkInTime')}</th>
                        <th>{$t('printQueue.actions')}</th>
                    </tr>
                </thead>
                <tbody>
                    {#each queueItems as item}
                        <tr>
                            <td>
                                <input
                                    type="checkbox"
                                    checked={selectedIds.has(item.id)}
                                    on:change={() => toggleSelection(item.id)}
                                />
                            </td>
                            <td>{item.child_name} {item.child_last_name}</td>
                            <td>{item.session_name}</td>
                            <td>{new Date(item.check_in_time).toLocaleTimeString()}</td>
                            <td>
                                <a
                                    href="/qr/{item.qr_token}"
                                    target="_blank"
                                    class="link"
                                >
                                    {$t('printQueue.viewQR')}
                                </a>
                            </td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>
    {/if}
</div>
```

#### 3.3 Add Navigation Link
Update top navigation to include print queue link:

```svelte
<!-- frontend/src/lib/components/TopNav.svelte -->

<!-- Add to navigation menu -->
<a href="/print-queue" class="nav-link">
    {$t('nav.printQueue')}
</a>
```

#### 3.4 Add i18n Translations
```json
// frontend/src/lib/i18n/locales/en.json
{
    "nav": {
        "printQueue": "Print Queue"
    },
    "printQueue": {
        "title": "Label Printing Queue",
        "empty": "No labels need printing",
        "childName": "Child Name",
        "session": "Session",
        "checkInTime": "Check-In Time",
        "actions": "Actions",
        "printSelected": "Print Selected",
        "selectAll": "Select All",
        "clearSelection": "Clear Selection",
        "viewQR": "View QR",
        "loadError": "Failed to load print queue",
        "markError": "Failed to mark as printed",
        "noSelection": "Please select at least one child"
    }
}
```

```json
// frontend/src/lib/i18n/locales/sv.json
{
    "nav": {
        "printQueue": "Utskriftskö"
    },
    "printQueue": {
        "title": "Etikettutskriftskö",
        "empty": "Inga etiketter behöver skrivas ut",
        "childName": "Barnnamn",
        "session": "Session",
        "checkInTime": "Incheckningstid",
        "actions": "Åtgärder",
        "printSelected": "Skriv ut valda",
        "selectAll": "Välj alla",
        "clearSelection": "Rensa val",
        "viewQR": "Visa QR",
        "loadError": "Kunde inte läsa in utskriftskön",
        "markError": "Kunde inte markera som utskrivna",
        "noSelection": "Vänligen välj minst ett barn"
    }
}
```

---

### Phase 4: PDF Generation (2-3 hours)

#### 4.1 Install PDF Library
```bash
cd /workspace/check-ins/backend
uv add reportlab  # or weasyprint
```

#### 4.2 Create Label PDF Generator
```python
# backend/printing/utils.py

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
from io import BytesIO

def generate_label_pdf(checkin_records):
    """Generate a PDF with labels for printing"""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Label dimensions (adjust based on actual label size)
    label_width = 2.5 * inch
    label_height = 1.5 * inch
    margin = 0.5 * inch

    labels_per_row = 3
    labels_per_col = 6

    x_positions = [margin + i * (label_width + 0.25*inch) for i in range(labels_per_row)]
    y_positions = [height - margin - (i+1) * (label_height + 0.25*inch) for i in range(labels_per_col)]

    label_count = 0
    page_count = 0

    for record in checkin_records:
        # Calculate position
        row = label_count % labels_per_col
        col = (label_count // labels_per_col) % labels_per_row

        if label_count > 0 and label_count % (labels_per_row * labels_per_col) == 0:
            c.showPage()
            page_count += 1

        x = x_positions[col]
        y = y_positions[row]

        # Draw label border (optional)
        c.rect(x, y, label_width, label_height)

        # Draw child name
        c.setFont("Helvetica-Bold", 14)
        c.drawString(x + 0.1*inch, y + label_height - 0.3*inch,
                    f"{record.child.first_name} {record.child.last_name}")

        # Draw session name
        c.setFont("Helvetica", 10)
        c.drawString(x + 0.1*inch, y + label_height - 0.5*inch,
                    f"{record.session.name}")

        # Generate QR code
        qr_url = f"https://your-domain.com/qr/{record.child.qr_token}"
        qr = QrCodeWidget(qr_url)
        qr.barWidth = 1.2 * inch
        qr.barHeight = 1.2 * inch

        d = Drawing()
        d.add(qr)
        renderPDF.draw(d, c, x + label_width - 1.3*inch, y + 0.1*inch)

        label_count += 1

    c.save()
    buffer.seek(0)
    return buffer.getvalue()
```

---

### Phase 5: Integration & Testing (2-3 hours)

#### 5.1 Update Check-In Flow
Modify check-in API to NOT auto-mark as printed:

```python
# backend/checkins/views.py

def perform_checkin(request):
    # ... existing check-in logic ...

    # Do NOT set label_printed=True automatically
    # Let staff manually trigger printing from queue

    return Response({
        'message': 'Check-in successful',
        'checkins': checkin_ids,
        'needs_printing': True  # Flag for UI
    })
```

#### 5.2 Create Tests
```python
# backend/test_printing.py

from django.test import TestCase
from checkins.models import CheckInRecord
from printing.views import PrintQueueViewSet

class PrintQueueTests(TestCase):
    def test_unprintable_checkins_in_queue(self):
        """Test that unprintable check-ins appear in queue"""
        # Create check-in without printing
        checkin = create_test_checkin(label_printed=False)

        queue = CheckInRecord.objects.filter(label_printed=False)
        self.assertEqual(queue.count(), 1)
        self.assertEqual(queue.first(), checkin)

    def test_mark_as_printed(self):
        """Test marking check-ins as printed"""
        checkin = create_test_checkin(label_printed=False)

        # Mark as printed
        checkin.label_printed = True
        checkin.save()

        queue = CheckInRecord.objects.filter(label_printed=False)
        self.assertEqual(queue.count(), 0)

    def test_checked_out_not_in_queue(self):
        """Test that checked-out children don't appear in queue"""
        checkin = create_test_checkin(label_printed=False)
        checkin.check_out_time = timezone.now()
        checkin.save()

        queue = CheckInRecord.objects.filter(
            label_printed=False,
            check_out_time__isnull=True
        )
        self.assertEqual(queue.count(), 0)
```

#### 5.3 Manual Testing Checklist
- [ ] Check-in child → appears in print queue
- [ ] Multiple check-ins → all appear in queue
- [ ] Select all → all items selected
- [ ] Print selected → PDF downloads/opens
- [ ] After printing → items removed from queue
- [ ] Check-out child → removed from queue (even if not printed)
- [ ] Refresh queue → updates correctly
- [ ] Swedish translations work
- [ ] Mobile responsive design

---

## Alternative Approaches

### Option A: Simple Print View (Simpler)
Instead of a queue with selection:
- Simple list of unprintable check-ins
- "Print All" button generates one PDF
- No manual selection needed
- Less flexible but faster to implement

### Option B: Browser Print Dialog (No PDF)
- Use browser's native print dialog
- Create print-optimized HTML page
- Use CSS `@media print` for label layout
- No PDF generation needed
- Simpler but less control over output

### Option C: Auto-Print on Check-In (Future)
- Automatically open print dialog on check-in
- Requires browser print API integration
- Can be annoying for staff if printer not ready
- Better suited for automatic printer integration

---

## Future Enhancements

### After Manual Queue is Working:
1. **Automatic Printer Integration**
   - Select Brother printer model
   - Network printer communication
   - Automatic print on check-in
   - Print job queue management

2. **Print Template Customization**
   - Configurable label layouts
   - Custom logo/branding
   - Variable label sizes
   - Color vs black-and-white

3. **Print History & Reprints**
   - View all printed labels
   - Reprint from history
   - Print statistics
   - Identify missing prints

4. **Batch Operations**
   - Print all for a session
   - Print all for a family
   - Scheduled printing
   - Print preview

---

## Timeline & Effort Estimate

| Phase | Task | Estimated Time |
|-------|------|----------------|
| 1 | Data model changes | 2-3 hours |
| 2 | Backend API | 2-3 hours |
| 3 | Frontend UI | 3-4 hours |
| 4 | PDF generation | 2-3 hours |
| 5 | Testing & integration | 2-3 hours |
| **Total** | | **11-16 hours** (~1-2 days) |

---

## Success Criteria

**MVP Complete When:**
- [ ] Print queue page accessible from navigation
- [ ] Queue shows all unprintable check-ins
- [ ] Staff can select multiple children
- [ ] Print button generates PDF with labels
- [ ] Labels include: child name, session, QR code
- [ ] After printing, labels marked as printed
- [ ] Queue updates correctly after printing
- [ ] Checked-out children removed from queue
- [ ] Swedish translations complete
- [ ] Tests pass

**Quality Gates:**
- [ ] PDF generates correctly on first try
- [ ] QR codes scannable from printed labels
- [ ] Label layout fits standard Brother label sheets
- [ ] Page loads quickly (<2s with 50+ items)
- [ ] No duplicate entries in queue
- [ ] Print history tracked correctly

---

## Dependencies & Prerequisites

**Required:**
- Django CheckInRecord model already exists ✅
- Child model with qr_token already exists ✅
- Admin authentication working ✅
- Frontend routing and navigation ✅

**To Install:**
- `reportlab` or `weasyprint` (Python PDF library)

**To Configure:**
- Label size and layout (need actual printer specs)
- QR code domain/URL (production domain)

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| PDF layout doesn't match printer | High | Test with actual printer early, make layout configurable |
| QR codes not scannable | High | Test QR size and resolution, increase if needed |
| Print queue grows too large | Medium | Add pagination, auto-archive old entries |
| Staff forget to print | Medium | Add visual indicator on check-in page |
| Concurrent printing conflicts | Low | Use database transactions, add locking |

---

## Notes & Considerations

1. **Label Size**: Need to determine actual Brother label dimensions before finalizing PDF layout
2. **QR Code URL**: Must use production domain, not localhost
3. **Print Confirmation**: Consider adding "Are you sure?" dialog before marking as printed
4. **Reprint Flow**: May want to add ability to reprint from queue (mark as unprintable again)
5. **Session Filter**: May want to filter queue by session for busy events
6. **Sound/Visual Alert**: Could add notification when new items added to queue

---

**Recommendation**: Start with Phase 1-3 (data model + API + basic UI) before investing in PDF generation. This allows testing the workflow with simple QR display before adding print complexity.
