<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { t } from 'svelte-i18n';
  import { websocketStore } from '$lib/stores/websocket';
  import { checkInApi, familyApi } from '$lib/api/services';
  import type { CheckInRecord, WebSocketMessage } from '$lib/api/types';

  // Import new components
  import PageHeader from '$lib/components/PageHeader.svelte';
  import SearchBox from '$lib/components/SearchBox.svelte';
  import TableHeader from '$lib/components/TableHeader.svelte';
  import IconButton from '$lib/components/IconButton.svelte';

  let searchQuery = $state('');
  let activeCheckIns = $state<CheckInRecord[]>([]);
  let filteredCheckIns = $state<CheckInRecord[]>([]);
  let loading = $state(false);
  let error = $state<string | null>(null);
  let successMessage = $state<string | null>(null);
  let pickedUpBy = $state<Record<string, string>>({});

  let unsubscribe: (() => void) | null = null;

  // Get reference to the websocket state store
  const wsStateStore = websocketStore.state;

  onMount(() => {
    // Connect to WebSocket for real-time updates
    websocketStore.connect();

    // Subscribe to WebSocket messages
    unsubscribe = websocketStore.onMessage(handleWebSocketMessage);

    // Load active check-ins
    loadActiveCheckIns();
  });

  onDestroy(() => {
    if (unsubscribe) {
      unsubscribe();
    }
  });

  function handleWebSocketMessage(message: WebSocketMessage) {
    if (message.type === 'child_checked_in' || message.type === 'child_checked_out') {
      // Reload active check-ins when someone checks in or out
      loadActiveCheckIns();
    }
  }

  async function loadActiveCheckIns() {
    loading = true;
    error = null;

    try {
      activeCheckIns = await checkInApi.active();
      filterCheckIns();
    } catch (err) {
      console.error('Failed to load active check-ins:', err);
      error = 'Failed to load checked-in children';
    } finally {
      loading = false;
    }
  }

  function filterCheckIns() {
    if (!searchQuery.trim()) {
      filteredCheckIns = activeCheckIns;
      return;
    }

    const query = searchQuery.toLowerCase();
    filteredCheckIns = activeCheckIns.filter((record) => {
      // This is a simplified filter - you'll need to adjust based on your data structure
      const childName = `${record.child}`.toLowerCase();
      return childName.includes(query);
    });
  }

  $effect(() => {
    // Re-filter when search query or active check-ins change
    filterCheckIns();
  });

  async function performCheckOut(recordId: string) {
    loading = true;
    error = null;
    successMessage = null;

    try {
      await checkInApi.checkOut(recordId, pickedUpBy[recordId] || '');

      successMessage = 'Successfully checked out child';

      // Clear the picked up by field
      delete pickedUpBy[recordId];

      // Reload active check-ins
      await loadActiveCheckIns();

      // Clear success message after 3 seconds
      setTimeout(() => {
        successMessage = null;
      }, 3000);
    } catch (err) {
      console.error('Check-out failed:', err);
      error = 'Check-out failed';
    } finally {
      loading = false;
    }
  }

  // Group check-ins by family (placeholder - you'll need to implement based on your data model)
  interface FamilyGroup {
    familyName: string;
    children: CheckInRecord[];
  }

  let familyGroups = $derived.by(() => {
    // This is a placeholder grouping - adjust based on your actual data structure
    const groups: Map<string, CheckInRecord[]> = new Map();

    for (const record of filteredCheckIns) {
      const familyId = 'family_' + record.child; // Placeholder
      if (!groups.has(familyId)) {
        groups.set(familyId, []);
      }
      groups.get(familyId)!.push(record);
    }

    return Array.from(groups.entries()).map(([familyId, children]): FamilyGroup => ({
      familyName: familyId.replace('family_', 'Family '),
      children,
    }));
  });
</script>

<svelte:head>
  <title>Check-Out Station</title>
</svelte:head>

<div class="max-w-4xl mx-auto">
  <div class="max-w-3xl mx-auto bg-white border-2 border-slate-300 rounded-lg p-5 shadow-lg">
    <PageHeader title="Check-Out Station" />

    <!-- Alerts -->
    {#if error}
      <div class="alert alert-error mb-5">
        {error}
      </div>
    {/if}

    {#if successMessage}
      <div class="alert alert-success mb-5">
        {successMessage}
      </div>
    {/if}

    <SearchBox
      bind:value={searchQuery}
      placeholder="Search by child name or family..."
      label="Search Checked-In Children"
    />

    {#if loading && activeCheckIns.length === 0}
      <div class="text-center p-8 bg-slate-50 border-2 border-dashed border-slate-300 rounded-md">
        <p class="text-slate-500">Loading...</p>
      </div>
    {:else if filteredCheckIns.length === 0}
      <div class="text-center p-8 bg-slate-50 border-2 border-dashed border-slate-300 rounded-md">
        <p class="text-slate-500">
          {searchQuery ? `No checked-in children matching "${searchQuery}"` : 'No children currently checked in'}
        </p>
      </div>
    {:else}
      <TableHeader title="Checked-In Children" count={familyGroups.length} />

      <table class="w-full border-collapse mb-5">
        <thead class="bg-slate-100">
          <tr>
            <th class="text-left p-2 font-semibold text-slate-600 text-sm border-b-2 border-slate-300">
              Family / Child
            </th>
            <th class="text-left p-2 font-semibold text-slate-600 text-sm border-b-2 border-slate-300">
              Checked In
            </th>
            <th class="text-center p-2 font-semibold text-slate-600 text-sm border-b-2 border-slate-300 w-20">
              Check Out
            </th>
          </tr>
        </thead>
        <tbody>
          {#each familyGroups as family, idx}
            {@const bgColor = idx % 2 === 0 ? 'bg-slate-50' : 'bg-slate-100/50'}
            {@const notCheckedOutCount = family.children.length}

            <!-- Family Name Row -->
            <tr class={bgColor}>
              <td class="p-2 font-bold text-blue-900 border-b border-slate-200">
                {family.familyName}
              </td>
              <td class="p-2 border-b border-slate-200"></td>
              <td class="p-2 text-center border-b border-slate-200">
                {#if notCheckedOutCount > 0}
                  <IconButton
                    variant="family-checkout"
                    tooltip="Check out {family.familyName} ({notCheckedOutCount})"
                    onclick={() => {
                      // Check out all children in family
                      for (const child of family.children) {
                        performCheckOut(child.id);
                      }
                    }}
                  />
                {/if}
              </td>
            </tr>

            <!-- Children Rows -->
            {#each family.children as record, childIdx}
              {@const isLastChild = childIdx === family.children.length - 1}

              <tr class={bgColor}>
                <td class="p-2 pl-5 font-medium text-slate-700 text-sm border-b border-slate-200">
                  Child {record.child}
                </td>
                <td class="p-2 border-b border-slate-200">
                  <span class="text-slate-500 text-sm">
                    {new Date(record.check_in_time).toLocaleTimeString()}
                  </span>
                </td>
                <td class="p-2 text-center border-b border-slate-200">
                  <IconButton
                    variant="checkout"
                    tooltip="Check Out"
                    onclick={() => performCheckOut(record.id)}
                    disabled={loading}
                  />
                </td>
              </tr>
            {/each}

            <!-- Pickup By Row -->
            <tr class="{bgColor} border-b-2 border-slate-300">
              <td colspan="3" class="p-2 pb-3">
                <div class="flex items-center gap-2 pl-5">
                  <span class="text-sm text-slate-500 font-semibold">Picked up by:</span>
                  <select
                    bind:value={pickedUpBy[family.children[0]?.id]}
                    class="px-2 py-1 border border-slate-300 rounded text-sm bg-white text-slate-700"
                    disabled={loading}
                  >
                    <option value="">Select...</option>
                    <option value="mom">Mom</option>
                    <option value="dad">Dad</option>
                    <option value="grandma">Grandma</option>
                    <option value="other">Other</option>
                  </select>
                </div>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}

    <div class="mt-4 text-center">
      <button
        onclick={loadActiveCheckIns}
        disabled={loading}
        class="bg-slate-600 hover:bg-slate-700 text-white font-semibold px-5 py-2 rounded-md disabled:opacity-50"
      >
        {loading ? 'Refreshing...' : 'Refresh'}
      </button>
    </div>
  </div>
</div>
