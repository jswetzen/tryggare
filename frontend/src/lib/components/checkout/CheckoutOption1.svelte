<script lang="ts">
  /**
   * Option 1: Ultra-Compact Cards with Colored Left Border
   * Family name inline with children, minimal padding
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

<div class="bg-white border-l-4 border-blue-600 rounded-r shadow-sm mb-2 p-2">
  <!-- Family header inline -->
  <div class="flex items-center justify-between mb-1">
    <h4 class="font-bold text-slate-800 text-sm">
      {family.name} ({family.children.length})
    </h4>
    <button
      type="button"
      on:click={onCheckOutFamily}
      class="px-2 py-1 bg-red-600 text-white text-xs font-semibold rounded-button hover:bg-red-700"
    >
      {$_('checkout.checkOutAll')}
    </button>
  </div>

  <!-- Children - very compact -->
  {#each family.children as child}
    <div class="flex items-center justify-between py-1 border-t border-slate-100">
      <div class="flex-1 text-sm">
        <span class="text-slate-700">{child.firstName} {child.lastName}</span>
        <span class="text-slate-500 text-xs ml-2">
          {child.checkInTime ? formatTime(child.checkInTime) : ''}
        </span>
      </div>
      <button
        on:click={() => onCheckOut(child.id)}
        class="px-2 py-0.5 bg-red-500 text-white text-xs rounded-button hover:bg-red-600"
      >
        {$_('checkout.checkOut')}
      </button>
    </div>
  {/each}

  <!-- Pickup selector inline -->
  <div class="flex items-center gap-2 mt-1 pt-1 border-t border-slate-200">
    <span class="text-xs text-slate-600 whitespace-nowrap">{$_('checkout.pickedUpBy')}:</span>
    <select
      bind:value={pickedUpBy}
      on:change={(e) => onPickedUpByChange((e.target as HTMLSelectElement).value)}
      class="text-xs px-2 py-0.5 border border-slate-300 rounded flex-1 bg-white"
    >
      <option value="">{$_('checkout.selectPerson')}</option>
      {#each family.parents as parent}
        <option value={parent.name}>{parent.name}</option>
      {/each}
    </select>
  </div>
</div>
