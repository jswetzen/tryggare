<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { t } from 'svelte-i18n';
  import { websocketStore } from '$lib/stores/websocket';
  import { checkInApi, familyApi, sessionApi } from '$lib/api/services';
  import type { CheckInRecord, WebSocketMessage, Family, Session } from '$lib/api/types';

  // Import new components
  import SearchBox from '$lib/components/SearchBox.svelte';
  import Alert from '$lib/components/ui/Alert.svelte';
  import SuccessToast from '$lib/components/checkin/SuccessToast.svelte';
  import { EmptyState, Button, Icon } from '$lib/components/ui';
  import CheckoutExpandableTable from '$lib/components/checkout/CheckoutExpandableTable.svelte';
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

  // Track recently checked-out records to prevent self-triggered WebSocket updates
  let recentlyCheckedOutRecords = $state<Set<string>>(new Set());

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
    // Check if message matches active session filter
    const matchesSession = !activeSession || message.data?.session_id === activeSession.id;

    if (message.type === 'child_checked_in') {
      // Skip if doesn't match current session filter
      if (!matchesSession) return;

      // Add new check-in to list
      const data = message.data;
      const newRecord: CheckInRecord = {
        id: data.record_id,
        child: data.child_id,
        child_name: `${data.child_name} ${data.child_last_name}`,
        session: data.session_id,
        session_name: data.session_name,
        check_in_time: data.check_in_time,
        supervised: data.supervised,
        check_in_staff: '',
        check_in_staff_name: '',
      };

      // Avoid duplicates
      if (!activeCheckIns.find(r => r.id === newRecord.id)) {
        activeCheckIns = [...activeCheckIns, newRecord];
        filterCheckIns();
      }
    }
    else if (message.type === 'child_checked_out') {
      const recordId = message.data?.record_id;

      // Skip if this was our own action
      if (recordId && recentlyCheckedOutRecords.has(recordId)) {
        recentlyCheckedOutRecords.delete(recordId);
        recentlyCheckedOutRecords = new Set(recentlyCheckedOutRecords);
        return;
      }

      // Remove from list
      activeCheckIns = activeCheckIns.filter(r => r.id !== recordId);
      filterCheckIns();
    }
    else if (message.type === 'checkin_undone') {
      // Remove from checkout list (no longer checked in)
      const recordId = message.data?.record_id;
      activeCheckIns = activeCheckIns.filter(r => r.id !== recordId);
      filterCheckIns();
    }
    else if (message.type === 'checkout_undone') {
      // Child was re-checked-in after checkout undo
      // Fetch the record from API since we don't have full data
      if (matchesSession) {
        fetchSingleCheckIn(message.data.record_id);
      }
    }
  }

  async function fetchSingleCheckIn(recordId: string) {
    try {
      // Note: We need a single record endpoint. For now, reload all
      const allCheckIns = await checkInApi.active();
      const record = allCheckIns.find(r => r.id === recordId);

      // Only add if still active and matches session
      if (record && !record.check_out_time && (!activeSession || record.session === activeSession.id)) {
        // Avoid duplicates
        if (!activeCheckIns.find(r => r.id === record.id)) {
          activeCheckIns = [...activeCheckIns, record];
          filterCheckIns();
        }
      }
    } catch (err) {
      console.error('Failed to fetch check-in record:', err);
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

    // Identify families that have at least one matching child. We then show the
    // whole family (all their active check-ins), mirroring the check-in page —
    // a first-name search like "Emma" should surface Emma's siblings too, since
    // pickup usually happens per family.
    const matchingFamilyIds = new Set<string>();
    for (const record of activeCheckIns) {
      const childName = record.child_name?.toLowerCase() || '';
      if (childName.includes(query)) {
        const family = families.find((f) => f.children.some((c) => c.id === record.child));
        // Records whose family isn't loaded fall back to their own id so they
        // still appear on a direct name match.
        matchingFamilyIds.add(family?.id ?? record.id);
      }
    }

    filteredCheckIns = activeCheckIns.filter((record) => {
      const childName = record.child_name?.toLowerCase() || '';
      if (childName.includes(query)) return true;
      const family = families.find((f) => f.children.some((c) => c.id === record.child));
      return matchingFamilyIds.has(family?.id ?? record.id);
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
      // Track to prevent WebSocket from re-removing
      recentlyCheckedOutRecords.add(recordId);
      recentlyCheckedOutRecords = new Set(recentlyCheckedOutRecords);

      await checkInApi.checkOut(recordId, pickedUpBy[recordId] || '');

      successMessage = $t('checkout.success');

      // Clear the picked up by field
      delete pickedUpBy[recordId];

      // Optimistic update - remove from local state immediately
      activeCheckIns = activeCheckIns.filter(r => r.id !== recordId);
      filterCheckIns();

      // Clear success message after 3 seconds
      setTimeout(() => {
        successMessage = null;
      }, 3000);
    } catch (err) {
      // Rollback on error
      recentlyCheckedOutRecords.delete(recordId);
      recentlyCheckedOutRecords = new Set(recentlyCheckedOutRecords);
      console.error('Check-out failed:', err);
      error = $t('checkout.error');
      // Reload to get accurate state
      await loadActiveCheckIns();
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

      // Track all records to prevent WebSocket from re-removing
      familyRecords.forEach(record => {
        recentlyCheckedOutRecords.add(record.id);
      });
      recentlyCheckedOutRecords = new Set(recentlyCheckedOutRecords);

      // Check out all children in the family
      await Promise.all(
        familyRecords.map(record =>
          checkInApi.checkOut(record.id, pickedUpBy[familyId] || '')
        )
      );

      successMessage = $t('checkout.familySuccess', { values: { count: familyRecords.length } });

      // Clear the picked up by field
      delete pickedUpBy[familyId];

      // Optimistic update - remove all family records from local state
      const recordIds = new Set(familyRecords.map(r => r.id));
      activeCheckIns = activeCheckIns.filter(r => !recordIds.has(r.id));
      filterCheckIns();

      // Clear success message after 3 seconds
      setTimeout(() => {
        successMessage = null;
      }, 3000);
    } catch (err) {
      // Rollback on error
      const familyRecords = activeCheckIns.filter(record => {
        const family = families.find(f =>
          f.children.some(c => c.id === record.child)
        );
        return family?.id === familyId;
      });
      familyRecords.forEach(record => {
        recentlyCheckedOutRecords.delete(record.id);
      });
      recentlyCheckedOutRecords = new Set(recentlyCheckedOutRecords);
      console.error('Family check-out failed:', err);
      error = $t('checkout.familyError');
      // Reload to get accurate state
      await loadActiveCheckIns();
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
            supervised: record.supervised,
            qrCode: record.qr_code || null,
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
            supervised: record.supervised,
            qrCode: record.qr_code || null,
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
  <div class="max-w-4xl mx-auto p-3 md:p-5">
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

    <!-- Header (scrollable) -->
    <div class="mb-5">
      <h1 class="text-3xl font-bold text-blue-900">{$t('checkout.title')}</h1>
    </div>

    <!-- Sticky Search Box -->
    <div class="sticky top-0 z-10 bg-slate-100 pb-2 -mx-3 px-3 md:-mx-5 md:px-5">
      <SearchBox
        bind:value={searchQuery}
        placeholder={$t('checkout.searchPlaceholder')}
      />
    </div>

    <!-- Session Selector Modal -->
    <SessionSelector
      show={showSessionSelector}
      sessions={activeSessions}
      currentSession={activeSession}
      onSelect={handleSessionSelect}
      onClose={() => showSessionSelector = false}
    />

    <!-- Error Alert -->
    {#if error}
      <Alert type="error" dismissible ondismiss={() => error = null} class="mb-4">
        {error}
      </Alert>
    {/if}

    {#if loading && activeCheckIns.length === 0}
      <EmptyState
        type="loading"
        title={$t('checkout.loading')}
      />
    {/if}

    {#if !loading && filteredCheckIns.length === 0}
      <div class="text-center py-12 bg-white rounded-card border-2 border-dashed border-slate-300">
        <p class="text-slate-500 mb-2">
          {#if searchQuery}
            {$t('checkout.noChildrenFiltered', { values: { query: searchQuery } })}
          {:else}
            {$t('checkout.noChildren')}
          {/if}
        </p>
        {#if searchQuery}
          <p class="text-sm text-slate-400">{$t('checkin.tryDifferentSearch')}</p>
        {/if}
      </div>
    {/if}

    {#if filteredCheckIns.length > 0 && !loading}
      <CheckoutExpandableTable
        families={transformedFamilies}
        {pickedUpBy}
        onCheckOut={performCheckOut}
        onCheckOutFamily={performFamilyCheckOut}
        onPickedUpByChange={(familyId, value) => {
          pickedUpBy = { ...pickedUpBy, [familyId]: value };
        }}
        {formatTime}
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

<!-- Success Toast -->
{#if successMessage}
  <SuccessToast
    message={successMessage}
    onClose={() => {
      successMessage = null;
    }}
  />
{/if}
