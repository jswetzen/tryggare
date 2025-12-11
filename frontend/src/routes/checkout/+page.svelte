<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { t } from 'svelte-i18n';
  import { websocketStore } from '$lib/stores/websocket';
  import { checkInApi, familyApi, sessionApi } from '$lib/api/services';
  import type { CheckInRecord, WebSocketMessage, Family, Session } from '$lib/api/types';

  // Import new components
  import PageHeader from '$lib/components/PageHeader.svelte';
  import SearchBox from '$lib/components/SearchBox.svelte';
  import Alert from '$lib/components/ui/Alert.svelte';
  import { EmptyState, Button, Icon } from '$lib/components/ui';
  import { PageContainer } from '$lib/components/layout';
  import FamilyTable from '$lib/components/domain/FamilyTable.svelte';
  import SessionIndicator from '$lib/components/checkin/SessionIndicator.svelte';
  import SessionSelector from '$lib/components/SessionSelector.svelte';

  let searchQuery = $state('');
  let activeCheckIns = $state<CheckInRecord[]>([]);
  let filteredCheckIns = $state<CheckInRecord[]>([]);
  let loading = $state(false);
  let error = $state<string | null>(null);
  let successMessage = $state<string | null>(null);
  let pickedUpBy = $state<Record<string, string>>({});
  let activeSession = $state<Session | null>(null);
  let activeSessions = $state<Session[]>([]);
  let families = $state<Family[]>([]);
  let showSessionSelector = $state(false);

  let unsubscribe: (() => void) | null = null;

  // Get reference to the websocket state store
  const wsStateStore = websocketStore.state;

  onMount(() => {
    // Connect to WebSocket for real-time updates
    websocketStore.connect();

    // Subscribe to WebSocket messages
    unsubscribe = websocketStore.onMessage(handleWebSocketMessage);

    // Load active session, families, and check-ins
    loadActiveSession();
    loadFamilies();
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

  async function loadActiveSession() {
    try {
      const sessions = await sessionApi.active();
      activeSessions = sessions;
      if (sessions.length > 0) {
        activeSession = sessions[0]; // Use the first active session
      }
    } catch (err) {
      console.error('Failed to load active session:', err);
      // Don't set error state here, as it's not critical for checkout
    }
  }

  async function loadFamilies() {
    try {
      families = await familyApi.list();
    } catch (err) {
      console.error('Failed to load families:', err);
      // Don't set error state here, parents will just be empty
    }
  }

  async function loadActiveCheckIns() {
    loading = true;
    error = null;

    try {
      // Load all active check-ins
      const allCheckIns = await checkInApi.active();

      // Filter by session if one is selected
      if (activeSession) {
        activeCheckIns = allCheckIns.filter(record => record.session === activeSession.id);
      } else {
        activeCheckIns = allCheckIns;
      }

      filterCheckIns();
    } catch (err) {
      console.error('Failed to load active check-ins:', err);
      error = $t('checkout.loadError');
    } finally {
      loading = false;
    }
  }

  function handleChangeSession() {
    showSessionSelector = true;
  }

  function handleSessionSelect(session: Session) {
    activeSession = session;
    showSessionSelector = false;
    loadActiveCheckIns();
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

  async function performFamilyCheckOut(familyId: string) {
    loading = true;
    error = null;
    successMessage = null;

    try {
      // Find all check-in records for this family
      const familyRecords = activeCheckIns.filter(record => {
        const family = families.find(f =>
          f.children.some(c => c.id === record.child)
        );
        return family?.id === familyId;
      });

      // Check out all children in the family
      await Promise.all(
        familyRecords.map(record =>
          checkInApi.checkOut(record.id, pickedUpBy[familyId] || '')
        )
      );

      successMessage = $t('checkout.familySuccess', { values: { count: familyRecords.length } });

      // Clear the picked up by field
      delete pickedUpBy[familyId];

      // Reload active check-ins
      await loadActiveCheckIns();

      // Clear success message after 3 seconds
      setTimeout(() => {
        successMessage = null;
      }, 3000);
    } catch (err) {
      console.error('Family check-out failed:', err);
      error = $t('checkout.familyError');
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
  // Group check-ins by family and include parent data
  const transformedFamilies = $derived.by(() => {
    // Create a map of family ID to family data
    const familyMap = new Map(families.map(f => [f.id, f]));

    // Create a map to group check-ins by family
    const familyCheckIns = new Map<string, CheckInRecord[]>();

    for (const record of filteredCheckIns) {
      // Find the child's family from our families list
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

    // Transform grouped check-ins into family format
    const result = Array.from(familyCheckIns.entries()).map(([familyId, records]) => {
      const family = familyMap.get(familyId);
      if (!family) {
        // Fallback if family not found
        return {
          id: records[0].id,
          name: records[0].child_name,
          last_name: '',
          display_name: records[0].child_name,
          family_name: records[0].child_name,
          primary_contact_name: '',
          primary_contact_phone: '',
          primary_contact_email: '',
          created_at: '',
          updated_at: '',
          children: records.map(record => ({
            ...record,
            id: record.id,
            family: record.child,
            first_name: record.child_name?.split(' ')[0] || '',
            last_name: record.child_name?.split(' ').slice(1).join(' ') || '',
            firstName: record.child_name?.split(' ')[0] || '',
            lastName: record.child_name?.split(' ').slice(1).join(' ') || '',
            checkInTime: record.check_in_time,
            date_of_birth: '',
            created_at: '',
            updated_at: ''
          })),
          parents: []
        };
      }

      // Map check-in records to children
      return {
        id: family.id,
        name: family.display_name,
        last_name: family.last_name,
        display_name: family.display_name,
        family_name: family.last_name,
        primary_contact_name: family.parents[0]?.name || '',
        primary_contact_phone: family.parents[0]?.phone || '',
        primary_contact_email: family.parents[0]?.email || '',
        created_at: '',
        updated_at: '',
        children: records.map(record => {
          const child = family.children.find(c => c.id === record.child);
          return {
            ...record,
            id: record.id,  // Use the CheckInRecord id for checkout operations
            family: record.child,
            first_name: child?.first_name || record.child_name?.split(' ')[0] || '',
            last_name: child?.last_name || record.child_name?.split(' ').slice(1).join(' ') || '',
            firstName: child?.first_name || record.child_name?.split(' ')[0] || '',
            lastName: child?.last_name || record.child_name?.split(' ').slice(1).join(' ') || '',
            checkInTime: record.check_in_time,
            date_of_birth: child?.birthdate || '',
            created_at: '',
            updated_at: ''
          };
        }),
        parents: family.parents.map(p => ({
          name: p.name,
          relationship_type: p.relationship_type
        }))
      };
    });

    return result;
  });
</script>

<svelte:head>
  <title>{$t('checkout.pageTitle')}</title>
</svelte:head>

<div class="min-h-screen bg-slate-100">
  <div class="max-w-4xl mx-auto p-5">
    <PageHeader title={$t('checkout.title')} />

    <!-- Session Indicator -->
    {#if activeSession}
      <SessionIndicator
        eventName={activeSession.event_name || 'No Event'}
        sessionName={activeSession.name || 'No Active Session'}
        sessionTime={activeSession
          ? `${new Date(activeSession.start_time).toLocaleTimeString('en-US', {
              hour: '2-digit',
              minute: '2-digit',
              hour12: false,
            })} - ${activeSession.end_time ? new Date(activeSession.end_time).toLocaleTimeString('en-US', {
              hour: '2-digit',
              minute: '2-digit',
              hour12: false,
            }) : 'Open'}`
          : ''}
        showAddFamily={false}
        showChangeSession={activeSessions.length > 1}
        onChangeSession={handleChangeSession}
      />
    {/if}

    <!-- Session Selector Modal -->
    <SessionSelector
      show={showSessionSelector}
      sessions={activeSessions}
      currentSession={activeSession}
      onSelect={handleSessionSelect}
      onClose={() => showSessionSelector = false}
    />

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
        onToggleFamily={performFamilyCheckOut}
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
