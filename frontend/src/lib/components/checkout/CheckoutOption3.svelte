<script lang="ts">
  /**
   * Option 3: Table on Desktop, Compact Cards on Mobile
   * Adaptive design - best of both worlds
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
    family,
    pickedUpBy = '',
    onCheckOut,
    onCheckOutFamily,
    onPickedUpByChange,
    formatTime
  }: {
    family: Family;
    pickedUpBy: string;
    onCheckOut: (childId: string) => void;
    onCheckOutFamily: () => void;
    onPickedUpByChange: (value: string) => void;
    formatTime: (isoString: string) => string;
  } = $props();
</script>

<!-- Mobile: Compact card -->
<div class="sm:hidden bg-white border border-slate-200 rounded-lg p-2 mb-2">
  <div class="flex items-center justify-between mb-1.5">
    <h4 class="font-bold text-slate-800 text-sm">{family.name} ({family.children.length})</h4>
    <button
      on:click={onCheckOutFamily}
      class="px-2 py-1 bg-red-600 text-white text-xs font-semibold rounded"
    >
      All
    </button>
  </div>
  {#each family.children as child}
    <div class="flex items-center justify-between py-1 text-sm border-t border-slate-100">
      <div class="flex-1">
        <div>{child.firstName} {child.lastName}</div>
        <div class="text-xs text-slate-500">
          {child.checkInTime ? formatTime(child.checkInTime) : ''}
        </div>
      </div>
      <button
        on:click={() => onCheckOut(child.id)}
        class="px-2 py-1 bg-red-500 text-white text-xs rounded"
      >
        Out
      </button>
    </div>
  {/each}
  <select
    bind:value={pickedUpBy}
    on:change={(e) => onPickedUpByChange((e.target as HTMLSelectElement).value)}
    class="mt-1.5 w-full text-xs px-2 py-1 border rounded"
  >
    <option value="">{$_('checkout.pickedUpBy')}</option>
    {#each family.parents as parent}
      <option value={parent.name}>{parent.name}</option>
    {/each}
  </select>
</div>

<!-- Desktop: Table row style -->
<div class="hidden sm:block">
  <!-- Family row -->
  <div class="bg-slate-50 border-b border-slate-200 py-2 px-3 font-semibold text-slate-800 flex items-center justify-between">
    <div class="flex items-center gap-3">
      <span>{family.name} ({family.children.length})</span>
      <button
        on:click={onCheckOutFamily}
        class="px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700"
      >
        {$_('checkout.checkOutAll')}
      </button>
    </div>
    <select
      bind:value={pickedUpBy}
      on:change={(e) => onPickedUpByChange((e.target as HTMLSelectElement).value)}
      class="text-sm px-3 py-1 border border-slate-300 rounded"
    >
      <option value="">{$_('checkout.pickedUpBy')}</option>
      {#each family.parents as parent}
        <option value={parent.name}>{parent.name}</option>
      {/each}
    </select>
  </div>
  <!-- Children rows -->
  {#each family.children as child}
    <div class="bg-white border-b border-slate-100 py-2 px-3 pl-8 flex items-center justify-between hover:bg-slate-50">
      <div class="flex items-center gap-4 flex-1">
        <span class="text-slate-700">{child.firstName} {child.lastName}</span>
        <span class="text-sm text-slate-500">
          {child.checkInTime ? formatTime(child.checkInTime) : ''}
        </span>
      </div>
      <button
        on:click={() => onCheckOut(child.id)}
        class="px-3 py-1 bg-red-500 text-white text-sm rounded hover:bg-red-600"
      >
        {$_('checkout.checkOut')}
      </button>
    </div>
  {/each}
</div>
