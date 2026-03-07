<script lang="ts">
  import { onMount } from 'svelte';
  import { t } from 'svelte-i18n';
  import { importApi } from '$lib/api/importService';
  import type { ImportSource } from '$lib/api/types';

  let sources = $state<ImportSource[]>([]);
  let loading = $state(true);
  let error = $state('');

  onMount(async () => {
    try {
      sources = await importApi.listSources();
    } catch (e) {
      error = $t('import.loadSourcesError');
    } finally {
      loading = false;
    }
  });

  function providerTypeLabel(type: string): string {
    return type === 'festivalpro' ? 'FestivalPro' : 'Planning Center';
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
      <p class="mt-1 text-neutral-600">{$t('import.selectSourceDescription')}</p>
    </div>
    <a
      href="/import/sources"
      class="mt-1 text-sm text-primary-600 hover:underline font-medium whitespace-nowrap"
    >
      {$t('import.manageSources')}
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
  {:else if sources.length === 0}
    <div class="bg-white rounded-lg border border-neutral-200 shadow-sm p-8 text-center">
      <p class="text-neutral-500">{$t('import.noSources')}</p>
      <a
        href="/import/sources"
        class="mt-4 inline-flex items-center px-4 py-2 bg-primary-600 text-white text-sm font-semibold rounded-button hover:bg-primary-700 transition-colors"
      >
        {$t('import.addSource')}
      </a>
    </div>
  {:else}
    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {#each sources as source (source.id)}
        <div class="bg-white rounded-lg border border-neutral-200 shadow-sm hover:shadow-md transition-shadow">
          <div class="p-5">
            <h2 class="text-lg font-semibold text-neutral-900 mb-1">{source.name}</h2>
            <p class="text-sm text-neutral-500 mb-1">{providerTypeLabel(source.provider_type)}</p>
            {#if source.has_credentials}
              <p class="text-xs text-success-700 mb-4">{$t('import.sources.credentialsSet')}</p>
            {:else}
              <p class="text-xs text-warning-700 mb-4">{$t('import.sources.credentialsNotSet')}</p>
            {/if}
            <a
              href="/import/{source.id}"
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
