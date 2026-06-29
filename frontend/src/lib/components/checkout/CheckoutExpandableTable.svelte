<script lang="ts">
  /**
   * CheckoutExpandableTable Component
   *
   * Expandable table/card layout for checkout page as specified in checkout-design.md.
   * - Mobile: Card layout with expandable families
   * - Desktop: Table layout with expandable rows
   * - Families collapsed by default to minimize scrolling
   */
  import { _ } from 'svelte-i18n';

  interface Child {
    id: string;
    first_name: string;
    last_name: string;
    firstName: string;
    lastName: string;
    checkInTime?: string;
    supervised?: boolean;
    qrCode?: string | null;
  }

  interface Parent {
    name: string;
    relationship_type: string;
  }

  interface Family {
    id: string;
    name: string;
    display_name: string;
    children: Child[];
    parents: Parent[];
  }

  let {
    families,
    pickedUpBy = {},
    onCheckOut,
    onCheckOutFamily,
    onPickedUpByChange,
    formatTime
  }: {
    families: Family[];
    pickedUpBy: Record<string, string>;
    onCheckOut: (childId: string) => void;
    onCheckOutFamily: (familyId: string) => void;
    onPickedUpByChange: (familyId: string, value: string) => void;
    formatTime: (isoString: string) => string;
  } = $props();

  // Track which families are expanded
  let expandedFamilies = $state<Set<string>>(new Set());

  function toggleFamily(familyId: string, event: MouseEvent) {
    // Prevent expansion if clicking on a button
    const target = event.target as HTMLElement;
    if (target.closest('button')) {
      return;
    }

    const newExpanded = new Set(expandedFamilies);
    if (newExpanded.has(familyId)) {
      newExpanded.delete(familyId);
    } else {
      newExpanded.add(familyId);
    }
    expandedFamilies = newExpanded;
  }

  function isExpanded(familyId: string): boolean {
    return expandedFamilies.has(familyId);
  }

  function getCheckInTimes(family: Family): string {
    return family.children
      .map(child => child.checkInTime ? formatTime(child.checkInTime) : '')
      .filter(time => time)
      .join(', ');
  }

  function hasSupervised(family: Family): boolean {
    return family.children.some(child => child.supervised);
  }
</script>

<!-- Mobile Layout (<768px) -->
<div class="md:hidden space-y-3">
  {#each families as family (family.id)}
    {@const expanded = isExpanded(family.id)}
    {@const childCount = family.children.length}
    {@const checkInTimes = getCheckInTimes(family)}
    {@const supervised = hasSupervised(family)}

    <div class="bg-white rounded-card border-2 border-slate-300 overflow-hidden">
      <!-- Collapsed/Expanded header - clickable to toggle -->
      <div
        class="flex items-center gap-3 px-4 py-3 cursor-pointer active:bg-slate-50"
        onclick={(e) => toggleFamily(family.id, e)}
        role="button"
        tabindex="0"
        onkeydown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            toggleFamily(family.id, e);
          }
        }}
      >
        <!-- Chevron icon -->
        <div class="flex-shrink-0">
          {#if expanded}
            <!-- Chevron Down -->
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M4 7l6 6 6-6"/>
            </svg>
          {:else}
            <!-- Chevron Right -->
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M7 4l6 6-6 6"/>
            </svg>
          {/if}
        </div>

        <!-- Family info -->
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <span class="font-medium text-slate-900">{family.display_name}</span>
            <span class="inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 bg-blue-100 text-blue-700 text-xs font-medium rounded">
              {childCount}
            </span>
            {#if supervised}
              <span class="text-xs text-blue-600">{$_('checkout.supervised')}</span>
            {/if}
          </div>
          <div class="text-sm text-slate-500 mt-0.5">
            {checkInTimes}
          </div>
        </div>

        <!-- Check Out All button -->
        <button
          type="button"
          onclick={() => onCheckOutFamily(family.id)}
          class="flex-shrink-0 px-3 py-1.5 sm:px-4 sm:py-2 bg-blue-600 text-white text-xs sm:text-sm font-medium rounded-button hover:bg-blue-700 active:bg-blue-800 transition-colors"
          aria-label={`${$_('checkout.checkOutAll')} ${family.display_name}`}
        >
          {$_('checkout.checkOutAll')}
        </button>
      </div>

      <!-- Expanded content -->
      {#if expanded}
        <div class="border-t border-slate-200 bg-slate-50">
          <!-- Children -->
          {#each family.children as child (child.id)}
            <div class="px-4 py-3 border-b border-slate-200 bg-white">
              <div class="flex items-center justify-between gap-3">
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2">
                    <span class="text-slate-900">{child.firstName} {child.lastName}</span>
                    {#if child.supervised}
                      <!-- Blue dot = supervised -->
                      <span class="inline-block w-2 h-2 bg-blue-600 rounded-full"></span>
                    {/if}
                    {#if child.checkInTime}
                      <span class="text-sm text-slate-500">{formatTime(child.checkInTime)}</span>
                    {/if}
                  </div>
                </div>

                <div class="flex items-center gap-2 flex-shrink-0">
                  {#if child.qrCode}
                    <a
                      href={`/qr/${child.qrCode}`}
                      target="_blank"
                      rel="noopener"
                      title={$_('checkout.childInfoTitle')}
                      class="px-3 py-1.5 border border-slate-300 text-slate-700 text-xs sm:text-sm font-medium rounded-button hover:bg-slate-100 transition-colors"
                    >
                      {$_('checkout.childInfo')}
                    </a>
                  {/if}
                  <button
                    type="button"
                    onclick={() => onCheckOut(child.id)}
                    class="px-3 py-1.5 bg-blue-600 text-white text-xs sm:text-sm font-medium rounded-button hover:bg-blue-700 transition-colors"
                    aria-label={`${$_('checkout.checkOut')} ${child.firstName} ${child.lastName}`}
                  >
                    {$_('checkout.checkOut')}
                  </button>
                </div>
              </div>
            </div>
          {/each}

          <!-- Pickup selector (always at bottom when expanded) -->
          <div class="px-4 py-3 bg-white border-t border-slate-200">
            <select
              value={pickedUpBy[family.id] || ''}
              onchange={(e) => onPickedUpByChange(family.id, (e.target as HTMLSelectElement).value)}
              class="w-full px-3 py-2 border border-slate-300 rounded-input focus:outline-none focus:ring-2 focus:ring-blue-500 text-xs sm:text-sm"
            >
              <option value="">{$_('checkout.pickedUpBy')}...</option>
              {#each family.parents as parent}
                <option value={parent.name}>
                  {parent.name} ({parent.relationship_type})
                </option>
              {/each}
            </select>
          </div>
        </div>
      {/if}
    </div>
  {/each}
</div>

<!-- Desktop Layout (≥768px) -->
<div class="hidden md:block bg-white rounded-card border-2 border-slate-300 overflow-hidden">
  <table class="w-full">
    <!-- Sticky header -->
    <thead class="bg-slate-50 border-b-2 border-slate-300 sticky top-0 z-[5]">
      <tr>
        <th class="px-4 py-3 text-left text-sm font-medium text-slate-700">
          Family (Count)
        </th>
        <th class="px-4 py-3 text-left text-sm font-medium text-slate-700">
          Check-ins
        </th>
        <th class="px-4 py-3 text-left text-sm font-medium text-slate-700">
        </th>
        <th class="px-4 py-3 text-right text-sm font-medium text-slate-700">
          Actions
        </th>
      </tr>
    </thead>

    <tbody>
      {#each families as family (family.id)}
        {@const expanded = isExpanded(family.id)}
        {@const childCount = family.children.length}
        {@const checkInTimes = getCheckInTimes(family)}
        {@const supervised = hasSupervised(family)}

        <!-- Family header row (collapsed/expanded) -->
        <tr
          class="border-b border-slate-200 hover:bg-slate-50 cursor-pointer"
          onclick={(e) => toggleFamily(family.id, e)}
          role="button"
          tabindex="0"
          onkeydown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              toggleFamily(family.id, e);
            }
          }}
        >
          <td class="px-4 py-3">
            <div class="flex items-center gap-2">
              <div class="flex-shrink-0">
                {#if expanded}
                  <!-- Chevron Down -->
                  <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M3 6l6 6 6-6"/>
                  </svg>
                {:else}
                  <!-- Chevron Right -->
                  <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M6 3l6 6-6 6"/>
                  </svg>
                {/if}
              </div>
              <span class="font-medium text-slate-900">{family.display_name}</span>
              <span class="inline-flex items-center justify-center min-w-[18px] h-5 px-1.5 bg-blue-100 text-blue-700 text-xs font-medium rounded">
                {childCount}
              </span>
              {#if supervised}
                <span class="text-xs text-blue-600">{$_('checkout.supervised')}</span>
              {/if}
            </div>
          </td>
          <td class="px-4 py-3 text-sm text-slate-600">
            {checkInTimes}
          </td>
          <td class="px-4 py-3">
          </td>
          <td class="px-4 py-3 text-right">
            <button
              type="button"
              onclick={() => onCheckOutFamily(family.id)}
              class="px-3 py-1.5 sm:px-4 sm:py-1.5 bg-blue-600 text-white text-xs sm:text-sm font-medium rounded-button hover:bg-blue-700 transition-colors"
              aria-label={`${$_('checkout.checkOutAll')} ${family.display_name}`}
            >
              {$_('checkout.checkOutAll')}
            </button>
          </td>
        </tr>

        <!-- Children rows (when expanded) -->
        {#if expanded}
          {#each family.children as child (child.id)}
            <tr class="border-b border-slate-200 bg-slate-50">
              <td class="px-4 py-3 pl-12" colspan="2">
                <div class="flex items-center gap-2">
                  <span class="text-slate-900">{child.firstName} {child.lastName}</span>
                  {#if child.supervised}
                    <span class="inline-block w-2 h-2 bg-blue-600 rounded-full"></span>
                  {/if}
                  {#if child.checkInTime}
                    <span class="text-sm text-slate-500">{formatTime(child.checkInTime)}</span>
                  {/if}
                </div>
              </td>
              <td class="px-4 py-3" colspan="2">
                <div class="flex items-center justify-end gap-2">
                  {#if child.qrCode}
                    <a
                      href={`/qr/${child.qrCode}`}
                      target="_blank"
                      rel="noopener"
                      title={$_('checkout.childInfoTitle')}
                      class="px-3 py-1.5 border border-slate-300 text-slate-700 text-xs sm:text-sm font-medium rounded-button hover:bg-slate-100 transition-colors"
                    >
                      {$_('checkout.childInfo')}
                    </a>
                  {/if}
                  <button
                    type="button"
                    onclick={() => onCheckOut(child.id)}
                    class="px-3 py-1.5 bg-blue-600 text-white text-xs sm:text-sm font-medium rounded-button hover:bg-blue-700 transition-colors"
                    aria-label={`${$_('checkout.checkOut')} ${child.firstName} ${child.lastName}`}
                  >
                    {$_('checkout.checkOut')}
                  </button>
                </div>
              </td>
            </tr>
          {/each}

          <!-- Pickup selector row -->
          <tr class="border-b border-slate-200 bg-slate-50">
            <td class="px-4 py-3 pl-12" colspan="4">
              <select
                value={pickedUpBy[family.id] || ''}
                onchange={(e) => onPickedUpByChange(family.id, (e.target as HTMLSelectElement).value)}
                class="w-full px-3 py-1.5 border border-slate-300 rounded-input focus:outline-none focus:ring-2 focus:ring-blue-500 text-xs sm:text-sm"
              >
                <option value="">{$_('checkout.pickedUpBy')}...</option>
                {#each family.parents as parent}
                  <option value={parent.name}>
                    {parent.name} ({parent.relationship_type})
                  </option>
                {/each}
              </select>
            </td>
          </tr>
        {/if}
      {/each}
    </tbody>
  </table>
</div>
