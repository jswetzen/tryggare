<script lang="ts">
  /**
   * CheckoutFamilyCard Component
   *
   * Displays a family with checked-in children for checkout.
   * Optimized for mobile with a card-based layout instead of table.
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

  const childCount = $derived(family.children.length);
</script>

<div
  class="bg-white border border-slate-300 rounded-card overflow-hidden mb-3 hover:shadow-md transition-shadow"
  data-testid={`checkout-family-card-${family.id}`}
>
  <!-- Family Header -->
  <div class="bg-slate-50 p-2.5 sm:p-3 border-b border-slate-200">
    <div class="flex items-center justify-between gap-2">
      <div class="flex-1 min-w-0">
        <h3 class="font-bold text-blue-900 text-base sm:text-lg">
          {family.name}
        </h3>
        <p class="text-xs sm:text-sm text-slate-600 mt-0.5">
          {$_('checkin.checkedInCount', { values: { count: childCount } })}
        </p>
      </div>

      <button
        type="button"
        on:click={onCheckOutFamily}
        class="px-3 py-1.5 sm:px-4 sm:py-2 bg-red-600 text-white font-semibold rounded-button hover:bg-red-700 transition-colors text-xs sm:text-sm whitespace-nowrap"
        aria-label={`Check out all children from ${family.name}`}
        data-testid={`family-checkout-button-${family.id}`}
      >
        {$_('checkout.checkOutAll')}
      </button>
    </div>
  </div>

  <!-- Children List -->
  <div class="p-2 sm:p-3 space-y-2">
    {#each family.children as child (child.id)}
      <div
        class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-2 bg-slate-50 rounded border border-slate-200"
        data-testid={`child-checkout-row-${child.id}`}
      >
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2 flex-wrap">
            <span class="font-medium text-slate-700 text-sm sm:text-base">
              {child.firstName} {child.lastName}
            </span>
            {#if child.supervised}
              <span class="px-1.5 py-0.5 text-xs font-semibold bg-blue-100 text-blue-800 rounded">
                {$_('checkout.supervised')}
              </span>
            {/if}
          </div>
          {#if child.checkInTime}
            <div class="text-xs text-slate-500 mt-0.5">
              {$_('checkin.checkedInAt', { values: { time: formatTime(child.checkInTime) } })}
            </div>
          {/if}
        </div>

        <button
          type="button"
          on:click={() => onCheckOut(child.id)}
          class="px-3 py-1.5 bg-red-600 text-white font-semibold rounded-button hover:bg-red-700 transition-colors text-xs sm:text-sm whitespace-nowrap self-start sm:self-center"
          aria-label={`Check out ${child.firstName} ${child.lastName}`}
          data-testid={`child-checkout-button-${child.id}`}
        >
          {$_('checkout.checkOut')}
        </button>
      </div>
    {/each}
  </div>

  <!-- Picked Up By Selector -->
  <div class="p-2.5 sm:p-3 bg-slate-50 border-t border-slate-200">
    <label class="flex flex-col sm:flex-row sm:items-center gap-2">
      <span class="text-sm font-semibold text-slate-700 whitespace-nowrap">
        {$_('checkout.pickedUpBy')}:
      </span>
      <select
        bind:value={pickedUpBy}
        on:change={(e) => onPickedUpByChange((e.target as HTMLSelectElement).value)}
        class="px-3 py-1.5 border border-slate-300 rounded-input text-sm bg-white text-slate-700 flex-1 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        data-testid={`picked-up-by-${family.id}`}
      >
        <option value="">{$_('checkout.selectPerson')}</option>
        {#each family.parents as parent}
          <option value={parent.name}>
            {parent.name} ({parent.relationship_type})
          </option>
        {/each}
      </select>
    </label>
  </div>
</div>
