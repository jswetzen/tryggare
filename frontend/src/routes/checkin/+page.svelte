<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { websocketStore } from '$lib/stores/websocket';
  import { familyApi, childApi, sessionApi, checkInApi } from '$lib/api/services';
  import type { Family, Child, Session, WebSocketMessage } from '$lib/api/types';

  let searchQuery = $state('');
  let families = $state<Family[]>([]);
  let selectedFamily = $state<Family | null>(null);
  let children = $state<Child[]>([]);
  let selectedChildren = $state<string[]>([]);
  let sessions = $state<Session[]>([]);
  let selectedSession = $state<string | null>(null);
  let loading = $state(false);
  let error = $state<string | null>(null);
  let successMessage = $state<string | null>(null);

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
      // Show notification or update UI
      console.log('Child checked in:', message.data);
    }
  }

  async function loadSessions() {
    try {
      sessions = await sessionApi.active();
    } catch (err) {
      console.error('Failed to load sessions:', err);
      error = 'Failed to load sessions';
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
      families = await familyApi.search(searchQuery);
    } catch (err) {
      console.error('Search failed:', err);
      error = 'Search failed';
      families = [];
    } finally {
      loading = false;
    }
  }

  async function selectFamily(family: Family) {
    selectedFamily = family;
    selectedChildren = [];
    loading = true;
    error = null;

    try {
      children = await childApi.list(family.id);
    } catch (err) {
      console.error('Failed to load children:', err);
      error = 'Failed to load children';
      children = [];
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

  async function performCheckIn() {
    if (!selectedSession || selectedChildren.length === 0) {
      error = 'Please select a session and at least one child';
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

      successMessage = `Successfully checked in ${selectedChildren.length} child(ren)`;

      // Reset selection
      selectedChildren = [];
      selectedFamily = null;
      children = [];
      searchQuery = '';
      families = [];

      // Clear success message after 3 seconds
      setTimeout(() => {
        successMessage = null;
      }, 3000);
    } catch (err) {
      console.error('Check-in failed:', err);
      error = 'Check-in failed';
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head>
  <title>Check-In Station</title>
</svelte:head>

<main class="container mx-auto p-6">
  <h1 class="text-3xl font-bold mb-6">Check-In Station</h1>

  <div class="card mb-6">
    <h2 class="text-xl font-semibold mb-4">WebSocket Status</h2>
    <div class="flex items-center gap-2">
      <div
        class="w-3 h-3 rounded-full {$wsStateStore.connected
          ? 'bg-green-500'
          : 'bg-red-500'}"
      ></div>
      <span>
        {$wsStateStore.connected ? 'Connected' : 'Disconnected'}
      </span>
    </div>
  </div>

  {#if error}
    <div class="alert alert-error mb-6">
      {error}
    </div>
  {/if}

  {#if successMessage}
    <div class="alert alert-success mb-6">
      {successMessage}
    </div>
  {/if}

  <!-- Session Selection -->
  <div class="card mb-6">
    <h2 class="text-xl font-semibold mb-4">Select Session</h2>
    <select
      bind:value={selectedSession}
      class="form-select w-full"
      disabled={loading}
    >
      <option value={null}>-- Select a session --</option>
      {#each sessions as session}
        <option value={session.id}>{session.name}</option>
      {/each}
    </select>
  </div>

  <!-- Family Search -->
  <div class="card mb-6">
    <h2 class="text-xl font-semibold mb-4">Search Family</h2>
    <div class="flex gap-2">
      <input
        type="text"
        bind:value={searchQuery}
        onkeydown={(e) => e.key === 'Enter' && searchFamilies()}
        placeholder="Search by family name, email, or phone..."
        class="form-input flex-1"
        disabled={loading}
      />
      <button
        onclick={searchFamilies}
        class="btn btn-primary"
        disabled={loading}
      >
        Search
      </button>
    </div>

    {#if families.length > 0}
      <div class="mt-4 space-y-2">
        {#each families as family}
          <button
            onclick={() => selectFamily(family)}
            class="w-full text-left p-4 border rounded hover:bg-gray-50 {selectedFamily?.id ===
            family.id
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-300'}"
          >
            <div class="font-semibold">{family.family_name}</div>
            <div class="text-sm text-gray-600">
              {family.primary_contact_name} - {family.primary_contact_phone}
            </div>
          </button>
        {/each}
      </div>
    {/if}
  </div>

  <!-- Child Selection -->
  {#if selectedFamily}
    <div class="card mb-6">
      <h2 class="text-xl font-semibold mb-4">Select Children</h2>
      {#if children.length === 0}
        <p class="text-gray-600">No children found for this family.</p>
      {:else}
        <div class="space-y-2">
          {#each children as child}
            <label class="flex items-center gap-3 p-3 border rounded cursor-pointer hover:bg-gray-50">
              <input
                type="checkbox"
                checked={selectedChildren.includes(child.id)}
                onchange={() => toggleChild(child.id)}
                class="form-checkbox"
              />
              <div class="flex-1">
                <div class="font-semibold">
                  {child.first_name}
                  {child.last_name}
                </div>
                {#if child.date_of_birth}
                  <div class="text-sm text-gray-600">
                    DOB: {child.date_of_birth}
                  </div>
                {/if}
              </div>
            </label>
          {/each}
        </div>
      {/if}
    </div>

    <!-- Check-In Button -->
    <div class="flex justify-end">
      <button
        onclick={performCheckIn}
        disabled={loading || !selectedSession || selectedChildren.length === 0}
        class="btn btn-primary btn-lg"
      >
        {loading ? 'Checking in...' : `Check In ${selectedChildren.length} Child(ren)`}
      </button>
    </div>
  {/if}
</main>
