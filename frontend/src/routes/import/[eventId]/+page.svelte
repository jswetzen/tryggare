<script lang="ts">
  import { onMount } from 'svelte';
  import { t } from 'svelte-i18n';
  import { page } from '$app/stores';
  import { apiClient } from '$lib/api/client';
  import { importApi } from '$lib/api/importService';
  import type { DiscoveredPrefix, EventImportConfig, ImportProvider, ImportRun } from '$lib/api/types';

  // ---------------------------------------------------------------------------
  // Types
  // ---------------------------------------------------------------------------

  interface SessionSummary {
    id: string;
    name: string;
  }

  interface EventInfo {
    id: string;
    name: string;
    start_date: string;
    end_date: string;
  }

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------

  let eventId = $derived($page.params.eventId);

  let step = $state(1); // 1=upload, 2=map, 3=results
  let jsonString = $state<string | null>(null); // Raw JSON text (preserves duplicate keys)
  let fileName = $state('');
  let totalBookings = $state(0);
  let discoveredPrefixes = $state<DiscoveredPrefix[]>([]);
  let fieldMappings = $state<Record<string, string>>({});
  let sessions = $state<SessionSummary[]>([]);
  let savedConfig = $state<EventImportConfig | null>(null);
  let eventInfo = $state<EventInfo | null>(null);
  let importResult = $state<ImportRun | null>(null);
  let importHistory = $state<ImportRun[]>([]);
  let analyzing = $state(false);
  let importing = $state(false);
  let error = $state('');
  let showLogDetails = $state(false);
  let isDragOver = $state(false);

  // Provider-related state
  let providerInfo = $state<ImportProvider | null>(null);
  let providerLoading = $state(false);
  let allProviders = $state<ImportProvider[]>([]);
  let selectedProviderId = $state<string>('');  // '' = none
  let providerSaving = $state(false);

  // Hidden file input element reference
  let fileInput = $state<HTMLInputElement>(null!);

  // Auto-fetch is enabled when a config with a provider exists
  let autoFetchMode = $derived(savedConfig !== null && savedConfig.provider_id !== null);
  let providerHasNoCredentials = $derived(autoFetchMode && providerInfo !== null && !providerInfo.has_credentials);
  let hasSavedMappings = $derived(savedConfig !== null && Object.keys(savedConfig.field_mappings).length > 0);

  // ---------------------------------------------------------------------------
  // Lifecycle
  // ---------------------------------------------------------------------------

  onMount(async () => {
    const id = $page.params.eventId;
    await Promise.all([
      loadEventInfo(id),
      loadSessions(id),
      loadSavedConfig(id),
      loadHistory(id),
      loadAllProviders(),
    ]);
  });

  async function loadAllProviders() {
    try {
      allProviders = await importApi.listProviders();
    } catch {
      allProviders = [];
    }
  }

  async function loadEventInfo(id: string) {
    try {
      eventInfo = await apiClient.get<EventInfo>(`/events/${id}/`);
    } catch {
      // Non-fatal: page still works without event name
    }
  }

  async function loadSessions(id: string) {
    try {
      const result = await apiClient.get<SessionSummary[]>(`/sessions/?event=${id}`);
      sessions = result;
    } catch {
      sessions = [];
    }
  }

  async function loadSavedConfig(id: string) {
    try {
      savedConfig = await importApi.getConfig(id);
      selectedProviderId = savedConfig.provider_id ?? '';
      // If config has a provider, fetch provider details to check credentials
      if (savedConfig?.provider_id) {
        providerLoading = true;
        try {
          providerInfo = await importApi.getProvider(savedConfig.provider_id);
        } catch {
          providerInfo = null;
        } finally {
          providerLoading = false;
        }
      }
    } catch {
      // 404 is expected when no config exists yet
      savedConfig = null;
      selectedProviderId = '';
    }
  }

  async function saveProviderLink() {
    providerSaving = true;
    error = '';
    try {
      const updated = await importApi.setConfigProvider(eventId, selectedProviderId || null);
      savedConfig = updated;
      // Reload provider info
      if (updated.provider_id) {
        providerInfo = allProviders.find(p => p.id === updated.provider_id) ?? null;
      } else {
        providerInfo = null;
      }
    } catch {
      error = $t('import.linkProviderError');
    } finally {
      providerSaving = false;
    }
  }

  async function loadHistory(id: string) {
    try {
      importHistory = await importApi.getHistory(id);
    } catch {
      importHistory = [];
    }
  }

  // ---------------------------------------------------------------------------
  // File handling
  // ---------------------------------------------------------------------------

  function handleFileInputChange(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      processFile(input.files[0]);
    }
  }

  function handleDragOver(event: DragEvent) {
    event.preventDefault();
    isDragOver = true;
  }

  function handleDragLeave() {
    isDragOver = false;
  }

  function handleDrop(event: DragEvent) {
    event.preventDefault();
    isDragOver = false;
    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      processFile(files[0]);
    }
  }

  function processFile(file: File) {
    fileName = file.name;
    error = '';
    analyzing = true;

    const reader = new FileReader();
    reader.onload = async (e) => {
      try {
        const text = e.target?.result as string;
        jsonString = text; // Keep raw string — backend parses with duplicate-key support

        const result = await importApi.discoverPrefixes(text);
        discoveredPrefixes = result.prefixes;
        totalBookings = result.total_bookings;

        // Initialize field mappings — default to "full_event", apply saved config if available
        const mappings: Record<string, string> = {};
        for (const p of result.prefixes) {
          if (savedConfig?.field_mappings[p.prefix]) {
            mappings[p.prefix] = savedConfig.field_mappings[p.prefix];
          } else {
            mappings[p.prefix] = 'full_event';
          }
        }
        fieldMappings = mappings;
      } catch {
        error = $t('import.fileReadError');
        jsonString = null;
        discoveredPrefixes = [];
        totalBookings = 0;
      } finally {
        analyzing = false;
      }
    };
    reader.onerror = () => {
      error = $t('import.fileReadError');
      analyzing = false;
    };
    reader.readAsText(file);
  }

  // ---------------------------------------------------------------------------
  // Provider auto-fetch
  // ---------------------------------------------------------------------------

  async function fetchFromProvider() {
    error = '';
    analyzing = true;
    try {
      const result = await importApi.discoverPrefixesFromProvider(eventId);
      discoveredPrefixes = result.prefixes;
      totalBookings = result.total_bookings;

      // Initialize mappings with saved config values where available
      const mappings: Record<string, string> = {};
      for (const p of result.prefixes) {
        if (savedConfig?.field_mappings[p.prefix]) {
          mappings[p.prefix] = savedConfig.field_mappings[p.prefix];
        } else {
          mappings[p.prefix] = 'full_event';
        }
      }
      fieldMappings = mappings;
      jsonString = null; // No local JSON — will use auto-fetch path on run
      step = 2;
    } catch (e: unknown) {
      const err = e as { details?: { detail?: string } };
      error = err?.details?.detail ?? 'Failed to fetch data from provider.';
    } finally {
      analyzing = false;
    }
  }

  async function runImportAutoFetch() {
    // One-click re-sync: uses saved mappings, skips mapping step
    error = '';
    importing = true;
    try {
      const result = await importApi.runImportAutoFetch(eventId, savedConfig!.field_mappings);
      importResult = result;
      step = 3;
      await loadHistory(eventId);
    } catch (e: unknown) {
      const err = e as { details?: { detail?: string } };
      error = err?.details?.detail ?? $t('import.importError');
    } finally {
      importing = false;
    }
  }

  // ---------------------------------------------------------------------------
  // Navigation between steps
  // ---------------------------------------------------------------------------

  function goToMapping() {
    error = '';
    step = 2;
  }

  async function runImport() {
    if (!jsonString) return;
    error = '';
    importing = true;

    try {
      const result = await importApi.runImport(
        eventId,
        jsonString,
        fieldMappings,
        fileName
      );
      importResult = result;
      step = 3;
      // Refresh history after import
      await loadHistory(eventId);
    } catch {
      error = $t('import.importError');
    } finally {
      importing = false;
    }
  }

  async function runImportFromStep2() {
    // Step 2 run — could be manual file or auto-fetch path
    if (jsonString) {
      await runImport();
    } else {
      // Auto-fetch path: re-fetch + import with current fieldMappings
      error = '';
      importing = true;
      try {
        const result = await importApi.runImportAutoFetch(eventId, fieldMappings);
        importResult = result;
        step = 3;
        await loadHistory(eventId);
      } catch (e: unknown) {
        const err = e as { details?: { detail?: string } };
        error = err?.details?.detail ?? $t('import.importError');
      } finally {
        importing = false;
      }
    }
  }

  function resetWizard() {
    step = 1;
    jsonString = null;
    fileName = '';
    totalBookings = 0;
    discoveredPrefixes = [];
    fieldMappings = {};
    importResult = null;
    error = '';
    showLogDetails = false;
    // Reset file input so the same file can be re-selected
    if (fileInput) fileInput.value = '';
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  function formatDateTime(dateStr: string | null): string {
    if (!dateStr) return '—';
    try {
      return new Date(dateStr).toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  }

  function statusLabel(status: ImportRun['status']): string {
    switch (status) {
      case 'completed': return $t('import.statusCompleted');
      case 'failed':    return $t('import.statusFailed');
      case 'running':   return $t('import.statusRunning');
      case 'pending':   return $t('import.statusPending');
      default:          return status;
    }
  }

  function statusClasses(status: ImportRun['status']): string {
    switch (status) {
      case 'completed': return 'bg-success-100 text-success-800';
      case 'failed':    return 'bg-danger-100 text-danger-800';
      case 'running':   return 'bg-blue-100 text-blue-800';
      case 'pending':   return 'bg-neutral-100 text-neutral-700';
      default:          return 'bg-neutral-100 text-neutral-700';
    }
  }

  function canProceedToMapping(): boolean {
    return !analyzing && jsonString !== null && discoveredPrefixes.length > 0;
  }
</script>

<svelte:head>
  <title>{$t('import.pageTitle')}{eventInfo ? ` — ${eventInfo.name}` : ''}</title>
</svelte:head>

<div class="max-w-4xl mx-auto">

  <!-- Page header / breadcrumb -->
  <div class="mb-6">
    <a href="/import" class="text-sm text-primary-600 hover:underline font-medium">
      {$t('import.backToEvents')}
    </a>
    <h1 class="mt-2 text-2xl font-bold text-neutral-900">
      {$t('import.title')}
      {#if eventInfo}
        <span class="text-neutral-400 font-normal">— {eventInfo.name}</span>
      {/if}
    </h1>
  </div>

  <!-- Step indicator -->
  <div class="flex items-center gap-2 mb-6">
    {#each [
      { n: 1, label: $t('import.step1Title') },
      { n: 2, label: $t('import.step2Title') },
      { n: 3, label: $t('import.step3Title') },
    ] as s (s.n)}
      <div class="flex items-center gap-2">
        {#if s.n > 1}
          <div class="h-px w-8 {step >= s.n ? 'bg-primary-400' : 'bg-neutral-300'}"></div>
        {/if}
        <div class="flex items-center gap-2">
          <span class="
            w-7 h-7 rounded-full flex items-center justify-center text-sm font-bold
            {step > s.n ? 'bg-primary-600 text-white' :
             step === s.n ? 'bg-primary-600 text-white' :
             'bg-neutral-200 text-neutral-500'}
          ">{s.n}</span>
          <span class="
            text-sm font-medium hidden sm:inline
            {step === s.n ? 'text-primary-700' : 'text-neutral-500'}
          ">{s.label}</span>
        </div>
      </div>
    {/each}
  </div>

  <!-- =========================================================
       STEP 1 — Upload / Auto-fetch
       ========================================================= -->
  {#if step === 1}
    <div class="bg-white rounded-lg border border-neutral-200 shadow-sm p-6">
      <h2 class="text-lg font-semibold text-neutral-900 mb-4">{$t('import.step1Title')}</h2>

      <!-- Provider selector -->
      {#if allProviders.length > 0}
        <div class="mb-5 flex items-end gap-3 flex-wrap">
          <div class="flex-1 min-w-48">
            <label class="block text-sm font-medium text-neutral-700 mb-1" for="provider-select">
              {$t('import.providerLabel')}
            </label>
            <select
              id="provider-select"
              bind:value={selectedProviderId}
              class="w-full border border-neutral-300 rounded px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-primary-400"
            >
              <option value="">{$t('import.manualUploadOption')}</option>
              {#each allProviders as p (p.id)}
                <option value={p.id}>{p.name}</option>
              {/each}
            </select>
          </div>
          <button
            onclick={saveProviderLink}
            disabled={providerSaving || selectedProviderId === (savedConfig?.provider_id ?? '')}
            class="px-4 py-2 bg-primary-600 text-white text-sm font-semibold rounded-button hover:bg-primary-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
          >
            {providerSaving ? $t('import.savingProvider') : $t('import.saveProvider')}
          </button>
          <a href="/import/providers" class="text-sm text-primary-600 hover:underline whitespace-nowrap py-2">
            {$t('import.manageProvidersLink')}
          </a>
        </div>
      {:else}
        <div class="mb-4 p-3 bg-neutral-50 border border-neutral-200 rounded text-neutral-600 text-sm flex items-center justify-between gap-3">
          <span>{$t('import.noProviders')}</span>
          <a href="/import/providers" class="text-primary-600 hover:underline font-medium whitespace-nowrap">
            {$t('import.addProvider')}
          </a>
        </div>
      {/if}

      <!-- Provider banner -->
      {#if autoFetchMode && !providerLoading}
        {#if providerHasNoCredentials}
          <div class="mb-4 p-3 bg-warning-50 border border-warning-200 rounded text-warning-700 text-sm">
            <strong>{$t('import.providerNoCredentials')}</strong> — {$t('import.providerNoCredentialsHelp')}
            <a href="/import/providers" class="underline font-medium">{$t('import.providerNoCredentialsLink')}</a>.
          </div>
        {:else if providerInfo}
          <div class="mb-4 p-3 bg-blue-50 border border-blue-200 rounded text-blue-700 text-sm flex items-center justify-between gap-4 flex-wrap">
            <span>
              <strong>{$t('import.autoFetchConfigured')}</strong> {savedConfig?.provider_name ?? providerInfo.name}
            </span>
            {#if hasSavedMappings}
              <!-- One-click re-sync: skip mapping step entirely -->
              <button
                onclick={runImportAutoFetch}
                disabled={importing}
                class="px-4 py-1.5 bg-blue-600 text-white text-sm font-semibold rounded-button hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
              >
                {importing ? $t('import.importing') : $t('import.resync')}
              </button>
            {:else}
              <!-- First run: fetch prefixes then go to mapping step -->
              <button
                onclick={fetchFromProvider}
                disabled={analyzing}
                class="px-4 py-1.5 bg-blue-600 text-white text-sm font-semibold rounded-button hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
              >
                {analyzing ? $t('import.fetching') : $t('import.fetchFromProvider')}
              </button>
            {/if}
          </div>
        {/if}
      {/if}

      {#if error}
        <div class="mb-4 p-3 bg-danger-50 border border-danger-200 rounded text-danger-700 text-sm">
          {error}
        </div>
      {/if}

      <!-- Drop zone -->
      <!-- svelte-ignore a11y_interactive_supports_focus -->
      <div
        role="button"
        aria-label={$t('import.dropOrClick')}
        class="
          border-2 border-dashed rounded-lg p-10 text-center cursor-pointer transition-colors
          {isDragOver ? 'border-primary-400 bg-primary-50' : 'border-neutral-300 hover:border-primary-400 hover:bg-neutral-50'}
        "
        onclick={() => fileInput.click()}
        onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') fileInput.click(); }}
        ondragover={handleDragOver}
        ondragleave={handleDragLeave}
        ondrop={handleDrop}
      >
        <svg class="mx-auto mb-3 h-10 w-10 text-neutral-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
            d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>

        {#if analyzing && !fileName}
          <p class="text-primary-600 font-medium">{$t('import.fetchingFromProvider')}</p>
        {:else if analyzing}
          <p class="text-primary-600 font-medium">{$t('import.analyzing')}</p>
        {:else if fileName}
          <p class="text-neutral-800 font-medium">{fileName}</p>
          {#if discoveredPrefixes.length > 0}
            <p class="mt-1 text-sm text-success-700">
              {$t('import.bookingsFound', { values: { count: totalBookings } })}
              &middot;
              {$t('import.prefixesFound', { values: { count: discoveredPrefixes.length } })}
            </p>
          {:else if jsonString !== null}
            <p class="mt-1 text-sm text-warning-700">{$t('import.noPrefixesFound')}</p>
          {/if}
          <p class="mt-2 text-xs text-neutral-400">{$t('import.dropOrClick')}</p>
        {:else}
          <p class="text-neutral-600 font-medium">{$t('import.dropOrClick')}</p>
          <p class="mt-1 text-sm text-neutral-400">{$t('import.acceptedFormat')}</p>
        {/if}
      </div>

      <!-- Hidden file input -->
      <input
        bind:this={fileInput}
        type="file"
        accept=".json,application/json"
        class="hidden"
        onchange={handleFileInputChange}
      />

      {#if !fileName && !analyzing}
        <p class="mt-4 text-sm text-neutral-400 text-center">{$t('import.loadFileFirst')}</p>
      {/if}

      <!-- Continue button -->
      <div class="mt-6 flex justify-end">
        <button
          onclick={goToMapping}
          disabled={!canProceedToMapping()}
          class="
            px-5 py-2 bg-primary-600 text-white font-semibold rounded-button transition-colors
            hover:bg-primary-700 disabled:opacity-40 disabled:cursor-not-allowed
          "
        >
          {$t('import.continueToMapping')}
        </button>
      </div>
    </div>
  {/if}

  <!-- =========================================================
       STEP 2 — Map prefixes
       ========================================================= -->
  {#if step === 2}
    <div class="bg-white rounded-lg border border-neutral-200 shadow-sm p-6">
      <h2 class="text-lg font-semibold text-neutral-900 mb-1">{$t('import.step2Title')}</h2>
      <p class="text-sm text-neutral-500 mb-4">{$t('import.mappingNote')}</p>

      {#if savedConfig}
        <div class="mb-4 p-3 bg-blue-50 border border-blue-200 rounded text-blue-700 text-sm">
          {$t('import.savedConfigFound')}
        </div>
      {/if}

      {#if sessions.length === 0}
        <div class="mb-4 p-3 bg-warning-50 border border-warning-200 rounded text-warning-700 text-sm">
          {$t('import.noSessions')}
        </div>
      {/if}

      <!-- Mapping table -->
      <div class="overflow-x-auto rounded-lg border border-neutral-200">
        <table class="w-full text-sm">
          <thead class="bg-neutral-50 border-b border-neutral-200">
            <tr>
              <th class="text-left px-4 py-3 font-semibold text-neutral-700">{$t('import.prefix')}</th>
              <th class="text-left px-4 py-3 font-semibold text-neutral-700">{$t('import.sampleChildren')}</th>
              <th class="text-right px-4 py-3 font-semibold text-neutral-700">{$t('import.childCount')}</th>
              <th class="text-left px-4 py-3 font-semibold text-neutral-700">{$t('import.mapTo')}</th>
            </tr>
          </thead>
          <tbody>
            {#each discoveredPrefixes as prefix, i (prefix.prefix)}
              <tr class="border-b border-neutral-100 {i % 2 === 1 ? 'bg-neutral-50' : ''}">
                <td class="px-4 py-3 font-mono text-neutral-800 font-medium">{prefix.prefix}</td>
                <td class="px-4 py-3 text-neutral-600 max-w-xs">
                  {prefix.sample_children.slice(0, 3).join(', ')}
                  {#if prefix.sample_children.length > 3}
                    <span class="text-neutral-400">&hellip;</span>
                  {/if}
                </td>
                <td class="px-4 py-3 text-right text-neutral-700">{prefix.booking_count}</td>
                <td class="px-4 py-3">
                  <select
                    bind:value={fieldMappings[prefix.prefix]}
                    class="w-full border border-neutral-300 rounded px-2 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-primary-400"
                  >
                    <option value="full_event">{$t('import.fullEvent')}</option>
                    {#each sessions as session (session.id)}
                      <option value={session.id}>{session.name}</option>
                    {/each}
                    <option value="ignore">{$t('import.ignore')}</option>
                  </select>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      {#if error}
        <div class="mt-4 p-3 bg-danger-50 border border-danger-200 rounded text-danger-700 text-sm">
          {error}
        </div>
      {/if}

      <!-- Actions -->
      <div class="mt-6 flex items-center justify-between">
        <button
          onclick={() => { step = 1; error = ''; }}
          class="px-4 py-2 text-neutral-600 font-semibold hover:text-neutral-900 transition-colors"
        >
          &larr; {$t('import.backToUpload')}
        </button>
        <button
          onclick={runImportFromStep2}
          disabled={importing}
          class="
            px-5 py-2 bg-primary-600 text-white font-semibold rounded-button transition-colors
            hover:bg-primary-700 disabled:opacity-40 disabled:cursor-not-allowed
          "
        >
          {importing ? $t('import.importing') : $t('import.runImport')}
        </button>
      </div>
    </div>
  {/if}

  <!-- =========================================================
       STEP 3 — Results
       ========================================================= -->
  {#if step === 3 && importResult}
    <div class="bg-white rounded-lg border border-neutral-200 shadow-sm p-6">
      <div class="flex items-center gap-3 mb-6">
        {#if importResult.status === 'completed'}
          <span class="flex-shrink-0 w-8 h-8 rounded-full bg-success-100 flex items-center justify-center">
            <svg class="w-5 h-5 text-success-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
          </span>
          <h2 class="text-lg font-semibold text-success-800">{$t('import.importComplete')}</h2>
        {:else}
          <span class="flex-shrink-0 w-8 h-8 rounded-full bg-danger-100 flex items-center justify-center">
            <svg class="w-5 h-5 text-danger-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </span>
          <h2 class="text-lg font-semibold text-danger-800">{$t('import.importFailed')}</h2>
        {/if}
      </div>

      <!-- Summary stats -->
      <div class="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-6">
        {#if importResult.summary.total_bookings !== undefined}
          <div class="bg-neutral-50 rounded-lg p-4 text-center border border-neutral-200">
            <div class="text-2xl font-bold text-neutral-900">{importResult.summary.total_bookings}</div>
            <div class="text-xs text-neutral-500 mt-1">{$t('import.totalBookings')}</div>
          </div>
        {/if}
        {#if importResult.summary.families_created !== undefined}
          <div class="bg-success-50 rounded-lg p-4 text-center border border-success-200">
            <div class="text-2xl font-bold text-success-800">{importResult.summary.families_created}</div>
            <div class="text-xs text-success-700 mt-1">{$t('import.familiesCreated')}</div>
          </div>
        {/if}
        {#if importResult.summary.families_skipped !== undefined}
          <div class="bg-neutral-50 rounded-lg p-4 text-center border border-neutral-200">
            <div class="text-2xl font-bold text-neutral-700">{importResult.summary.families_skipped}</div>
            <div class="text-xs text-neutral-500 mt-1">{$t('import.familiesSkipped')}</div>
          </div>
        {/if}
        {#if importResult.summary.children_created !== undefined}
          <div class="bg-success-50 rounded-lg p-4 text-center border border-success-200">
            <div class="text-2xl font-bold text-success-800">{importResult.summary.children_created}</div>
            <div class="text-xs text-success-700 mt-1">{$t('import.childrenCreated')}</div>
          </div>
        {/if}
        {#if importResult.summary.children_skipped !== undefined}
          <div class="bg-neutral-50 rounded-lg p-4 text-center border border-neutral-200">
            <div class="text-2xl font-bold text-neutral-700">{importResult.summary.children_skipped}</div>
            <div class="text-xs text-neutral-500 mt-1">{$t('import.childrenSkipped')}</div>
          </div>
        {/if}
        {#if importResult.summary.tickets_created !== undefined}
          <div class="bg-primary-50 rounded-lg p-4 text-center border border-primary-200">
            <div class="text-2xl font-bold text-primary-800">{importResult.summary.tickets_created}</div>
            <div class="text-xs text-primary-700 mt-1">{$t('import.ticketsCreated')}</div>
          </div>
        {/if}
      </div>

      <!-- Errors -->
      {#if importResult.summary.errors && importResult.summary.errors.length > 0}
        <div class="mb-4">
          <h3 class="text-sm font-semibold text-danger-700 mb-2">{$t('import.errors')}</h3>
          <ul class="space-y-1">
            {#each importResult.summary.errors as err (err)}
              <li class="text-sm text-danger-600 bg-danger-50 border border-danger-200 rounded px-3 py-2">{err}</li>
            {/each}
          </ul>
        </div>
      {/if}

      <!-- Warnings -->
      {#if importResult.summary.warnings && importResult.summary.warnings.length > 0}
        <div class="mb-4">
          <h3 class="text-sm font-semibold text-warning-700 mb-2">{$t('import.warnings')}</h3>
          <ul class="space-y-1">
            {#each importResult.summary.warnings as warning (warning)}
              <li class="text-sm text-warning-700 bg-warning-50 border border-warning-200 rounded px-3 py-2">{warning}</li>
            {/each}
          </ul>
        </div>
      {/if}

      <!-- Import Again button -->
      <div class="mt-6 flex justify-end">
        <button
          onclick={resetWizard}
          class="px-5 py-2 bg-primary-600 text-white font-semibold rounded-button hover:bg-primary-700 transition-colors"
        >
          {$t('import.importAgain')}
        </button>
      </div>
    </div>
  {/if}

  <!-- =========================================================
       Import History (always shown at bottom)
       ========================================================= -->
  <div class="mt-8 bg-white rounded-lg border border-neutral-200 shadow-sm">
    <div class="px-6 py-4 border-b border-neutral-200">
      <h2 class="text-base font-semibold text-neutral-900">{$t('import.importHistory')}</h2>
    </div>

    {#if importHistory.length === 0}
      <div class="px-6 py-8 text-center text-neutral-400 text-sm">
        {$t('import.noHistory')}
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-neutral-50 border-b border-neutral-200">
            <tr>
              <th class="text-left px-4 py-3 font-semibold text-neutral-700">{$t('import.historyDate')}</th>
              <th class="text-left px-4 py-3 font-semibold text-neutral-700">{$t('import.historyStatus')}</th>
              <th class="text-left px-4 py-3 font-semibold text-neutral-700">{$t('import.historyUser')}</th>
              <th class="text-right px-4 py-3 font-semibold text-neutral-700">{$t('import.historyFamilies')}</th>
              <th class="text-right px-4 py-3 font-semibold text-neutral-700">{$t('import.historyChildren')}</th>
            </tr>
          </thead>
          <tbody>
            {#each importHistory as run, i (run.id)}
              <tr class="border-b border-neutral-100 {i % 2 === 1 ? 'bg-neutral-50' : ''}">
                <td class="px-4 py-3 text-neutral-700 whitespace-nowrap">
                  {formatDateTime(run.started_at)}
                  {#if run.source_file_name}
                    <span class="block text-xs text-neutral-400 font-mono">{run.source_file_name}</span>
                  {/if}
                </td>
                <td class="px-4 py-3">
                  <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold {statusClasses(run.status)}">
                    {statusLabel(run.status)}
                  </span>
                </td>
                <td class="px-4 py-3 text-neutral-600">
                  {run.triggered_by_name ?? run.triggered_by ?? '—'}
                </td>
                <td class="px-4 py-3 text-right text-neutral-700">
                  {#if run.summary?.families_created !== undefined}
                    <span class="text-success-700">+{run.summary.families_created}</span>
                    {#if run.summary.families_skipped}
                      <span class="text-neutral-400 text-xs"> / {run.summary.families_skipped} {$t('import.skipped')}</span>
                    {/if}
                  {:else}
                    —
                  {/if}
                </td>
                <td class="px-4 py-3 text-right text-neutral-700">
                  {#if run.summary?.children_created !== undefined}
                    <span class="text-success-700">+{run.summary.children_created}</span>
                    {#if run.summary.children_skipped}
                      <span class="text-neutral-400 text-xs"> / {run.summary.children_skipped} {$t('import.skipped')}</span>
                    {/if}
                  {:else}
                    —
                  {/if}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </div>

</div>
