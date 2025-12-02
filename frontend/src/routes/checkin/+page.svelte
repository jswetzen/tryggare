<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { t } from 'svelte-i18n';
  import { websocketStore } from '$lib/stores/websocket';
  import { familyApi, childApi, sessionApi, checkInApi } from '$lib/api/services';
  import type { Family, Child, Session, WebSocketMessage } from '$lib/api/types';

  // Import new components
  import PageHeader from '$lib/components/PageHeader.svelte';
  import SearchBox from '$lib/components/SearchBox.svelte';
  import TableHeader from '$lib/components/TableHeader.svelte';
  import TicketBadge from '$lib/components/TicketBadge.svelte';
  import IconButton from '$lib/components/IconButton.svelte';
  import AddFamilyModal from '$lib/components/AddFamilyModal.svelte';

  let searchQuery = $state('');
  let families = $state<Family[]>([]);
  let children = $state<Child[]>([]);
  let selectedChildren = $state<string[]>([]);
  let sessions = $state<Session[]>([]);
  let selectedSession = $state<string | null>(null);
  let loading = $state(false);
  let error = $state<string | null>(null);
  let successMessage = $state<string | null>(null);
  let showAddFamilyModal = $state(false);

  let unsubscribe: (() => void) | null = null;

  // Get reference to the websocket state store
  const wsStateStore = websocketStore.state;

  onMount(() => {
    // Connect to WebSocket for real-time updates
    websocketStore.connect();

    // Subscribe to WebSocket messages
    unsubscribe = websocketStore.onMessage(handleWebSocketMessage);

    // Load active sessions
    loadSessions();
  });

  onDestroy(() => {
    if (unsubscribe) {
      unsubscribe();
    }
  });

  function handleWebSocketMessage(message: WebSocketMessage) {
    if (message.type === 'child_checked_in') {
      console.log('Child checked in:', message.data);
      // Refresh the data
      if (families.length > 0) {
        searchFamilies();
      }
    }
  }

  async function loadSessions() {
    try {
      sessions = await sessionApi.active();
      // Auto-select first session if only one
      if (sessions.length === 1) {
        selectedSession = sessions[0].id;
      }
    } catch (err) {
      console.error('Failed to load sessions:', err);
      error = $t('checkin.sessionsError');
    }
  }

  async function searchFamilies() {
    if (!searchQuery.trim()) {
      families = [];
      return;
    }

    loading = true;
    error = null;

    try {
      const results = await familyApi.search(searchQuery);
      families = results;

      // Load children for all families
      for (const family of families) {
        const familyChildren = await childApi.list(family.id);
        family.children = familyChildren;
      }
    } catch (err) {
      console.error('Search failed:', err);
      error = $t('checkin.searchError');
      families = [];
    } finally {
      loading = false;
    }
  }

  function toggleChild(childId: string) {
    if (selectedChildren.includes(childId)) {
      selectedChildren = selectedChildren.filter((id) => id !== childId);
    } else {
      selectedChildren = [...selectedChildren, childId];
    }
  }

  function toggleFamily(family: Family) {
    const familyChildIds = (family.children || []).map((c: Child) => c.id);
    const allSelected = familyChildIds.every((id: string) => selectedChildren.includes(id));

    if (allSelected) {
      // Deselect all
      selectedChildren = selectedChildren.filter((id) => !familyChildIds.includes(id));
    } else {
      // Select all unchecked children
      const toAdd = familyChildIds.filter((id: string) => !selectedChildren.includes(id));
      selectedChildren = [...selectedChildren, ...toAdd];
    }
  }

  async function performCheckIn() {
    if (!selectedSession || selectedChildren.length === 0) {
      error = $t('checkin.selectError');
      return;
    }

    loading = true;
    error = null;
    successMessage = null;

    try {
      for (const childId of selectedChildren) {
        await checkInApi.checkIn({
          child: childId,
          session: selectedSession,
        });
      }

      successMessage = `${$t('checkin.checkIn')} ${selectedChildren.length} ${selectedChildren.length === 1 ? $t('checkin.child') : $t('checkin.children')}`;

      // Reset selection
      selectedChildren = [];
      searchQuery = '';
      families = [];

      // Clear success message after 5 seconds
      setTimeout(() => {
        successMessage = null;
      }, 5000);
    } catch (err: any) {
      console.error('Check-in failed:', err);
      error = err.message || $t('checkin.error');
    } finally {
      loading = false;
    }
  }

  // Get ticket type for a child (placeholder - you'll need to implement based on your data model)
  function getTicketType(child: Child): 'event' | 'session' | 'none' {
    // This is a placeholder - adjust based on your actual data structure
    return 'event'; // or 'session' or 'none'
  }

  // Check if child is already checked in
  function isCheckedIn(child: Child): boolean {
    // This is a placeholder - adjust based on your actual data structure
    return false;
  }
</script>

<svelte:head>
  <title>{$t('checkin.pageTitle')}</title>
</svelte:head>

<div class="max-w-4xl mx-auto">
  <div class="max-w-3xl mx-auto bg-white border-2 border-slate-300 rounded-lg p-5 shadow-lg">
    <PageHeader title={$t('checkin.title')} />

    <!-- Alerts -->
    {#if error}
      <div data-testid="error-alert" class="alert alert-error mb-5">
        {error}
      </div>
    {/if}

    {#if successMessage}
      <div data-testid="success-alert" class="alert alert-success mb-5">
        {successMessage}
      </div>
    {/if}

    <!-- Session Selection (only show if multiple sessions) -->
    {#if sessions.length > 1}
      <div class="border-2 border-blue-500 rounded-md p-3 mb-5 bg-blue-50">
        <label for="session-select" class="block font-semibold text-blue-900 mb-2 text-sm">
          {$t('checkin.selectSession')}
        </label>
        <select
          id="session-select"
          data-testid="session-select"
          bind:value={selectedSession}
          class="w-full px-3 py-2 border border-slate-300 rounded bg-white text-sm"
          disabled={loading}
        >
          <option value={null}>{$t('checkin.selectSessionPlaceholder')}</option>
          {#each sessions as session}
            <option value={session.id}>{session.name}</option>
          {/each}
        </select>
      </div>
    {/if}

    <SearchBox
      bind:value={searchQuery}
      placeholder={$t('checkin.searchPlaceholder')}
      label={$t('checkin.searchFamily')}
    />

    <div class="flex justify-end mb-4">
      <button
        data-testid="search-button"
        onclick={searchFamilies}
        class="btn btn-primary"
        disabled={loading || !searchQuery.trim()}
      >
        {loading ? $t('checkin.searchButton') + '...' : $t('checkin.searchButton')}
      </button>
    </div>

    {#if loading && families.length === 0}
      <div class="text-center p-8 bg-slate-50 border-2 border-dashed border-slate-300 rounded-md">
        <p class="text-slate-500">{$t('checkin.searching')}</p>
      </div>
    {:else if families.length === 0 && searchQuery}
      <div class="text-center p-8 bg-slate-50 border-2 border-dashed border-slate-300 rounded-md">
        <p class="text-slate-500 mb-3">{$t('checkin.noFamiliesFound', { values: { query: searchQuery } })}</p>
        <button
          class="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-5 py-2 rounded"
          onclick={() => showAddFamilyModal = true}
        >
          {$t('checkin.addNewFamily')}
        </button>
      </div>
    {:else if families.length > 0}
      <TableHeader title={$t('checkin.registeredFamilies')} count={families.length} />

      <table class="w-full border-collapse mb-5">
        <thead class="bg-slate-100">
          <tr>
            <th class="text-left p-2 font-semibold text-slate-600 text-sm border-b-2 border-slate-300">
              {$t('checkin.familyChild')}
            </th>
            <th class="text-left p-2 font-semibold text-slate-600 text-sm border-b-2 border-slate-300">
              {$t('checkin.ticket')}
            </th>
            <th class="text-center p-2 font-semibold text-slate-600 text-sm border-b-2 border-slate-300 w-20">
              {$t('checkin.checkIn')}
            </th>
          </tr>
        </thead>
        <tbody>
          {#each families as family, idx}
            {@const bgColor = idx % 2 === 0 ? 'bg-slate-50' : 'bg-slate-100/50'}
            {@const familyChildren = family.children || []}
            {@const uncheckedCount = familyChildren.filter((c: Child) => !isCheckedIn(c) && !selectedChildren.includes(c.id)).length}

            <!-- Family Name Row -->
            <tr class={bgColor}>
              <td class="p-2 font-bold text-blue-900 border-b border-slate-200">
                {family.family_name || `${family.primary_contact_name}'s Family`}
              </td>
              <td class="p-2 border-b border-slate-200"></td>
              <td class="p-2 text-center border-b border-slate-200">
                {#if uncheckedCount > 0}
                  <IconButton
                    variant="family-checkin"
                    tooltip={$t('checkin.checkInFamily', { values: { family: family.family_name || 'family', count: uncheckedCount } })}
                    onclick={() => toggleFamily(family)}
                  />
                {/if}
              </td>
            </tr>

            <!-- Children Rows -->
            {#each familyChildren as child, childIdx}
              {@const isLastChild = childIdx === familyChildren.length - 1}
              {@const checkedIn = isCheckedIn(child)}
              {@const isSelected = selectedChildren.includes(child.id)}

              <tr class={bgColor}>
                <td class="p-2 pl-5 font-medium text-slate-700 text-sm {isLastChild ? 'border-b-2 border-slate-300' : 'border-b border-slate-200'}">
                  {child.first_name} {child.last_name}
                </td>
                <td class="p-2 {isLastChild ? 'border-b-2 border-slate-300' : 'border-b border-slate-200'}">
                  <TicketBadge type={getTicketType(child)} />
                </td>
                <td class="p-2 text-center {isLastChild ? 'border-b-2 border-slate-300' : 'border-b border-slate-200'}">
                  <IconButton
                    variant={checkedIn ? 'checked-in' : (isSelected ? 'checked-in' : 'checkin')}
                    tooltip={checkedIn ? $t('checkin.alreadyCheckedIn') : (isSelected ? $t('checkin.selected') : $t('checkin.checkIn'))}
                    onclick={() => !checkedIn && toggleChild(child.id)}
                    disabled={checkedIn}
                  />
                </td>
              </tr>
            {/each}
          {/each}
        </tbody>
      </table>

      <!-- Check-In Button -->
      {#if selectedChildren.length > 0}
        <div class="flex justify-end">
          <button
            data-testid="main-checkin-button"
            onclick={performCheckIn}
            class="bg-green-600 hover:bg-green-700 text-white font-semibold px-6 py-3 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={loading || !selectedSession}
          >
            {loading ? $t('checkin.checkingIn') : `${$t('checkin.checkIn')} ${selectedChildren.length} ${selectedChildren.length === 1 ? $t('checkin.child') : $t('checkin.children')}`}
          </button>
        </div>
      {/if}
    {:else}
      <div class="text-center p-8 bg-slate-50 border-2 border-dashed border-slate-300 rounded-md">
        <p class="text-slate-500 mb-3">{$t('checkin.getStarted')}</p>
      </div>
    {/if}
  </div>
</div>

<!-- Add Family Modal -->
<AddFamilyModal
  bind:show={showAddFamilyModal}
  onClose={() => showAddFamilyModal = false}
  onSuccess={async () => {
    successMessage = $t('checkin.createSuccess');
    // Refresh the search to show the new family
    if (searchQuery) {
      await searchFamilies();
    }
  }}
/>
