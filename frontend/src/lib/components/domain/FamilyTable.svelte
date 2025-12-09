<script lang="ts">
  import type { Family, Child } from '$lib/api/types';
  import IconButton from '../IconButton.svelte';
  import TicketBadge from '../TicketBadge.svelte';
  import { t } from 'svelte-i18n';

  // Extended types for display purposes
  interface DisplayChild extends Child {
    firstName: string;
    lastName: string;
    ticketType?: 'event' | 'session' | 'none';
    checkInTime?: string;
  }

  interface DisplayFamily extends Omit<Family, 'children'> {
    name: string;
    children?: DisplayChild[];
    parents?: Array<{
      firstName: string;
      lastName: string;
      relationshipType: string;
    }>;
  }

  interface Props {
    families: DisplayFamily[];
    selectedChildren?: string[];
    mode: 'checkin' | 'checkout';
    onToggleChild?: (childId: string) => void;
    onToggleFamily?: (familyId: string) => void;
    onCheckOut?: (childId: string) => void;
    isChildDisabled?: (child: DisplayChild) => boolean;
    formatTime?: (isoString: string) => string;
    pickedUpBy?: Record<string, string>;
    onPickedUpByChange?: (familyId: string, value: string) => void;
  }

  let {
    families,
    selectedChildren = [],
    mode,
    onToggleChild,
    onToggleFamily,
    onCheckOut,
    isChildDisabled,
    formatTime = (iso) => new Date(iso).toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit'
    }),
    pickedUpBy = {},
    onPickedUpByChange
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
              {#if mode === 'checkin' && onToggleChild}
                <IconButton
                  variant={isDisabled ? 'checked-in' : 'checkin'}
                  tooltip={isDisabled ? $t('checkin.alreadyCheckedIn') : $t('checkin.checkIn')}
                  onclick={() => onToggleChild(child.id)}
                  disabled={isDisabled}
                />
              {:else if mode === 'checkout' && onCheckOut}
                <IconButton
                  variant="checkout"
                  tooltip={$t('checkout.checkOut')}
                  onclick={() => onCheckOut(child.id)}
                  disabled={isDisabled}
                />
              {/if}
            </td>
          </tr>
        {/each}

        <!-- Pickup row for checkout mode -->
        {#if mode === 'checkout' && onPickedUpByChange}
          <tr class="{bgColor} border-b-2 border-neutral-300">
            <td colspan="3" class="p-3">
              <label class="flex items-center gap-3">
                <span class="text-sm font-semibold text-neutral-700 whitespace-nowrap">
                  {$t('checkout.pickedUpBy')}:
                </span>
                <select
                  bind:value={pickedUpBy[family.id]}
                  onchange={(e) => onPickedUpByChange?.(family.id, (e.target as HTMLSelectElement).value)}
                  class="px-2 py-1 border border-neutral-300 rounded-input text-sm bg-white text-neutral-700 flex-1"
                >
                  <option value="">{$t('checkout.selectPerson')}</option>
                  {#each family.parents || [] as parent}
                    <option value="{parent.firstName} {parent.lastName}">
                      {parent.firstName} {parent.lastName} ({parent.relationshipType})
                    </option>
                  {/each}
                </select>
              </label>
            </td>
          </tr>
        {/if}
      {/each}
    </tbody>
  </table>
</div>
