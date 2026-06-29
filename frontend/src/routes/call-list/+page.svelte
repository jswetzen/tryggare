<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { t } from 'svelte-i18n';
  import { checkInApi, familyApi } from '$lib/api/services';
  import { websocketStore } from '$lib/stores/websocket';
  import type { CheckInRecord, Family, WebSocketMessage } from '$lib/api/types';
  import { normalizePhone } from '$lib/utils/phone';
  import { EmptyState, Button, Icon, Alert } from '$lib/components/ui';

  let activeCheckIns = $state<CheckInRecord[]>([]);
  let families = $state<Family[]>([]);
  let loading = $state(false);
  let error = $state<string | null>(null);

  let unsubscribe: (() => void) | null = null;

  onMount(() => {
    websocketStore.connect();
    unsubscribe = websocketStore.onMessage(handleWebSocketMessage);
    load();
  });

  onDestroy(() => {
    if (unsubscribe) unsubscribe();
  });

  function handleWebSocketMessage(message: WebSocketMessage) {
    // Keep the list live: anything that changes who is checked in should refresh.
    if (
      message.type === 'child_checked_in' ||
      message.type === 'child_checked_out' ||
      message.type === 'checkin_undone' ||
      message.type === 'checkout_undone'
    ) {
      loadCheckIns();
    }
  }

  async function load() {
    loading = true;
    error = null;
    try {
      await Promise.all([loadCheckIns(), loadFamilies()]);
    } catch (err) {
      console.error('Failed to load call list:', err);
      error = $t('callList.loadError');
    } finally {
      loading = false;
    }
  }

  async function loadCheckIns() {
    activeCheckIns = await checkInApi.active();
  }

  async function loadFamilies() {
    families = await familyApi.list();
  }

  function formatTime(isoString: string): string {
    return new Date(isoString).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  }

  interface CallListChild {
    name: string;
    checkInTime?: string;
  }
  interface CallListFamily {
    id: string;
    displayName: string;
    children: CallListChild[];
    parents: { name: string; phone?: string; relationship: string }[];
  }

  // Group still-checked-in children by family, so staff can call one parent to
  // arrange pickup for the whole family at once. Families with no remaining
  // checked-in children drop off the list.
  const callListFamilies = $derived.by<CallListFamily[]>(() => {
    const byFamily = new Map<string, CheckInRecord[]>();
    const looseRecords: CheckInRecord[] = [];

    for (const record of activeCheckIns) {
      const family = families.find((f) => f.children.some((c) => c.id === record.child));
      if (family) {
        if (!byFamily.has(family.id)) byFamily.set(family.id, []);
        byFamily.get(family.id)!.push(record);
      } else {
        looseRecords.push(record);
      }
    }

    const result: CallListFamily[] = [];

    for (const [familyId, records] of byFamily.entries()) {
      const family = families.find((f) => f.id === familyId)!;
      result.push({
        id: familyId,
        displayName: family.display_name || family.last_name,
        children: records.map((r) => {
          const child = family.children.find((c) => c.id === r.child);
          return {
            name: child ? `${child.first_name} ${child.last_name}` : r.child_name,
            checkInTime: r.check_in_time,
          };
        }),
        parents: family.parents.map((p) => ({
          name: p.name,
          phone: p.phone,
          relationship: p.relationship_type,
        })),
      });
    }

    // Records whose family we couldn't resolve still deserve a row so no child
    // is silently dropped — they just have no parent contacts to call.
    for (const record of looseRecords) {
      result.push({
        id: record.id,
        displayName: record.child_name,
        children: [{ name: record.child_name, checkInTime: record.check_in_time }],
        parents: [],
      });
    }

    // Sort by earliest check-in so longest-waiting families surface first.
    const earliest = (f: CallListFamily) =>
      Math.min(...f.children.map((c) => (c.checkInTime ? Date.parse(c.checkInTime) : Infinity)));
    return result.sort((a, b) => earliest(a) - earliest(b));
  });
</script>

<svelte:head>
  <title>{$t('callList.pageTitle')}</title>
</svelte:head>

<div class="min-h-screen bg-slate-100">
  <div class="max-w-4xl mx-auto p-3 md:p-5">
    <div class="mb-5">
      <h1 class="text-3xl font-bold text-blue-900">{$t('callList.title')}</h1>
      <p class="text-slate-600 mt-1">{$t('callList.subtitle')}</p>
    </div>

    {#if error}
      <Alert type="error" dismissible ondismiss={() => (error = null)} class="mb-4">
        {error}
      </Alert>
    {/if}

    <div class="flex justify-end mb-4">
      <Button variant="ghost" onclick={load} disabled={loading}>
        <Icon name="refresh" size="sm" class="mr-2" />
        {$t('callList.refresh')}
      </Button>
    </div>

    {#if loading && activeCheckIns.length === 0}
      <EmptyState type="loading" title={$t('callList.loading')} />
    {:else if callListFamilies.length === 0}
      <EmptyState type="empty" title={$t('callList.empty')}>
        {#snippet icon()}
          <Icon name="check-circle" size="xl" />
        {/snippet}
      </EmptyState>
    {:else}
      <div class="space-y-3">
        {#each callListFamilies as family (family.id)}
          <div class="bg-white rounded-card border-2 border-slate-300 overflow-hidden">
            <div class="px-4 py-3 border-b border-slate-200">
              <div class="flex items-center gap-2">
                <span class="font-semibold text-slate-900">{family.displayName}</span>
                <span
                  class="inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 bg-blue-100 text-blue-700 text-xs font-medium rounded"
                >
                  {$t('callList.childrenStillIn', { values: { count: family.children.length } })}
                </span>
              </div>
              <div class="text-sm text-slate-500 mt-1">
                {#each family.children as child, i}
                  <span>
                    {child.name}{#if child.checkInTime}
                      <span class="text-slate-400">
                        ({$t('callList.checkedInSince', {
                          values: { time: formatTime(child.checkInTime) },
                        })})</span
                      >{/if}{#if i < family.children.length - 1},
                    {/if}
                  </span>
                {/each}
              </div>
            </div>

            <div class="px-4 py-3">
              {#if family.parents.length === 0}
                <div class="text-sm text-slate-400 italic">{$t('callList.noPhone')}</div>
              {:else}
                <div class="space-y-2">
                  {#each family.parents as parent}
                    <div class="flex items-center justify-between gap-3">
                      <div class="min-w-0">
                        <span class="text-slate-900">{parent.name}</span>
                        <span class="text-xs text-slate-500">({parent.relationship})</span>
                      </div>
                      {#if parent.phone}
                        <a
                          href={`tel:${normalizePhone(parent.phone)}`}
                          class="flex-shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 bg-green-600 text-white text-sm font-medium rounded hover:bg-green-700 transition-colors"
                        >
                          <Icon name="phone" size="sm" />
                          {parent.phone}
                        </a>
                      {:else}
                        <span class="flex-shrink-0 text-xs text-slate-400 italic">
                          {$t('callList.noPhone')}
                        </span>
                      {/if}
                    </div>
                  {/each}
                </div>
              {/if}
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </div>
</div>
