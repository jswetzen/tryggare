<script lang="ts">
  /**
   * ExpandableListTable Component
   *
   * Generic expandable table/card layout that works for both family-based data and flat lists.
   * - Mobile: Card layout with expandable items
   * - Desktop: Table layout with expandable rows
   * - Uses slate-* color palette consistently
   * - Items collapsed by default to minimize scrolling
   */
  import type { Snippet } from 'svelte';

  interface Column {
    key: string;
    label: string;
    align?: 'left' | 'right' | 'center';
    class?: string;
  }

  interface ListItem {
    id: string;
    [key: string]: any;
    children?: any[];
  }

  interface Props {
    items: ListItem[];
    columns: Column[];
    onToggle?: (itemId: string, isExpanded: boolean) => void;
    headerRow?: Snippet<[ListItem]>;
    expandedContent?: Snippet<[ListItem]>;
    class?: string;
  }

  let {
    items,
    columns,
    onToggle,
    headerRow,
    expandedContent,
    class: className = ''
  }: Props = $props();

  // Track which items are expanded
  let expandedItems = $state<Set<string>>(new Set());

  function toggleItem(itemId: string, event: MouseEvent | KeyboardEvent) {
    // Prevent expansion if clicking on a button or interactive element
    const target = event.target as HTMLElement;
    if (target.closest('button') || target.closest('select') || target.closest('input')) {
      return;
    }

    const newExpanded = new Set(expandedItems);
    const wasExpanded = newExpanded.has(itemId);

    if (wasExpanded) {
      newExpanded.delete(itemId);
    } else {
      newExpanded.add(itemId);
    }

    expandedItems = newExpanded;

    if (onToggle) {
      onToggle(itemId, !wasExpanded);
    }
  }

  function isExpanded(itemId: string): boolean {
    return expandedItems.has(itemId);
  }

  function getColumnValue(item: ListItem, key: string): any {
    return item[key];
  }

  function getAlignment(align?: string): string {
    if (align === 'right') return 'text-right';
    if (align === 'center') return 'text-center';
    return 'text-left';
  }
</script>

<!-- Mobile Layout (<768px) -->
<div class="md:hidden space-y-3 {className}">
  {#each items as item (item.id)}
    {@const expanded = isExpanded(item.id)}
    {@const hasChildren = item.children && item.children.length > 0}

    <div class="bg-white rounded-lg border-2 border-slate-300 overflow-hidden">
      <!-- Card header - clickable to toggle if has children -->
      {#if hasChildren}
        <button
          class="flex items-center gap-3 px-4 py-3 w-full text-left cursor-pointer active:bg-slate-50"
          onclick={(e) => toggleItem(item.id, e)}
          onkeydown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              toggleItem(item.id, e);
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

          <!-- Item content -->
          <div class="flex-1 min-w-0">
            {#if headerRow}
              {@render headerRow(item)}
            {:else}
              <div class="flex items-center gap-2">
                {#each columns as column}
                  <span class="text-slate-900">
                    {getColumnValue(item, column.key)}
                  </span>
                {/each}
              </div>
            {/if}
          </div>
        </button>
      {:else}
        <div class="flex items-center gap-3 px-4 py-3">
          <!-- Item content (no expansion) -->
          <div class="flex-1 min-w-0">
            {#if headerRow}
              {@render headerRow(item)}
            {:else}
              <div class="flex items-center gap-2">
                {#each columns as column}
                  <span class="text-slate-900">
                    {getColumnValue(item, column.key)}
                  </span>
                {/each}
              </div>
            {/if}
          </div>
        </div>
      {/if}

      <!-- Expanded content -->
      {#if expanded && expandedContent && hasChildren}
        <div class="border-t border-slate-200 bg-slate-50">
          {@render expandedContent(item)}
        </div>
      {/if}
    </div>
  {/each}
</div>

<!-- Desktop Layout (≥768px) -->
<div class="hidden md:block bg-white rounded-lg border-2 border-slate-300 overflow-hidden {className}">
  <table class="w-full">
    <!-- Sticky header -->
    <thead class="bg-slate-50 border-b-2 border-slate-300 sticky top-0 z-[5]">
      <tr>
        {#each columns as column}
          <th class="px-4 py-3 {getAlignment(column.align)} text-sm font-medium text-slate-700 {column.class || ''}">
            {column.label}
          </th>
        {/each}
      </tr>
    </thead>

    <tbody>
      {#each items as item (item.id)}
        {@const expanded = isExpanded(item.id)}
        {@const hasChildren = item.children && item.children.length > 0}

        <!-- Item row -->
        <tr
          class="border-b border-slate-200 {hasChildren ? 'hover:bg-slate-50 cursor-pointer' : ''}"
          onclick={(e) => hasChildren && toggleItem(item.id, e)}
          role={hasChildren ? 'button' : undefined}
          tabindex={hasChildren ? 0 : undefined}
          onkeydown={(e) => {
            if (hasChildren && (e.key === 'Enter' || e.key === ' ')) {
              e.preventDefault();
              toggleItem(item.id, e);
            }
          }}
        >
          {#each columns as column, idx}
            <td class="px-4 py-3 {getAlignment(column.align)} {column.class || ''}">
              {#if idx === 0 && hasChildren}
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
                  {#if headerRow}
                    {@render headerRow(item)}
                  {:else}
                    <span class="text-slate-900">{getColumnValue(item, column.key)}</span>
                  {/if}
                </div>
              {:else}
                {#if headerRow && idx === 0}
                  {@render headerRow(item)}
                {:else}
                  <span class="text-slate-900">{getColumnValue(item, column.key)}</span>
                {/if}
              {/if}
            </td>
          {/each}
        </tr>

        <!-- Expanded rows (when expanded) -->
        {#if expanded && expandedContent && hasChildren}
          <tr class="border-b border-slate-200 bg-slate-50">
            <td colspan={columns.length} class="px-4 py-3">
              {@render expandedContent(item)}
            </td>
          </tr>
        {/if}
      {/each}
    </tbody>
  </table>
</div>
