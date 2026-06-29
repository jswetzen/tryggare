<script lang="ts">
  import { onMount } from 'svelte';
  import { checkInApi, familyApi, sessionApi } from '$lib/api/services';
  import type { CheckInRecord, Family, Session } from '$lib/api/types';

  import CheckoutOption1 from '$lib/components/checkout/CheckoutOption1.svelte';
  import CheckoutOption2 from '$lib/components/checkout/CheckoutOption2.svelte';
  import CheckoutOption3 from '$lib/components/checkout/CheckoutOption3.svelte';
  import CheckoutFamilyCard from '$lib/components/checkout/CheckoutFamilyCard.svelte';

  let activeCheckIns = $state<CheckInRecord[]>([]);
  let families = $state<Family[]>([]);
  let pickedUpBy = $state<Record<string, string>>({});
  let loading = $state(true);

  onMount(async () => {
    try {
      const [checkIns, fams] = await Promise.all([
        checkInApi.active(),
        familyApi.list()
      ]);
      activeCheckIns = checkIns;
      families = fams;
    } catch (err) {
      console.error('Failed to load data:', err);
    } finally {
      loading = false;
    }
  });

  function formatTime(isoString: string) {
    return new Date(isoString).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  }

  function noop() {}

  const transformedFamilies = $derived.by(() => {
    const familyMap = new Map(families.map(f => [f.id, f]));
    const familyCheckIns = new Map<string, CheckInRecord[]>();

    for (const record of activeCheckIns) {
      const family = families.find(f =>
        f.children.some(c => c.id === record.child)
      );

      if (family) {
        if (!familyCheckIns.has(family.id)) {
          familyCheckIns.set(family.id, []);
        }
        familyCheckIns.get(family.id)!.push(record);
      }
    }

    return Array.from(familyCheckIns.entries()).map(([familyId, records]) => {
      const family = familyMap.get(familyId)!;
      return {
        id: family.id,
        name: family.display_name,
        last_name: family.last_name,
        display_name: family.display_name,
        children: records.map(record => {
          const child = family.children.find(c => c.id === record.child);
          return {
            ...record,
            id: record.id,
            family: record.child,
            first_name: child?.first_name || record.child_name?.split(' ')[0] || '',
            last_name: child?.last_name || record.child_name?.split(' ').slice(1).join(' ') || '',
            firstName: child?.first_name || record.child_name?.split(' ')[0] || '',
            lastName: child?.last_name || record.child_name?.split(' ').slice(1).join(' ') || '',
            checkInTime: record.check_in_time,
            supervised: record.supervised,
          };
        }),
        parents: family.parents.map(p => ({
          name: p.name,
          relationship_type: p.relationship_type
        }))
      };
    });
  });
</script>

<svelte:head>
  <title>Checkout Design Comparison</title>
</svelte:head>

<div class="min-h-screen bg-neutral-100 p-4">
  <div class="max-w-6xl mx-auto">
    <h1 class="text-3xl font-bold text-primary-900 mb-6">Checkout Design Comparison</h1>

    {#if loading}
      <p class="text-neutral-600">Loading...</p>
    {:else if transformedFamilies.length === 0}
      <p class="text-neutral-600">No checked-in children to display. Go check in some children first!</p>
      <a href="/checkin" class="text-primary-600 hover:underline mt-2 inline-block">Go to Check-In</a>
    {:else}
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">

        <!-- Current Design -->
        <div>
          <div class="bg-primary-100 border-l-4 border-primary-600 p-3 mb-3">
            <h2 class="font-bold text-primary-900">Current Design</h2>
            <p class="text-sm text-primary-800">Spacious cards with full layout</p>
          </div>
          <div class="space-y-3">
            {#each transformedFamilies as family}
              <CheckoutFamilyCard
                {family}
                pickedUpBy={pickedUpBy[family.id] || ''}
                onCheckOut={noop}
                onCheckOutFamily={noop}
                onPickedUpByChange={noop}
                {formatTime}
              />
            {/each}
          </div>
        </div>

        <!-- Option 1 -->
        <div>
          <div class="bg-success-100 border-l-4 border-success-600 p-3 mb-3">
            <h2 class="font-bold text-success-900">Option 1: Compact with Colored Border</h2>
            <p class="text-sm text-success-800">Minimal padding, left border accent</p>
            <p class="text-xs text-success-700 mt-1">Pros: Less vertical space, clear family separation</p>
            <p class="text-xs text-success-700">Cons: Might feel cramped</p>
          </div>
          {#each transformedFamilies as family}
            <CheckoutOption1
              {family}
              pickedUpBy={pickedUpBy[family.id] || ''}
              onCheckOut={noop}
              onCheckOutFamily={noop}
              onPickedUpByChange={noop}
              {formatTime}
            />
          {/each}
        </div>

        <!-- Option 2 -->
        <div>
          <div class="bg-primary-100 border-l-4 border-primary-600 p-3 mb-3">
            <h2 class="font-bold text-primary-900">Option 2: Minimalist Flat List</h2>
            <p class="text-sm text-primary-800">Alternating backgrounds, inline children</p>
            <p class="text-xs text-primary-700 mt-1">Pros: Most compact, fast to scan</p>
            <p class="text-xs text-primary-700">Cons: Less visual hierarchy, children inline</p>
          </div>
          {#each transformedFamilies as family, index}
            <CheckoutOption2
              {family}
              {index}
              pickedUpBy={pickedUpBy[family.id] || ''}
              onCheckOut={noop}
              onCheckOutFamily={noop}
              onPickedUpByChange={noop}
              {formatTime}
            />
          {/each}
        </div>

        <!-- Option 3 -->
        <div>
          <div class="bg-warning-100 border-l-4 border-warning-600 p-3 mb-3">
            <h2 class="font-bold text-warning-900">Option 3: Adaptive Table/Cards</h2>
            <p class="text-sm text-warning-800">Table on desktop, cards on mobile</p>
            <p class="text-xs text-warning-700 mt-1">Pros: Best of both worlds, efficient table</p>
            <p class="text-xs text-warning-700">Cons: Different UX per device</p>
          </div>
          <div class="border border-neutral-300 rounded-card overflow-hidden bg-white">
            {#each transformedFamilies as family}
              <CheckoutOption3
                {family}
                pickedUpBy={pickedUpBy[family.id] || ''}
                onCheckOut={noop}
                onCheckOutFamily={noop}
                onPickedUpByChange={noop}
                {formatTime}
              />
            {/each}
          </div>
        </div>

      </div>
    {/if}
  </div>
</div>
