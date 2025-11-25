<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { websocketStore } from '$lib/stores/websocket';
  import { checkInApi } from '$lib/api/services';
  import type { CheckInRecord, WebSocketMessage } from '$lib/api/types';

  let activeCheckIns = $state<CheckInRecord[]>([]);
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
    } catch (err) {
      console.error('Failed to load active check-ins:', err);
      error = 'Failed to load active check-ins';
    } finally {
      loading = false;
    }
  }

  async function performCheckOut(recordId: string) {
    loading = true;
    error = null;
    successMessage = null;

    try {
      await checkInApi.checkOut(recordId, pickedUpBy[recordId] || '');

      successMessage = 'Successfully checked out';

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
</script>

<svelte:head>
  <title>Check-Out Station</title>
</svelte:head>

<main class="container mx-auto p-6">
  <h1 class="text-3xl font-bold mb-6">Check-Out Station</h1>

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

  <div class="card">
    <h2 class="text-xl font-semibold mb-4">Currently Checked In</h2>

    {#if loading && activeCheckIns.length === 0}
      <div class="text-center py-8">
        <div class="text-gray-600">Loading...</div>
      </div>
    {:else if activeCheckIns.length === 0}
      <div class="text-center py-8">
        <div class="text-gray-600">No children currently checked in.</div>
      </div>
    {:else}
      <div class="space-y-4">
        {#each activeCheckIns as record}
          <div class="border rounded-lg p-4">
            <div class="flex items-start justify-between gap-4">
              <div class="flex-1">
                <div class="font-semibold text-lg">Child ID: {record.child}</div>
                <div class="text-sm text-gray-600 mt-1">
                  Session: {record.session}
                </div>
                <div class="text-sm text-gray-600">
                  Checked in: {new Date(record.check_in_time).toLocaleString()}
                </div>
                {#if record.notes}
                  <div class="text-sm text-gray-600 mt-2">
                    Notes: {record.notes}
                  </div>
                {/if}
              </div>

              <div class="flex flex-col gap-2 min-w-[200px]">
                <input
                  type="text"
                  bind:value={pickedUpBy[record.id]}
                  placeholder="Picked up by..."
                  class="form-input text-sm"
                  disabled={loading}
                />
                <button
                  onclick={() => performCheckOut(record.id)}
                  disabled={loading}
                  class="btn btn-primary btn-sm"
                >
                  {loading ? 'Checking out...' : 'Check Out'}
                </button>
              </div>
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </div>

  <div class="mt-4 text-center">
    <button onclick={loadActiveCheckIns} disabled={loading} class="btn btn-secondary">
      {loading ? 'Refreshing...' : 'Refresh'}
    </button>
  </div>
</main>
