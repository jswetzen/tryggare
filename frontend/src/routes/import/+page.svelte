<script lang="ts">
  import { onMount } from 'svelte';
  import { t } from 'svelte-i18n';
  import { apiClient } from '$lib/api/client';

  interface EventSummary {
    id: string;
    name: string;
    start_date: string;
    end_date: string;
  }

  let events = $state<EventSummary[]>([]);
  let loading = $state(true);
  let error = $state('');

  onMount(async () => {
    try {
      events = await apiClient.get<EventSummary[]>('/events/');
    } catch (e) {
      error = 'Failed to load events';
    } finally {
      loading = false;
    }
  });

  function formatDate(dateStr: string): string {
    if (!dateStr) return '';
    try {
      return new Date(dateStr).toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return dateStr;
    }
  }
</script>

<svelte:head>
  <title>{$t('import.pageTitle')}</title>
</svelte:head>

<div class="max-w-4xl mx-auto">
  <!-- Page header -->
  <div class="mb-6 flex items-start justify-between">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900">{$t('import.title')}</h1>
      <p class="mt-1 text-neutral-600">{$t('import.selectEventDescription')}</p>
    </div>
    <a
      href="/import/providers"
      class="mt-1 text-sm text-primary-600 hover:underline font-medium whitespace-nowrap"
    >
      Manage Providers
    </a>
  </div>

  {#if loading}
    <div class="bg-white rounded-lg border border-neutral-200 shadow-sm p-8 text-center">
      <div class="text-neutral-500">{$t('common.loading')}</div>
    </div>
  {:else if error}
    <div class="bg-white rounded-lg border border-neutral-200 shadow-sm p-8 text-center">
      <p class="text-danger-600">{error}</p>
    </div>
  {:else if events.length === 0}
    <div class="bg-white rounded-lg border border-neutral-200 shadow-sm p-8 text-center">
      <p class="text-neutral-500">{$t('import.noEvents')}</p>
    </div>
  {:else}
    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {#each events as event (event.id)}
        <div class="bg-white rounded-lg border border-neutral-200 shadow-sm hover:shadow-md transition-shadow">
          <div class="p-5">
            <h2 class="text-lg font-semibold text-neutral-900 mb-1">{event.name}</h2>
            {#if event.start_date}
              <p class="text-sm text-neutral-500 mb-4">
                {formatDate(event.start_date)}
                {#if event.end_date && event.end_date !== event.start_date}
                  &ndash; {formatDate(event.end_date)}
                {/if}
              </p>
            {:else}
              <div class="mb-4"></div>
            {/if}
            <a
              href="/import/{event.id}"
              class="inline-flex items-center px-4 py-2 bg-primary-600 text-white text-sm font-semibold rounded-button hover:bg-primary-700 transition-colors"
            >
              {$t('import.title')} &rarr;
            </a>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>
