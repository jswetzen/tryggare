<script lang="ts">
  /**
   * Option 2: Minimalist List with Background Shading
   * No borders, alternating backgrounds, ultra-flat
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
    formatTime,
    index = 0
  }: {
    family: Family;
    pickedUpBy: string;
    onCheckOut: (childId: string) => void;
    onCheckOutFamily: () => void;
    onPickedUpByChange: (value: string) => void;
    formatTime: (isoString: string) => string;
    index?: number;
  } = $props();

  const bgColor = $derived(index % 2 === 0 ? 'bg-white' : 'bg-slate-50');
</script>

<div class="{bgColor} py-1.5 px-2">
  <!-- Family header - minimal -->
  <div class="flex items-center justify-between mb-1">
    <div class="flex items-center gap-2">
      <span class="font-semibold text-slate-800 text-sm">{family.name}</span>
      <span class="text-xs text-slate-500">({family.children.length})</span>
      <button
        type="button"
        on:click={onCheckOutFamily}
        class="text-xs text-red-600 hover:text-red-700 font-medium underline"
      >
        {$_('checkout.checkOutAll')}
      </button>
    </div>
    <select
      bind:value={pickedUpBy}
      on:change={(e) => onPickedUpByChange((e.target as HTMLSelectElement).value)}
      class="text-xs px-2 py-0.5 border border-slate-300 rounded bg-white"
    >
      <option value="">{$_('checkout.pickedUpBy')}: {$_('checkout.selectPerson')}</option>
      {#each family.parents as parent}
        <option value={parent.name}>{parent.name}</option>
      {/each}
    </select>
  </div>

  <!-- Children - ultra compact, inline -->
  <div class="flex flex-wrap gap-x-4 gap-y-1 pl-2">
    {#each family.children as child}
      <div class="flex items-center gap-2 text-sm">
        <span class="text-slate-700">{child.firstName} {child.lastName}</span>
        <span class="text-slate-400 text-xs">
          {child.checkInTime ? formatTime(child.checkInTime) : ''}
        </span>
        <button
          on:click={() => onCheckOut(child.id)}
          class="text-xs text-red-600 hover:text-red-700 font-medium"
        >
          ✕
        </button>
      </div>
    {/each}
  </div>
</div>
