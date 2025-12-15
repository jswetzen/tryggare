# Checkout Page Design Handoff - Expandable Table Layout

## Overview
Compact, expandable table design that minimizes scrolling. Families are collapsed by default showing only essential info. Click to expand and see individual children + pickup selector.

## Screenshots

### Desktop View (≥768px)
**Collapsed State:**
- Clean table with 48px row height
- ~15 families visible on laptop screen
- Sticky header stays visible when scrolling

**Expanded State:**
- Children rows appear with gray background
- Pickup selector at bottom of expanded section
- All actions inline and accessible

### Mobile View (<768px)
**Collapsed State:**
- Card-based layout with 56px height per family
- ~10 families visible on tablet portrait
- Times shown inline for quick context

**Expanded State:**
- Children listed with individual checkout buttons
- Pickup selector at bottom
- Touch-friendly 44px+ tap targets

---

## HTML Structure

### Mobile Layout (<768px)

#### Search Header (Sticky)
```html
<!-- Fixed header with search -->
<div class="bg-white border-b border-gray-200 px-4 py-3 sticky top-0 z-10">
  <div class="max-w-6xl mx-auto">
    <h1 class="text-lg font-semibold text-gray-900 mb-3">
      Search Checked-In Children
    </h1>
    
    <!-- Search bar -->
    <div class="relative">
      <input
        type="text"
        placeholder="Search families or children..."
        class="w-full h-12 pl-4 pr-10 border border-blue-500 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
      <!-- Clear button appears when there's text -->
      <button class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor">
          <path d="M6 6l8 8M14 6l-8 8" stroke-width="2" stroke-linecap="round"/>
        </svg>
      </button>
    </div>
  </div>
</div>
```

#### Family Card - Collapsed (Default)
```html
<!-- Single family collapsed -->
<div class="bg-white rounded-lg border border-gray-200 overflow-hidden">
  <!-- Collapsed header - clickable to expand -->
  <div class="flex items-center gap-3 px-4 py-3 cursor-pointer active:bg-gray-50">
    <!-- Chevron icon -->
    <div class="flex-shrink-0">
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor">
        <path d="M7 4l6 6-6 6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </div>
    
    <!-- Family info -->
    <div class="flex-1 min-w-0">
      <div class="flex items-center gap-2">
        <span class="font-medium text-gray-900">Smith</span>
        <span class="inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 bg-blue-100 text-blue-700 text-xs font-medium rounded">
          3
        </span>
        <span class="text-xs text-blue-600">Supervised</span>
      </div>
      <div class="text-sm text-gray-500 mt-0.5">
        13:05, 13:05, 13:22
      </div>
    </div>
    
    <!-- Check Out All button -->
    <button class="flex-shrink-0 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded hover:bg-blue-700 active:bg-blue-800">
      Check Out All
    </button>
  </div>
</div>
```

#### Family Card - Expanded
```html
<!-- Single family expanded -->
<div class="bg-white rounded-lg border border-gray-200 overflow-hidden">
  <!-- Header - now with down chevron -->
  <div class="flex items-center gap-3 px-4 py-3 cursor-pointer active:bg-gray-50">
    <div class="flex-shrink-0">
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor">
        <path d="M4 7l6 6 6-6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </div>
    
    <div class="flex-1 min-w-0">
      <div class="flex items-center gap-2">
        <span class="font-medium text-gray-900">Smith</span>
        <span class="inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 bg-blue-100 text-blue-700 text-xs font-medium rounded">
          3
        </span>
        <span class="text-xs text-blue-600">Supervised</span>
      </div>
      <div class="text-sm text-gray-500 mt-0.5">
        13:05, 13:05, 13:22
      </div>
    </div>
    
    <button class="flex-shrink-0 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded hover:bg-blue-700 active:bg-blue-800">
      Check Out All
    </button>
  </div>

  <!-- Expanded content -->
  <div class="border-t border-gray-200 bg-gray-50">
    <!-- Child 1 -->
    <div class="px-4 py-3 border-b border-gray-200 bg-white">
      <div class="flex items-center justify-between gap-3">
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <span class="text-gray-900">Olivia Smith</span>
            <!-- Blue dot = supervised -->
            <span class="inline-block w-2 h-2 bg-blue-600 rounded-full"></span>
            <span class="text-sm text-gray-500">13:05</span>
          </div>
        </div>
        
        <button class="px-3 py-1.5 bg-blue-600 text-white text-sm font-medium rounded hover:bg-blue-700">
          Check Out
        </button>
      </div>
    </div>

    <!-- Child 2 -->
    <div class="px-4 py-3 border-b border-gray-200 bg-white">
      <div class="flex items-center justify-between gap-3">
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <span class="text-gray-900">Noah Smith</span>
            <span class="inline-block w-2 h-2 bg-blue-600 rounded-full"></span>
            <span class="text-sm text-gray-500">13:05</span>
          </div>
        </div>
        
        <button class="px-3 py-1.5 bg-blue-600 text-white text-sm font-medium rounded hover:bg-blue-700">
          Check Out
        </button>
      </div>
    </div>

    <!-- Child 3 (not supervised - no dot) -->
    <div class="px-4 py-3 border-b border-gray-200 bg-white">
      <div class="flex items-center justify-between gap-3">
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <span class="text-gray-900">Ava Smith</span>
            <span class="text-sm text-gray-500">13:22</span>
          </div>
        </div>
        
        <button class="px-3 py-1.5 bg-blue-600 text-white text-sm font-medium rounded hover:bg-blue-700">
          Check Out
        </button>
      </div>
    </div>

    <!-- Pickup selector (always at bottom when expanded) -->
    <div class="px-4 py-3 bg-white border-t border-gray-200">
      <select class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm">
        <option value="">Picked up by...</option>
        <option value="1">Jennifer Smith (Parent)</option>
        <option value="2">Robert Smith (Parent)</option>
        <option value="3">Margaret Smith (Grandparent)</option>
      </select>
    </div>
  </div>
</div>
```

#### Multiple Families (Page Layout)
```html
<!-- Page wrapper -->
<div class="min-h-screen bg-gray-50">
  <!-- Header (shown above) -->
  
  <!-- Main content area -->
  <div class="max-w-6xl mx-auto p-4">
    <!-- List of families with 8px gap -->
    <div class="space-y-2">
      
      <!-- Family 1: Collapsed -->
      <div class="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <!-- ... collapsed card ... -->
      </div>

      <!-- Family 2: Expanded (shown in detail above) -->
      <div class="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <!-- ... expanded card ... -->
      </div>

      <!-- Family 3: Collapsed, single child -->
      <div class="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div class="flex items-center gap-3 px-4 py-3 cursor-pointer active:bg-gray-50">
          <div class="flex-shrink-0">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor">
              <path d="M7 4l6 6-6 6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2">
              <span class="font-medium text-gray-900">Williams</span>
              <span class="inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 bg-blue-100 text-blue-700 text-xs font-medium rounded">
                1
              </span>
            </div>
            <div class="text-sm text-gray-500 mt-0.5">
              13:30
            </div>
          </div>
          
          <button class="flex-shrink-0 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded hover:bg-blue-700 active:bg-blue-800">
            Check Out All
          </button>
        </div>
      </div>

    </div>
  </div>
</div>
```

---

## Desktop Layout (≥768px)

#### Table Structure
```html
<div class="min-h-screen bg-gray-50">
  <!-- Same header as mobile -->
  
  <!-- Main content -->
  <div class="max-w-6xl mx-auto p-4">
    <div class="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <table class="w-full">
        <!-- Sticky header -->
        <thead class="bg-gray-50 border-b border-gray-200 sticky top-[73px] z-[5]">
          <tr>
            <th class="px-4 py-3 text-left text-sm font-medium text-gray-700">
              Family (Count)
            </th>
            <th class="px-4 py-3 text-left text-sm font-medium text-gray-700">
              Check-ins
            </th>
            <th class="px-4 py-3 text-left text-sm font-medium text-gray-700">
            </th>
            <th class="px-4 py-3 text-right text-sm font-medium text-gray-700">
              Actions
            </th>
          </tr>
        </thead>
        
        <tbody>
          <!-- Family rows inside tbody -->
        </tbody>
      </table>
    </div>
  </div>
</div>
```

#### Family Row - Collapsed
```html
<!-- Single family row (collapsed) -->
<tr class="border-b border-gray-200 hover:bg-gray-50 cursor-pointer">
  <td class="px-4 py-3">
    <div class="flex items-center gap-2">
      <div class="flex-shrink-0">
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor">
          <path d="M6 3l6 6-6 6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>
      <span class="font-medium text-gray-900">Smith</span>
      <span class="inline-flex items-center justify-center min-w-[18px] h-5 px-1.5 bg-blue-100 text-blue-700 text-xs font-medium rounded">
        3
      </span>
      <span class="text-xs text-blue-600">Supervised</span>
    </div>
  </td>
  <td class="px-4 py-3 text-sm text-gray-600">
    13:05, 13:05, 13:22
  </td>
  <td class="px-4 py-3">
  </td>
  <td class="px-4 py-3 text-right">
    <button class="px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded hover:bg-blue-700">
      Check Out All
    </button>
  </td>
</tr>
```

#### Family Row - Expanded (with children)
```html
<!-- Family header row (expanded) -->
<tr class="border-b border-gray-200 hover:bg-gray-50 cursor-pointer">
  <td class="px-4 py-3">
    <div class="flex items-center gap-2">
      <div class="flex-shrink-0">
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor">
          <path d="M3 6l6 6 6-6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>
      <span class="font-medium text-gray-900">Smith</span>
      <span class="inline-flex items-center justify-center min-w-[18px] h-5 px-1.5 bg-blue-100 text-blue-700 text-xs font-medium rounded">
        3
      </span>
      <span class="text-xs text-blue-600">Supervised</span>
    </div>
  </td>
  <td class="px-4 py-3 text-sm text-gray-600">
    13:05, 13:05, 13:22
  </td>
  <td class="px-4 py-3">
  </td>
  <td class="px-4 py-3 text-right">
    <button class="px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded hover:bg-blue-700">
      Check Out All
    </button>
  </td>
</tr>

<!-- Child 1 row -->
<tr class="border-b border-gray-200 bg-gray-50">
  <td class="px-4 py-3 pl-12" colspan="2">
    <div class="flex items-center gap-2">
      <span class="text-gray-900">Olivia Smith</span>
      <span class="inline-block w-2 h-2 bg-blue-600 rounded-full"></span>
      <span class="text-sm text-gray-500">13:05</span>
    </div>
  </td>
  <td class="px-4 py-3" colspan="2">
    <div class="flex items-center justify-end">
      <button class="px-3 py-1.5 bg-blue-600 text-white text-sm font-medium rounded hover:bg-blue-700">
        Check Out
      </button>
    </div>
  </td>
</tr>

<!-- Child 2 row -->
<tr class="border-b border-gray-200 bg-gray-50">
  <td class="px-4 py-3 pl-12" colspan="2">
    <div class="flex items-center gap-2">
      <span class="text-gray-900">Noah Smith</span>
      <span class="inline-block w-2 h-2 bg-blue-600 rounded-full"></span>
      <span class="text-sm text-gray-500">13:05</span>
    </div>
  </td>
  <td class="px-4 py-3" colspan="2">
    <div class="flex items-center justify-end">
      <button class="px-3 py-1.5 bg-blue-600 text-white text-sm font-medium rounded hover:bg-blue-700">
        Check Out
      </button>
    </div>
  </td>
</tr>

<!-- Child 3 row -->
<tr class="border-b border-gray-200 bg-gray-50">
  <td class="px-4 py-3 pl-12" colspan="2">
    <div class="flex items-center gap-2">
      <span class="text-gray-900">Ava Smith</span>
      <span class="text-sm text-gray-500">13:22</span>
    </div>
  </td>
  <td class="px-4 py-3" colspan="2">
    <div class="flex items-center justify-end">
      <button class="px-3 py-1.5 bg-blue-600 text-white text-sm font-medium rounded hover:bg-blue-700">
        Check Out
      </button>
    </div>
  </td>
</tr>

<!-- Pickup selector row -->
<tr class="border-b border-gray-200 bg-gray-50">
  <td class="px-4 py-3 pl-12" colspan="4">
    <select class="w-full px-3 py-1.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm">
      <option value="">Picked up by...</option>
      <option value="1">Jennifer Smith (Parent)</option>
      <option value="2">Robert Smith (Parent)</option>
      <option value="3">Margaret Smith (Grandparent)</option>
    </select>
  </td>
</tr>
```

---

## Design Specifications

### Layout & Spacing

**Mobile (<768px):**
- Card layout with 8px gap between cards (`space-y-2`)
- Collapsed card height: 56px (py-3 = 12px top + 12px bottom + ~32px content)
- Expanded child row height: 48px (py-3)
- Page padding: 16px all sides (`p-4`)
- Border radius: 8px (`rounded-lg`)

**Desktop (≥768px):**
- Table layout with full-width cards
- Collapsed row height: 48px (py-3 = 12px top + 12px bottom + ~24px content)
- Expanded child row height: 44px (py-3)
- Indentation for children: 48px (`pl-12`)
- Page max-width: 1152px (`max-w-6xl`)

### Typography

| Element | Classes | Size | Weight | Color |
|---------|---------|------|--------|-------|
| Page title | `text-lg font-semibold text-gray-900` | 18px | 600 | gray-900 |
| Family name | `font-medium text-gray-900` | 16px | 500 | gray-900 |
| Child name | `text-gray-900` | 16px | 400 | gray-900 |
| Check-in time (inline) | `text-sm text-gray-500` | 14px | 400 | gray-500 |
| Child count badge | `text-xs font-medium text-blue-700` | 12px | 500 | blue-700 |
| Supervised label | `text-xs text-blue-600` | 12px | 400 | blue-600 |
| Button text | `text-sm font-medium` | 14px | 500 | white |

### Colors

**Primary Actions (Blue):**
- Background: `bg-blue-600` (#2563EB)
- Hover: `hover:bg-blue-700` (#1D4ED8)
- Active (mobile): `active:bg-blue-800` (#1E40AF)

**Borders:**
- Card border: `border-gray-200` (#E5E7EB)
- Input border: `border-gray-300` (#D1D5DB)
- Active input: `border-blue-500` (#3B82F6)

**Backgrounds:**
- Page: `bg-gray-50` (#F9FAFB)
- Cards: `bg-white` (#FFFFFF)
- Expanded rows: `bg-gray-50` (#F9FAFB)
- Count badge: `bg-blue-100` (#DBEAFE)
- Hover row: `hover:bg-gray-50` (#F9FAFB)

**Text:**
- Primary: `text-gray-900` (#111827)
- Secondary: `text-gray-600` (#4B5563)
- Meta: `text-gray-500` (#6B7280)
- Links/accents: `text-blue-600` (#2563EB)
- Badge text: `text-blue-700` (#1D4ED8)

### Interactive States

**Buttons:**
```html
<!-- Default -->
<button class="bg-blue-600 hover:bg-blue-700">

<!-- Active (mobile touch) -->
<button class="bg-blue-600 active:bg-blue-800">

<!-- Focus -->
<button class="focus:outline-none focus:ring-2 focus:ring-blue-500">
```

**Rows (clickable):**
```html
<!-- Default -->
<div class="cursor-pointer">

<!-- Hover (desktop) -->
<div class="hover:bg-gray-50">

<!-- Active (mobile) -->
<div class="active:bg-gray-50">
```

**Inputs:**
```html
<!-- Focus state -->
<input class="focus:outline-none focus:ring-2 focus:ring-blue-500">
<select class="focus:outline-none focus:ring-2 focus:ring-blue-500">
```

### Icons

**Chevron Right (Collapsed):**
```svg
<svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M7 4l6 6-6 6"/>
</svg>
```

**Chevron Down (Expanded):**
```svg
<svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M4 7l6 6 6-6"/>
</svg>
```

**X (Clear search):**
```svg
<svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
  <path d="M6 6l8 8M14 6l-8 8"/>
</svg>
```

**Supervised indicator:**
- Use a simple `<span>` with classes: `inline-block w-2 h-2 bg-blue-600 rounded-full`
- No SVG needed, just a blue dot

### Responsive Breakpoints

**Mobile: < 768px**
- Card-based layout
- Larger touch targets (44px minimum)
- Stacked content

**Desktop: ≥ 768px**
- Table layout
- Hover states active
- More compact spacing

**Switching point:**
```html
<!-- Show on mobile only -->
<div class="md:hidden">
  <!-- Mobile cards -->
</div>

<!-- Show on desktop only -->
<div class="hidden md:block">
  <!-- Desktop table -->
</div>
```

---

## Dynamic Content Notes

Replace static content with these variables:

| Static Content | Dynamic Variable | Notes |
|---------------|------------------|-------|
| "Smith" | `{family.surname}` | Family last name |
| "3" | `{family.children.length}` | Count of children |
| "13:05, 13:05, 13:22" | Format from `children[].checkinTime` | Join all times with ", " |
| "Supervised" | Show if `children.some(c => c.supervised)` | Only if at least one child supervised |
| "Olivia Smith" | `{child.firstName} {family.surname}` | Full child name |
| "13:05" | Format from `child.checkinTime` | Individual child time |
| Blue dot | Show if `child.supervised === true` | Conditional render |
| Select options | Loop through `family.guardians[]` | `{guardian.name} ({guardian.relationship})` |

### Conditional Rendering

**Supervised label (in collapsed family header):**
```
Show "Supervised" text only if: family.children.some(child => child.supervised === true)
```

**Supervised dot (next to child name):**
```
Show blue dot only if: child.supervised === true
```

**Clear search button:**
```
Show X icon only if: searchQuery.length > 0
```

**Empty state:**
```html
<!-- Show when no families match search -->
<div class="text-center py-12 text-gray-500">
  No families found matching "{searchQuery}"
</div>
```

---

## Interaction Behaviors

### Expand/Collapse Family

**Trigger:** Click anywhere on family header row/card  
**Exception:** Don't expand when clicking "Check Out All" button

**Visual changes:**
1. Chevron rotates: right → down
2. Children rows appear below with slide-down animation (200ms ease)
3. Pickup selector row appears at bottom

**On collapse:**
1. Chevron rotates: down → right
2. Children + pickup selector disappear with slide-up animation (200ms ease)

### Search Filtering

**Trigger:** Typing in search input  
**Behavior:** Real-time filter (no submit button)

**Matches on:**
- Family surname (partial, case-insensitive)
- Child first name (partial, case-insensitive)
- Full child name: "firstName surname" (partial, case-insensitive)

**Example:**
- Query: "oli" matches "Olivia Smith" and "Smith" family
- Query: "smith" matches "Smith" family and all children with surname Smith

### Checkout Actions

**"Check Out All" button:**
- Removes entire family card/row from list
- No confirmation needed
- Family disappears with fade-out animation (150ms)

**Individual "Check Out" button:**
- Removes that child row from expanded list
- If last child in family, removes entire family
- Child row disappears with fade-out animation (150ms)

### Pickup Selector

**Behavior:**
- Optional field, can be left as "Picked up by..."
- Selection persists for that family during session
- Same guardian applies to all children in family when using "Check Out All"
- When checking out individual child, uses currently selected guardian (if any)

---

## Edge Cases

### Single Child Family
```html
<!-- No different from multi-child, just 1 child row when expanded -->
<div class="bg-white rounded-lg border border-gray-200">
  <!-- Header shows (1) badge -->
  <div class="flex items-center gap-3 px-4 py-3">
    <!-- ... -->
    <span class="inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 bg-blue-100 text-blue-700 text-xs font-medium rounded">
      1
    </span>
    <!-- ... -->
  </div>
  
  <!-- When expanded, shows single child + pickup selector -->
</div>
```

### Many Children (5+)
- No visual difference in collapsed state
- When expanded, list grows vertically
- Pickup selector always at bottom regardless of child count
- Consider max-height with scroll if > 10 children (unlikely but possible)

### No Supervised Children
- Don't show "Supervised" label in family header
- Don't show blue dots next to any child names

### All Children Supervised
- Show "Supervised" label in family header
- Show blue dot next to each child name

### Long Names
- Child names truncate with ellipsis if needed: `truncate` class
- Family names should not wrap, use `whitespace-nowrap` if needed

### Empty Search Results
```html
<div class="text-center py-12 text-gray-500">
  No families found matching "xyz"
</div>
```

---

## Accessibility Notes

- All interactive elements have min 44x44px touch targets (mobile)
- Focus states visible on all interactive elements
- Semantic HTML: `<table>` for desktop, proper heading hierarchy
- Search input has placeholder text
- Buttons have clear labels ("Check Out All" vs "Check Out")
- Select has descriptive first option ("Picked up by...")

---

## Animation/Transitions

**Expand/collapse:**
- Duration: 200ms
- Easing: ease-in-out
- Affect: max-height and opacity

**Button hovers:**
- Duration: 150ms (Tailwind default with `transition-colors`)
- Affect: background-color only

**Row removal (checkout):**
- Duration: 150ms
- Easing: ease-out
- Affect: opacity + transform (slide up slightly)

**Search filtering:**
- Instant (no animation)

---

## Summary Checklist

✅ Complete HTML for mobile collapsed state  
✅ Complete HTML for mobile expanded state  
✅ Complete HTML for desktop table collapsed  
✅ Complete HTML for desktop table expanded  
✅ All Tailwind classes documented  
✅ Responsive breakpoint (768px) specified  
✅ Color palette defined  
✅ Typography scale defined  
✅ Spacing measurements provided  
✅ Interactive states documented  
✅ Edge cases covered  
✅ Dynamic content mapping provided  
✅ SVG icons included  
✅ Animation specs noted  

Ready for Svelte translation! 🚀
