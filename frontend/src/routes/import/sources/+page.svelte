<script lang="ts">
  import { onMount } from 'svelte';
  import { t } from 'svelte-i18n';
  import { importApi } from '$lib/api/importService';
  import type { ImportSource, ImportSourceWrite } from '$lib/api/types';

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------

  let sources = $state<ImportSource[]>([]);
  let loading = $state(true);
  let error = $state('');
  let formError = $state('');
  let saving = $state(false);

  // Form visibility
  let showForm = $state(false);
  let editingId = $state<string | null>(null);

  // Form fields
  let formName = $state('');
  let formProviderType = $state<'festivalpro' | 'planningcenter'>('festivalpro');
  let formLoginUrl = $state('');
  let formExportUrl = $state('');
  let formExportBody = $state('');
  let formUsername = $state('');
  let formPassword = $state('');

  // ---------------------------------------------------------------------------
  // Lifecycle
  // ---------------------------------------------------------------------------

  onMount(async () => {
    await loadSources();
  });

  async function loadSources() {
    loading = true;
    error = '';
    try {
      sources = await importApi.listSources();
    } catch {
      error = $t('import.sources.loadError');
    } finally {
      loading = false;
    }
  }

  // ---------------------------------------------------------------------------
  // Form helpers
  // ---------------------------------------------------------------------------

  function resetForm() {
    formName = '';
    formProviderType = 'festivalpro';
    formLoginUrl = '';
    formExportUrl = '';
    formExportBody = '';
    formUsername = '';
    formPassword = '';
    formError = '';
    editingId = null;
    showForm = false;
  }

  function startCreate() {
    resetForm();
    showForm = true;
  }

  function startEdit(source: ImportSource) {
    editingId = source.id;
    formName = source.name;
    formProviderType = source.provider_type;
    formLoginUrl = source.festivalpro_config?.login_url ?? '';
    formExportUrl = source.festivalpro_config?.export_url ?? '';
    formExportBody = source.festivalpro_config?.export_body ?? '';
    formUsername = '';
    formPassword = '';
    formError = '';
    showForm = true;
  }

  async function saveSource() {
    formError = '';
    if (!formName.trim()) { formError = $t('import.sources.nameRequired'); return; }
    if (formProviderType === 'festivalpro') {
      if (!formLoginUrl.trim()) { formError = $t('import.sources.loginUrlRequired'); return; }
      if (!formExportUrl.trim()) { formError = $t('import.sources.exportUrlRequired'); return; }
    }

    saving = true;
    try {
      const data: ImportSourceWrite = {
        name: formName.trim(),
        provider_type: formProviderType,
      };
      if (formUsername.trim()) data.username = formUsername.trim();
      if (formPassword) data.password = formPassword;

      if (formProviderType === 'festivalpro') {
        data.festivalpro_config = {
          login_url: formLoginUrl.trim(),
          export_url: formExportUrl.trim(),
          export_body: formExportBody.trim(),
        };
      }

      if (editingId) {
        await importApi.updateSource(editingId, data);
      } else {
        await importApi.createSource(data);
      }
      resetForm();
      await loadSources();
    } catch (e: unknown) {
      const err = e as { details?: { name?: string[]; login_url?: string[] } };
      formError = err?.details?.name?.[0] ?? err?.details?.login_url?.[0] ?? $t('import.sources.saveError');
    } finally {
      saving = false;
    }
  }

  async function deleteSource(source: ImportSource) {
    if (!confirm($t('import.sources.deleteConfirm', { values: { name: source.name } }))) return;
    try {
      await importApi.deleteSource(source.id);
      await loadSources();
    } catch {
      error = $t('import.sources.deleteError');
    }
  }

  function formatDate(dateStr: string): string {
    try {
      return new Date(dateStr).toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return dateStr;
    }
  }

  function providerTypeLabel(type: string): string {
    return type === 'festivalpro' ? 'FestivalPro' : 'Planning Center';
  }
</script>

<svelte:head>
  <title>{$t('import.sources.pageTitle')} — {$t('import.pageTitle')}</title>
</svelte:head>

<div class="max-w-4xl mx-auto">

  <!-- Header -->
  <div class="mb-6">
    <a href="/import" class="text-sm text-primary-600 hover:underline font-medium">
      ← {$t('import.backToSources')}
    </a>
    <h1 class="mt-2 text-2xl font-bold text-neutral-900">{$t('import.sources.pageTitle')}</h1>
    <p class="mt-1 text-neutral-600">{$t('import.sources.description')}</p>
  </div>

  <!-- Global error -->
  {#if error}
    <div class="mb-4 p-3 bg-danger-50 border border-danger-200 rounded text-danger-700 text-sm">
      {error}
    </div>
  {/if}

  <!-- New source form -->
  {#if showForm}
    <div class="mb-6 bg-white rounded-lg border border-neutral-200 shadow-sm p-6">
      <h2 class="text-base font-semibold text-neutral-900 mb-4">
        {editingId ? $t('import.sources.editSource') : $t('import.sources.newSource')}
      </h2>

      {#if formError}
        <div class="mb-4 p-3 bg-danger-50 border border-danger-200 rounded text-danger-700 text-sm">
          {formError}
        </div>
      {/if}

      <div class="grid gap-4 sm:grid-cols-2">
        <!-- Name -->
        <div class="sm:col-span-2">
          <label class="block text-sm font-medium text-neutral-700 mb-1" for="src-name">
            {$t('import.sources.fieldName')} <span class="text-danger-500">*</span>
          </label>
          <input
            id="src-name"
            type="text"
            bind:value={formName}
            placeholder="e.g. FestivalPro SK27"
            class="w-full border border-neutral-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
          />
        </div>

        <!-- Provider type -->
        <div class="sm:col-span-2">
          <label class="block text-sm font-medium text-neutral-700 mb-1" for="src-type">
            {$t('import.sources.fieldProviderType')} <span class="text-danger-500">*</span>
          </label>
          <select
            id="src-type"
            bind:value={formProviderType}
            class="w-full border border-neutral-300 rounded px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-primary-400"
          >
            <option value="festivalpro">FestivalPro</option>
            <option value="planningcenter">Planning Center</option>
          </select>
        </div>

        <!-- FestivalPro-specific fields -->
        {#if formProviderType === 'festivalpro'}
          <div>
            <label class="block text-sm font-medium text-neutral-700 mb-1" for="src-login-url">
              {$t('import.sources.fieldLoginUrl')} <span class="text-danger-500">*</span>
            </label>
            <input
              id="src-login-url"
              type="url"
              bind:value={formLoginUrl}
              placeholder="https://example.com/?login"
              class="w-full border border-neutral-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-neutral-700 mb-1" for="src-export-url">
              {$t('import.sources.fieldExportUrl')} <span class="text-danger-500">*</span>
            </label>
            <input
              id="src-export-url"
              type="url"
              bind:value={formExportUrl}
              placeholder="https://example.com/?advancedExport"
              class="w-full border border-neutral-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
            />
          </div>

          <div class="sm:col-span-2">
            <label class="block text-sm font-medium text-neutral-700 mb-1" for="src-export-body">
              {$t('import.sources.fieldExportBody')}
              <span class="text-neutral-400 font-normal">({$t('import.sources.fieldExportBodyHint')})</span>
            </label>
            <textarea
              id="src-export-body"
              bind:value={formExportBody}
              rows="5"
              placeholder="QUERYQ=CODE*__EQ__*...&EVENTID=5781&EXPORT=JSON&ETICKETS=1&..."
              class="w-full border border-neutral-300 rounded px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary-400 resize-y"
            ></textarea>
            <p class="mt-1 text-xs text-neutral-400">
              {$t('import.sources.fieldExportBodyHelp')}
            </p>
          </div>

          <div>
            <label class="block text-sm font-medium text-neutral-700 mb-1" for="src-username">
              {$t('import.sources.fieldUsername')}
              {#if editingId}
                <span class="text-neutral-400 font-normal">({$t('import.sources.fieldKeepExisting')})</span>
              {/if}
            </label>
            <input
              id="src-username"
              type="text"
              autocomplete="off"
              bind:value={formUsername}
              placeholder={editingId ? '(unchanged)' : 'username'}
              class="w-full border border-neutral-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-neutral-700 mb-1" for="src-password">
              {$t('import.sources.fieldPassword')}
              {#if editingId}
                <span class="text-neutral-400 font-normal">({$t('import.sources.fieldKeepExisting')})</span>
              {/if}
            </label>
            <input
              id="src-password"
              type="password"
              autocomplete="new-password"
              bind:value={formPassword}
              placeholder={editingId ? '(unchanged)' : 'password'}
              class="w-full border border-neutral-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
            />
          </div>

        {:else}
          <!-- Planning Center placeholder -->
          <div class="sm:col-span-2 p-4 bg-neutral-50 border border-neutral-200 rounded text-neutral-600 text-sm">
            {$t('import.sources.planningCenterPlaceholder')}
          </div>
        {/if}
      </div>

      <div class="mt-5 flex items-center gap-3 justify-end">
        <button
          onclick={resetForm}
          class="px-4 py-2 text-neutral-600 font-semibold hover:text-neutral-900 transition-colors"
        >
          {$t('import.sources.cancel')}
        </button>
        <button
          onclick={saveSource}
          disabled={saving}
          class="px-5 py-2 bg-primary-600 text-white font-semibold rounded-button hover:bg-primary-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {saving ? $t('import.sources.saving') : (editingId ? $t('import.sources.saveChanges') : $t('import.sources.createSource'))}
        </button>
      </div>
    </div>
  {/if}

  <!-- Sources table -->
  <div class="bg-white rounded-lg border border-neutral-200 shadow-sm">
    <div class="px-6 py-4 border-b border-neutral-200 flex items-center justify-between">
      <h2 class="text-base font-semibold text-neutral-900">{$t('import.sources.tableTitle')}</h2>
      {#if !showForm}
        <button
          onclick={startCreate}
          class="px-4 py-1.5 bg-primary-600 text-white text-sm font-semibold rounded-button hover:bg-primary-700 transition-colors"
        >
          {$t('import.sources.addNew')}
        </button>
      {/if}
    </div>

    {#if loading}
      <div class="px-6 py-8 text-center text-neutral-400 text-sm">{$t('import.sources.loading')}</div>
    {:else if sources.length === 0}
      <div class="px-6 py-8 text-center text-neutral-400 text-sm">
        {$t('import.sources.noSources')}
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-neutral-50 border-b border-neutral-200">
            <tr>
              <th class="text-left px-4 py-3 font-semibold text-neutral-700">{$t('import.sources.colName')}</th>
              <th class="text-left px-4 py-3 font-semibold text-neutral-700">{$t('import.sources.colType')}</th>
              <th class="text-center px-4 py-3 font-semibold text-neutral-700">{$t('import.sources.colCredentials')}</th>
              <th class="text-left px-4 py-3 font-semibold text-neutral-700">{$t('import.sources.colCreated')}</th>
              <th class="text-right px-4 py-3 font-semibold text-neutral-700">{$t('import.sources.colActions')}</th>
            </tr>
          </thead>
          <tbody>
            {#each sources as source, i (source.id)}
              <tr class="border-b border-neutral-100 {i % 2 === 1 ? 'bg-neutral-50' : ''}">
                <td class="px-4 py-3 font-medium text-neutral-900">
                  <a href="/import/{source.id}" class="hover:text-primary-600 hover:underline">
                    {source.name}
                  </a>
                </td>
                <td class="px-4 py-3 text-neutral-600">{providerTypeLabel(source.provider_type)}</td>
                <td class="px-4 py-3 text-center">
                  {#if source.has_credentials}
                    <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-success-100 text-success-800">
                      {$t('import.sources.credentialsSet')}
                    </span>
                  {:else}
                    <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-warning-100 text-warning-700">
                      {$t('import.sources.credentialsNotSet')}
                    </span>
                  {/if}
                </td>
                <td class="px-4 py-3 text-neutral-500 whitespace-nowrap">{formatDate(source.created_at)}</td>
                <td class="px-4 py-3 text-right whitespace-nowrap">
                  <a
                    href="/import/{source.id}"
                    class="text-primary-600 hover:text-primary-800 font-medium text-sm mr-3"
                  >
                    {$t('import.sources.import')}
                  </a>
                  <button
                    onclick={() => startEdit(source)}
                    class="text-neutral-600 hover:text-neutral-800 font-medium text-sm mr-3"
                  >
                    {$t('import.sources.edit')}
                  </button>
                  <button
                    onclick={() => deleteSource(source)}
                    class="text-danger-600 hover:text-danger-800 font-medium text-sm"
                  >
                    {$t('import.sources.delete')}
                  </button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </div>

</div>
