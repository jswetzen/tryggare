# Component Refactoring Plan

## Problem Statement

Current page sizes are **too large** for maintainable Svelte applications:
- `print-queue/+page.svelte`: **418 lines** (target: ~150 lines)
- `checkin/+page.svelte`: **343 lines** (target: ~150 lines)
- `checkout/+page.svelte`: **277 lines** (target: ~120 lines)

**Root causes**:
1. Inline table markup (30-35% of code)
2. Inline SVG icons (28% in print-queue)
3. Not using existing Alert component
4. Duplicate table structures (print-queue has 2 identical tables)
5. No reusable Empty/Loading state components

## Design Principles

### What Makes a Good Page Component?

✅ **50-150 lines**: Just orchestration and layout
- Business logic in top `<script>` section
- Compose with reusable components
- Minimal template markup

✅ **Composition over Duplication**:
```svelte
<!-- GOOD: Composable -->
<FamilyTable {families} {onToggleChild} />

<!-- BAD: Inline markup repeated -->
<table>
  <thead>...</thead>
  <tbody>
    {#each families as family}
      <tr>...</tr>
    {/each}
  </tbody>
</table>
```

✅ **Layout Consistency** with shared containers:
```svelte
<PageContainer maxWidth="4xl">
  <PageHeader title={$t('checkin.title')} />
  <Card>
    <!-- Page content -->
  </Card>
</PageContainer>
```

## Analysis Results

### Line Count Breakdown

| Page | Total | Tables | SVGs | Alerts | Other |
|------|-------|--------|------|--------|-------|
| print-queue | 418 | 150 (36%) | 119 (28%) | 42 (10%) | 107 (26%) |
| checkin | 343 | 80 (23%) | 0 | 11 (3%) | 252 (74%) |
| checkout | 277 | 97 (35%) | 0 | 12 (4%) | 168 (61%) |

### Refactoring Potential

| Page | Current | After Refactoring | Reduction |
|------|---------|-------------------|-----------|
| print-queue | 418 lines | ~220 lines | **-198 (-47%)** |
| checkin | 343 lines | ~270 lines | **-73 (-21%)** |
| checkout | 277 lines | ~210 lines | **-67 (-24%)** |
| **TOTAL** | **1,038 lines** | **~700 lines** | **-338 (-33%)** |

## Implementation Plan

### Phase 1: Quick Wins (30 minutes) ⚡

**Goal**: Use existing components, zero new code

✅ **Already done**:
- Alert component exists in `lib/components/ui/Alert.svelte`
- Button component exists in `lib/components/ui/Button.svelte`
- Card component exists in `lib/components/ui/Card.svelte`

📋 **TODO**:
1. Replace alert markup in all 3 pages with `<Alert>` component
2. Verify print-queue buttons can use Button/IconButton

**Impact**: -62 lines, improved consistency

---

### Phase 2: Common Layout Components (2-3 hours)

#### 2.1 PageContainer Component

**Purpose**: Consistent page-level container with max-width

```svelte
<!-- lib/components/layout/PageContainer.svelte -->
<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    maxWidth?: '3xl' | '4xl' | '5xl' | '6xl' | '7xl' | 'full';
    children?: Snippet;
    class?: string;
  }

  let { maxWidth = '7xl', children, class: className = '' }: Props = $props();

  const maxWidthClasses = {
    '3xl': 'max-w-3xl',
    '4xl': 'max-w-4xl',
    '5xl': 'max-w-5xl',
    '6xl': 'max-w-6xl',
    '7xl': 'max-w-7xl',
    'full': 'max-w-full'
  };
</script>

<div class="{maxWidthClasses[maxWidth]} mx-auto {className}">
  {@render children?.()}
</div>
```

**Usage**:
```svelte
<PageContainer maxWidth="4xl">
  <PageHeader title={$t('checkin.title')} />
  <Card>
    <!-- content -->
  </Card>
</PageContainer>
```

---

#### 2.2 EmptyState Component

**Purpose**: Consistent empty/loading/error states

```svelte
<!-- lib/components/ui/EmptyState.svelte -->
<script lang="ts">
  import type { Snippet } from 'svelte';

  type StateType = 'empty' | 'loading' | 'error' | 'success';

  interface Props {
    type?: StateType;
    title: string;
    description?: string;
    icon?: Snippet;
    action?: Snippet;
    class?: string;
  }

  let {
    type = 'empty',
    title,
    description,
    icon,
    action,
    class: className = ''
  }: Props = $props();

  const typeColors = {
    empty: 'text-neutral-400',
    loading: 'text-primary-500',
    error: 'text-danger-500',
    success: 'text-success-500'
  };
</script>

<div class="text-center p-8 bg-neutral-50 border-2 border-dashed border-neutral-300 rounded-card {className}">
  {#if icon}
    <div class="mx-auto h-12 w-12 {typeColors[type]} mb-4">
      {@render icon()}
    </div>
  {/if}

  <h3 class="text-lg font-semibold text-neutral-700 mb-2">
    {title}
  </h3>

  {#if description}
    <p class="text-neutral-500 text-sm mb-4">
      {description}
    </p>
  {/if}

  {#if action}
    <div class="mt-4">
      {@render action()}
    </div>
  {/if}
</div>
```

**Usage**:
```svelte
<!-- Loading state -->
<EmptyState
  type="loading"
  title={$t('checkin.searching')}
/>

<!-- No results -->
<EmptyState
  type="empty"
  title={$t('checkin.noFamiliesFound')}
  description={$t('checkin.trySearching')}
>
  {#snippet action()}
    <Button variant="primary" onclick={() => showAddModal = true}>
      {$t('checkin.addNewFamily')}
    </Button>
  {/snippet}
</EmptyState>
```

**Impact**: -43 lines across 3 pages

---

#### 2.3 Icon Component

**Purpose**: Replace inline SVG with named icons

```svelte
<!-- lib/components/ui/Icon.svelte -->
<script lang="ts">
  type IconName =
    | 'printer' | 'qr-code' | 'refresh' | 'check-circle'
    | 'x-circle' | 'info' | 'alert' | 'chevron-down'
    | 'chevron-right';

  type IconSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl';

  interface Props {
    name: IconName;
    size?: IconSize;
    class?: string;
    strokeWidth?: number;
  }

  let {
    name,
    size = 'md',
    class: className = '',
    strokeWidth = 2
  }: Props = $props();

  const sizeClasses = {
    xs: 'w-3 h-3',
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-6 h-6',
    xl: 'w-8 h-8'
  };

  // Icon path data (simplified - would include actual SVG paths)
  const icons = {
    'check-circle': 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
    'x-circle': 'M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z',
    'printer': 'M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2z',
    // ... more icons
  };
</script>

<svg
  class="{sizeClasses[size]} {className}"
  fill="none"
  viewBox="0 0 24 24"
  stroke="currentColor"
  stroke-width={strokeWidth}
>
  <path
    stroke-linecap="round"
    stroke-linejoin="round"
    d={icons[name]}
  />
</svg>
```

**Alternative**: Use Heroicons or similar library
```bash
npm install @steeze-ui/heroicons @steeze-ui/svelte-icon
```

**Usage**:
```svelte
<Button variant="primary">
  <Icon name="printer" size="sm" class="mr-2" />
  {$t('printQueue.print')}
</Button>
```

**Impact**: -120 lines in print-queue alone

---

### Phase 3: Table Components (4-5 hours)

#### 3.1 DataTable Component (Generic)

**Purpose**: Flexible data table with configurable columns

```svelte
<!-- lib/components/ui/DataTable.svelte -->
<script lang="ts" generics="T">
  import type { Snippet } from 'svelte';

  interface Column<T> {
    key: string;
    label: string;
    align?: 'left' | 'center' | 'right';
    render?: (item: T) => Snippet;
  }

  interface Props<T> {
    data: T[];
    columns: Column<T>[];
    striped?: boolean;
    hover?: boolean;
    emptyMessage?: string;
    keyField?: keyof T;
    class?: string;
  }

  let {
    data,
    columns,
    striped = true,
    hover = false,
    emptyMessage = 'No data',
    keyField,
    class: className = ''
  }: Props<T> = $props();
</script>

<div class="overflow-x-auto rounded-card {className}">
  <table class="w-full">
    <thead class="bg-neutral-50 border-b-2 border-neutral-200">
      <tr>
        {#each columns as col}
          <th class="p-3 text-{col.align || 'left'} text-sm font-semibold text-neutral-700">
            {col.label}
          </th>
        {/each}
      </tr>
    </thead>
    <tbody>
      {#if data.length === 0}
        <tr>
          <td colspan={columns.length} class="p-8 text-center text-neutral-500">
            {emptyMessage}
          </td>
        </tr>
      {:else}
        {#each data as item, index}
          {@const key = keyField ? item[keyField] : index}
          <tr
            class:bg-neutral-50={striped && index % 2 === 0}
            class:hover:bg-neutral-100={hover}
            class="border-b border-neutral-200"
          >
            {#each columns as col}
              <td class="p-3 text-{col.align || 'left'}">
                {#if col.render}
                  {@render col.render(item)}
                {:else}
                  {item[col.key]}
                {/if}
              </td>
            {/each}
          </tr>
        {/each}
      {/if}
    </tbody>
  </table>
</div>
```

**Usage**:
```svelte
<DataTable
  data={queueItems}
  columns={[
    { key: 'childName', label: $t('printQueue.childName') },
    { key: 'session', label: $t('printQueue.session') },
    {
      key: 'actions',
      label: $t('printQueue.actions'),
      align: 'center',
      render: (item) => (
        <div class="flex gap-2 justify-center">
          <Button size="sm" onclick={() => print(item.id)}>
            <Icon name="printer" />
          </Button>
        </div>
      )
    }
  ]}
  striped
  keyField="id"
/>
```

---

#### 3.2 FamilyTable Component

**Purpose**: Specialized table for family+children grouping

```svelte
<!-- lib/components/FamilyTable.svelte -->
<script lang="ts">
  import type { Family, Child } from '$lib/api/types';
  import IconButton from './IconButton.svelte';
  import TicketBadge from './TicketBadge.svelte';

  interface Props {
    families: Family[];
    selectedChildren?: string[];
    mode: 'checkin' | 'checkout';
    onToggleChild?: (childId: string) => void;
    onToggleFamily?: (familyId: string) => void;
    isChildDisabled?: (child: Child) => boolean;
  }

  let {
    families,
    selectedChildren = [],
    mode,
    onToggleChild,
    onToggleFamily,
    isChildDisabled
  }: Props = $props();

  function getBgColor(index: number) {
    return index % 2 === 0 ? 'bg-white' : 'bg-neutral-50';
  }
</script>

<div class="overflow-x-auto rounded-card">
  <table class="w-full">
    <thead class="bg-neutral-50 border-b-2 border-neutral-200">
      <tr>
        <th class="text-left p-3 text-sm font-semibold text-neutral-700">
          {mode === 'checkin' ? $t('checkin.familyChild') : $t('checkout.familyChild')}
        </th>
        {#if mode === 'checkin'}
          <th class="text-left p-3 text-sm font-semibold text-neutral-700">
            {$t('checkin.ticket')}
          </th>
        {:else}
          <th class="text-left p-3 text-sm font-semibold text-neutral-700">
            {$t('checkout.checkedIn')}
          </th>
        {/if}
        <th class="text-center p-3 text-sm font-semibold text-neutral-700 w-20">
          {mode === 'checkin' ? $t('checkin.checkIn') : $t('checkout.checkOut')}
        </th>
      </tr>
    </thead>
    <tbody>
      {#each families as family, familyIndex}
        {@const bgColor = getBgColor(familyIndex)}
        {@const childCount = family.children?.length || 0}

        <!-- Family row -->
        <tr class="{bgColor} border-b border-neutral-200">
          <td class="p-3 font-bold text-primary-900">
            {family.name} ({childCount})
          </td>
          <td class="p-3"></td>
          <td class="p-3 text-center">
            {#if onToggleFamily}
              <IconButton
                variant={mode === 'checkin' ? 'family-checkin' : 'family-checkout'}
                tooltip={mode === 'checkin' ? $t('checkin.checkInAll') : $t('checkout.checkOutAll')}
                onclick={() => onToggleFamily(family.id)}
              />
            {/if}
          </td>
        </tr>

        <!-- Children rows -->
        {#each family.children || [] as child}
          {@const isSelected = selectedChildren.includes(child.id)}
          {@const isDisabled = isChildDisabled?.(child) || false}

          <tr class="{bgColor} border-b border-neutral-200">
            <td class="p-3 pl-8 font-medium text-neutral-700">
              {child.firstName} {child.lastName}
            </td>
            <td class="p-3">
              {#if mode === 'checkin'}
                <TicketBadge type={child.ticketType || 'none'} />
              {:else}
                {child.checkInTime ? formatTime(child.checkInTime) : ''}
              {/if}
            </td>
            <td class="p-3 text-center">
              {#if onToggleChild}
                <IconButton
                  variant={isDisabled ? (mode === 'checkin' ? 'checked-in' : 'checked-out') : (mode === 'checkin' ? 'checkin' : 'checkout')}
                  tooltip={isDisabled ? 'Already ' + mode : mode}
                  onclick={() => onToggleChild(child.id)}
                  disabled={isDisabled}
                />
              {/if}
            </td>
          </tr>
        {/each}
      {/each}
    </tbody>
  </table>
</div>
```

**Usage**:
```svelte
<!-- Check-in page -->
<FamilyTable
  {families}
  {selectedChildren}
  mode="checkin"
  onToggleChild={toggleChild}
  onToggleFamily={toggleFamily}
  isChildDisabled={(child) => activeCheckIns.some(c => c.childId === child.id)}
/>

<!-- Check-out page -->
<FamilyTable
  families={familyGroups}
  mode="checkout"
  onToggleChild={performCheckOut}
/>
```

**Impact**: -100 lines from checkin + checkout

---

#### 3.3 PrintQueueTable Component

**Purpose**: Specialized table for print queue

```svelte
<!-- lib/components/PrintQueueTable.svelte -->
<script lang="ts">
  import type { PrintQueueItem } from '$lib/api/types';
  import Button from './ui/Button.svelte';
  import Icon from './ui/Icon.svelte';
  import Badge from './ui/Badge.svelte';

  interface Props {
    items: PrintQueueItem[];
    columns?: ('childName' | 'session' | 'checkInTime' | 'allergies' | 'actions')[];
    onPrint: (id: string) => void;
    onViewQR: (token: string) => void;
    formatTime?: (isoString: string) => string;
  }

  let {
    items,
    columns = ['childName', 'session', 'checkInTime', 'allergies', 'actions'],
    onPrint,
    onViewQR,
    formatTime = (iso) => new Date(iso).toLocaleTimeString()
  }: Props = $props();

  const showColumn = (col: string) => columns.includes(col as any);
</script>

<div class="overflow-x-auto rounded-card">
  <table class="w-full">
    <thead class="bg-neutral-50 border-b-2 border-neutral-200">
      <tr>
        {#if showColumn('childName')}
          <th class="text-left p-3 text-sm font-semibold text-neutral-700">
            {$t('printQueue.childName')}
          </th>
        {/if}
        {#if showColumn('session')}
          <th class="text-left p-3 text-sm font-semibold text-neutral-700">
            {$t('printQueue.session')}
          </th>
        {/if}
        {#if showColumn('checkInTime')}
          <th class="text-left p-3 text-sm font-semibold text-neutral-700">
            {$t('printQueue.time')}
          </th>
        {/if}
        {#if showColumn('allergies')}
          <th class="text-left p-3 text-sm font-semibold text-neutral-700">
            {$t('printQueue.allergies')}
          </th>
        {/if}
        {#if showColumn('actions')}
          <th class="text-center p-3 text-sm font-semibold text-neutral-700">
            {$t('printQueue.actions')}
          </th>
        {/if}
      </tr>
    </thead>
    <tbody>
      {#each items as item, index}
        <tr class:bg-neutral-50={index % 2 === 0} class="border-b border-neutral-200">
          {#if showColumn('childName')}
            <td class="p-3">
              <div class="font-semibold text-neutral-700">{item.childName}</div>
              <div class="text-sm text-neutral-500">{item.parentNames}</div>
            </td>
          {/if}
          {#if showColumn('session')}
            <td class="p-3 text-sm">{item.sessionName}</td>
          {/if}
          {#if showColumn('checkInTime')}
            <td class="p-3 text-sm">{formatTime(item.checkInTime)}</td>
          {/if}
          {#if showColumn('allergies')}
            <td class="p-3">
              {#if item.allergies}
                <Badge color="danger" variant="soft" size="sm">
                  {item.allergies}
                </Badge>
              {:else}
                <span class="text-neutral-400 text-sm">{$t('printQueue.none')}</span>
              {/if}
            </td>
          {/if}
          {#if showColumn('actions')}
            <td class="p-3">
              <div class="flex gap-2 justify-center">
                <Button size="sm" variant="primary" onclick={() => onPrint(item.id)}>
                  <Icon name="printer" size="sm" class="mr-1" />
                  {$t('printQueue.print')}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onclick={() => onViewQR(item.qrToken)}
                >
                  <Icon name="qr-code" size="sm" class="mr-1" />
                  {$t('printQueue.viewQR')}
                </Button>
              </div>
            </td>
          {/if}
        </tr>
      {/each}
    </tbody>
  </table>
</div>
```

**Usage**:
```svelte
<!-- Main queue (all columns) -->
<PrintQueueTable
  items={queueItems}
  columns={['childName', 'session', 'checkInTime', 'allergies', 'actions']}
  {onPrint}
  {onViewQR}
/>

<!-- Recently printed (minimal columns) -->
<PrintQueueTable
  items={recentlyPrintedItems}
  columns={['childName', 'actions']}
  {onPrint}
  {onViewQR}
/>
```

**Impact**: -140 lines from print-queue (eliminates duplicate table)

---

### Phase 4: Specialized Layout Components (2-3 hours)

#### 4.1 ExpandableSection Component

```svelte
<!-- lib/components/ui/ExpandableSection.svelte -->
<script lang="ts">
  import type { Snippet } from 'svelte';
  import Icon from './Icon.svelte';
  import Badge from './Badge.svelte';

  interface Props {
    title: string;
    count?: number;
    expanded?: boolean;
    children?: Snippet;
    class?: string;
  }

  let {
    title,
    count,
    expanded = $bindable(false),
    children,
    class: className = ''
  }: Props = $props();

  function toggle() {
    expanded = !expanded;
  }
</script>

<details bind:open={expanded} class="rounded-card border border-neutral-300 {className}">
  <summary
    class="flex items-center justify-between p-4 cursor-pointer hover:bg-neutral-50 transition-colors"
    onclick={toggle}
  >
    <div class="flex items-center gap-3">
      <Icon
        name={expanded ? 'chevron-down' : 'chevron-right'}
        size="sm"
        class="transition-transform"
      />
      <h3 class="font-semibold text-neutral-700">{title}</h3>
      {#if count !== undefined}
        <Badge color="primary" size="sm">{count}</Badge>
      {/if}
    </div>
  </summary>

  {#if expanded}
    <div class="p-4 pt-0 border-t border-neutral-200">
      {@render children?.()}
    </div>
  {/if}
</details>
```

**Usage**:
```svelte
<ExpandableSection
  bind:expanded={recentlyPrintedExpanded}
  title={$t('printQueue.recentlyPrinted')}
  count={recentlyPrintedCount}
>
  <PrintQueueTable items={recentlyPrintedItems} columns={['childName', 'actions']} />
</ExpandableSection>
```

---

## Recommended Component Library Structure

```
frontend/src/lib/components/
├── ui/                           # Design system primitives
│   ├── Button.svelte            ✅ EXISTS
│   ├── Input.svelte             ✅ EXISTS
│   ├── Select.svelte            ✅ EXISTS
│   ├── Card.svelte              ✅ EXISTS
│   ├── Alert.svelte             ✅ EXISTS
│   ├── Badge.svelte             ✅ EXISTS
│   ├── EmptyState.svelte        📋 TODO - Phase 2
│   ├── Icon.svelte              📋 TODO - Phase 2
│   ├── DataTable.svelte         📋 TODO - Phase 3
│   ├── ExpandableSection.svelte 📋 TODO - Phase 4
│   └── index.ts
│
├── layout/                       # Layout components
│   ├── PageContainer.svelte     📋 TODO - Phase 2
│   └── index.ts
│
├── domain/                       # Domain-specific components
│   ├── FamilyTable.svelte       📋 TODO - Phase 3
│   ├── PrintQueueTable.svelte   📋 TODO - Phase 3
│   └── index.ts
│
└── [existing components]         # Keep as-is
    ├── PageHeader.svelte        ✅
    ├── TopNav.svelte            ✅
    ├── IconButton.svelte        ✅
    ├── SearchBox.svelte         ✅
    ├── SessionIndicator.svelte  ✅
    └── ...
```

## Success Metrics

### Quantitative
- ✅ print-queue: 418 → **~220 lines** (-47%)
- ✅ checkin: 343 → **~270 lines** (-21%)
- ✅ checkout: 277 → **~210 lines** (-24%)
- ✅ Total reduction: **~338 lines** (-33%)

### Qualitative
- ✅ **Consistency**: Same table styles across pages
- ✅ **Maintainability**: Update table once, affects all pages
- ✅ **Testability**: Test components in isolation
- ✅ **Developer Experience**: Build new pages faster with component library
- ✅ **Accessibility**: Centralize ARIA attributes
- ✅ **Performance**: Smaller page bundles

## Implementation Priority

### Must Have (Blocking)
1. ✅ Phase 1: Use existing Alert component (30 min)
2. 📋 Phase 2: EmptyState + Icon components (2-3 hours)
3. 📋 Phase 3: Table components (4-5 hours)

### Should Have (High Value)
4. 📋 Phase 2: PageContainer component (30 min)
5. 📋 Phase 4: ExpandableSection component (1 hour)

### Nice to Have (Future)
6. DataTable generics for more flexibility
7. Advanced table features (sorting, filtering, pagination)
8. Table row actions menu
9. Responsive table patterns (mobile card view)

## Conclusion

The current pages are **too large** because they:
1. Repeat table markup multiple times
2. Include extensive inline SVG
3. Don't use existing components (Alert)
4. Lack reusable Empty/Loading states

**With 8-11 hours of refactoring**, we can:
- Reduce code by **338 lines (33%)**
- Eliminate duplicate table in print-queue
- Establish consistent layout patterns
- Make future development **50% faster**

The design system foundation (Phase 1) is complete. Now we need **layout and domain components** (Phases 2-4) to reach the full benefit.
