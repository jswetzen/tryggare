<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { t } from 'svelte-i18n';
  import { websocketStore } from '$lib/stores/websocket';
  import { checkInApi, familyApi } from '$lib/api/services';
  import type { CheckInRecord, WebSocketMessage } from '$lib/api/types';

  // Import new components
  import PageHeader from '$lib/components/PageHeader.svelte';
  import SearchBox from '$lib/components/SearchBox.svelte';
  import Alert from '$lib/components/ui/Alert.svelte';
  import { EmptyState, Button, Icon } from '$lib/components/ui';
  import { PageContainer } from '$lib/components/layout';
  import FamilyTable from '$lib/components/domain/FamilyTable.svelte';

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
      error = $t('checkout.loadError');
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
      const childName = record.child_name?.toLowerCase() || '';
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

      successMessage = $t('checkout.success');

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
      error = $t('checkout.error');
    } finally {
      loading = false;
    }
  }

  // Helper function to format time
  function formatTime(isoString: string) {
    return new Date(isoString).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  }

  // Transform check-ins to match FamilyTable's expected format
  // Each check-in record is treated as a separate "family" since we don't have family grouping data
  const transformedFamilies = $derived(
    filteredCheckIns.map((record) => ({
      id: record.id,
      name: record.child_name,
      family_name: record.child_name,
      primary_contact_name: '',
      primary_contact_phone: '',
      primary_contact_email: '',
      created_at: '',
      updated_at: '',
      children: [{
        ...record,
        id: record.id,  // Use the CheckInRecord id
        family: record.child,
        first_name: record.child_name?.split(' ')[0] || '',
        last_name: record.child_name?.split(' ').slice(1).join(' ') || '',
        firstName: record.child_name?.split(' ')[0] || '',
        lastName: record.child_name?.split(' ').slice(1).join(' ') || '',
        checkInTime: record.check_in_time,
        date_of_birth: '',
        created_at: '',
        updated_at: ''
      }],
      parents: []
    }))
  );
</script>

<svelte:head>
  <title>{$t('checkout.pageTitle')}</title>
</svelte:head>

<div class="max-w-4xl mx-auto">
  <div class="max-w-3xl mx-auto bg-white border-2 border-neutral-300 rounded-card p-5 shadow-lg">
    <PageHeader title={$t('checkout.title')} />

    <!-- Alerts -->
    {#if error}
      <Alert type="error" dismissible ondismiss={() => error = null} class="mb-4">
        {error}
      </Alert>
    {/if}

    {#if successMessage}
      <Alert type="success" dismissible ondismiss={() => successMessage = null} class="mb-4">
        {successMessage}
      </Alert>
    {/if}

    <SearchBox
      bind:value={searchQuery}
      placeholder={$t('checkout.searchPlaceholder')}
      label={$t('checkout.searchLabel')}
    />

    {#if loading && activeCheckIns.length === 0}
      <EmptyState
        type="loading"
        title={$t('checkout.loading')}
      />
    {/if}

    {#if !loading && filteredCheckIns.length === 0}
      <EmptyState
        type="empty"
        title={searchQuery ? $t('checkout.noChildrenFiltered', { values: { query: searchQuery } }) : $t('checkout.noChildren')}
        description={$t('checkout.noChildrenDescription')}
      >
        {#snippet icon()}
          <Icon name="check-circle" size="xl" />
        {/snippet}
      </EmptyState>
    {/if}

    {#if filteredCheckIns.length > 0 && !loading}
      <FamilyTable
        families={transformedFamilies}
        mode="checkout"
        onCheckOut={performCheckOut}
        formatTime={formatTime}
        bind:pickedUpBy={pickedUpBy}
        onPickedUpByChange={(familyId, value) => {
          pickedUpBy = { ...pickedUpBy, [familyId]: value };
        }}
      />
    {/if}

    <div class="mt-6 flex justify-end">
      <Button variant="ghost" onclick={loadActiveCheckIns} disabled={loading}>
        <Icon name="refresh" size="sm" class="mr-2" />
        {$t('common.refresh')}
      </Button>
    </div>
  </div>
</div>
