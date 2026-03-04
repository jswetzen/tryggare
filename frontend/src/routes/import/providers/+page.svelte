<script lang="ts">
  import { onMount } from 'svelte';
  import { t } from 'svelte-i18n';
  import { importApi } from '$lib/api/importService';
  import type { ImportProvider, ImportProviderWrite } from '$lib/api/types';

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------

  let providers = $state<ImportProvider[]>([]);
  let loading = $state(true);
  let error = $state('');
  let formError = $state('');
  let saving = $state(false);

  // Form visibility
  let showForm = $state(false);
  let editingId = $state<string | null>(null);

  // Form fields
  let formName = $state('');
  let formLoginUrl = $state('');
  let formExportUrl = $state('');
  let formExportBody = $state('');
  let formUsername = $state('');
  let formPassword = $state('');

  // ---------------------------------------------------------------------------
  // Lifecycle
  // ---------------------------------------------------------------------------

  onMount(async () => {
    await loadProviders();
  });

  async function loadProviders() {
    loading = true;
    error = '';
    try {
      providers = await importApi.listProviders();
    } catch {
      error = 'Failed to load providers.';
    } finally {
      loading = false;
    }
  }

  // ---------------------------------------------------------------------------
  // Form helpers
  // ---------------------------------------------------------------------------

  function resetForm() {
    formName = '';
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

  function startEdit(provider: ImportProvider) {
    editingId = provider.id;
    formName = provider.name;
    formLoginUrl = provider.login_url;
    formExportUrl = provider.export_url;
    formExportBody = provider.export_body;
    formUsername = '';
    formPassword = '';
    formError = '';
    showForm = true;
  }

  async function saveProvider() {
    formError = '';
    if (!formName.trim()) { formError = 'Name is required.'; return; }
    if (!formLoginUrl.trim()) { formError = 'Login URL is required.'; return; }
    if (!formExportUrl.trim()) { formError = 'Export URL is required.'; return; }

    saving = true;
    try {
      const data: ImportProviderWrite = {
        name: formName.trim(),
        login_url: formLoginUrl.trim(),
        export_url: formExportUrl.trim(),
        export_body: formExportBody.trim(),
      };
      if (formUsername.trim()) data.username = formUsername.trim();
      if (formPassword) data.password = formPassword;

      if (editingId) {
        await importApi.updateProvider(editingId, data);
      } else {
        await importApi.createProvider(data);
      }
      resetForm();
      await loadProviders();
    } catch (e: unknown) {
      const err = e as { details?: { name?: string[]; login_url?: string[] } };
      formError = err?.details?.name?.[0] ?? err?.details?.login_url?.[0] ?? 'Save failed.';
    } finally {
      saving = false;
    }
  }

  async function deleteProvider(provider: ImportProvider) {
    if (!confirm(`Delete provider "${provider.name}"? This cannot be undone.`)) return;
    try {
      await importApi.deleteProvider(provider.id);
      await loadProviders();
    } catch {
      error = 'Failed to delete provider.';
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
</script>

<svelte:head>
  <title>Import Providers — {$t('import.pageTitle')}</title>
</svelte:head>

<div class="max-w-4xl mx-auto">

  <!-- Header -->
  <div class="mb-6">
    <a href="/import" class="text-sm text-primary-600 hover:underline font-medium">
      ← {$t('import.backToEvents')}
    </a>
    <h1 class="mt-2 text-2xl font-bold text-neutral-900">Import Providers</h1>
    <p class="mt-1 text-neutral-600">Configure external booking system connections for automatic data fetching.</p>
  </div>

  <!-- Global error -->
  {#if error}
    <div class="mb-4 p-3 bg-danger-50 border border-danger-200 rounded text-danger-700 text-sm">
      {error}
    </div>
  {/if}

  <!-- New provider form -->
  {#if showForm}
    <div class="mb-6 bg-white rounded-lg border border-neutral-200 shadow-sm p-6">
      <h2 class="text-base font-semibold text-neutral-900 mb-4">
        {editingId ? 'Edit Provider' : 'New Provider'}
      </h2>

      {#if formError}
        <div class="mb-4 p-3 bg-danger-50 border border-danger-200 rounded text-danger-700 text-sm">
          {formError}
        </div>
      {/if}

      <div class="grid gap-4 sm:grid-cols-2">
        <div class="sm:col-span-2">
          <label class="block text-sm font-medium text-neutral-700 mb-1" for="prov-name">
            Name <span class="text-danger-500">*</span>
          </label>
          <input
            id="prov-name"
            type="text"
            bind:value={formName}
            placeholder="e.g. FestivalPro Production"
            class="w-full border border-neutral-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-neutral-700 mb-1" for="prov-login-url">
            Login URL <span class="text-danger-500">*</span>
          </label>
          <input
            id="prov-login-url"
            type="url"
            bind:value={formLoginUrl}
            placeholder="https://example.com/?login"
            class="w-full border border-neutral-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-neutral-700 mb-1" for="prov-export-url">
            Export URL <span class="text-danger-500">*</span>
          </label>
          <input
            id="prov-export-url"
            type="url"
            bind:value={formExportUrl}
            placeholder="https://example.com/?advancedExport"
            class="w-full border border-neutral-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
          />
        </div>

        <div class="sm:col-span-2">
          <label class="block text-sm font-medium text-neutral-700 mb-1" for="prov-export-body">
            Export POST Body
            <span class="text-neutral-400 font-normal">(paste from browser network capture)</span>
          </label>
          <textarea
            id="prov-export-body"
            bind:value={formExportBody}
            rows="5"
            placeholder="QUERYQ=CODE*__EQ__*...&EVENTID=5781&EXPORT=JSON&ETICKETS=1&..."
            class="w-full border border-neutral-300 rounded px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary-400 resize-y"
          ></textarea>
          <p class="mt-1 text-xs text-neutral-400">
            Raw form-encoded body for the export POST request. Contains event-specific parameters
            (EVENTID, QUERYQ, etc.) but no credentials.
          </p>
        </div>

        <div>
          <label class="block text-sm font-medium text-neutral-700 mb-1" for="prov-username">
            Username
            {#if editingId}
              <span class="text-neutral-400 font-normal">(leave blank to keep existing)</span>
            {/if}
          </label>
          <input
            id="prov-username"
            type="text"
            autocomplete="off"
            bind:value={formUsername}
            placeholder={editingId ? '(unchanged)' : 'username'}
            class="w-full border border-neutral-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-neutral-700 mb-1" for="prov-password">
            Password
            {#if editingId}
              <span class="text-neutral-400 font-normal">(leave blank to keep existing)</span>
            {/if}
          </label>
          <input
            id="prov-password"
            type="password"
            autocomplete="new-password"
            bind:value={formPassword}
            placeholder={editingId ? '(unchanged)' : 'password'}
            class="w-full border border-neutral-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
          />
        </div>
      </div>

      <div class="mt-5 flex items-center gap-3 justify-end">
        <button
          onclick={resetForm}
          class="px-4 py-2 text-neutral-600 font-semibold hover:text-neutral-900 transition-colors"
        >
          Cancel
        </button>
        <button
          onclick={saveProvider}
          disabled={saving}
          class="px-5 py-2 bg-primary-600 text-white font-semibold rounded-button hover:bg-primary-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {saving ? 'Saving…' : (editingId ? 'Save Changes' : 'Create Provider')}
        </button>
      </div>
    </div>
  {/if}

  <!-- Providers table -->
  <div class="bg-white rounded-lg border border-neutral-200 shadow-sm">
    <div class="px-6 py-4 border-b border-neutral-200 flex items-center justify-between">
      <h2 class="text-base font-semibold text-neutral-900">Providers</h2>
      {#if !showForm}
        <button
          onclick={startCreate}
          class="px-4 py-1.5 bg-primary-600 text-white text-sm font-semibold rounded-button hover:bg-primary-700 transition-colors"
        >
          + New Provider
        </button>
      {/if}
    </div>

    {#if loading}
      <div class="px-6 py-8 text-center text-neutral-400 text-sm">Loading…</div>
    {:else if providers.length === 0}
      <div class="px-6 py-8 text-center text-neutral-400 text-sm">
        No providers configured yet. Create one to enable automatic data fetching.
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-neutral-50 border-b border-neutral-200">
            <tr>
              <th class="text-left px-4 py-3 font-semibold text-neutral-700">Name</th>
              <th class="text-left px-4 py-3 font-semibold text-neutral-700">Login URL</th>
              <th class="text-left px-4 py-3 font-semibold text-neutral-700">Export URL</th>
              <th class="text-center px-4 py-3 font-semibold text-neutral-700">Credentials</th>
              <th class="text-left px-4 py-3 font-semibold text-neutral-700">Created</th>
              <th class="text-right px-4 py-3 font-semibold text-neutral-700">Actions</th>
            </tr>
          </thead>
          <tbody>
            {#each providers as provider, i (provider.id)}
              <tr class="border-b border-neutral-100 {i % 2 === 1 ? 'bg-neutral-50' : ''}">
                <td class="px-4 py-3 font-medium text-neutral-900">{provider.name}</td>
                <td class="px-4 py-3 text-neutral-600 font-mono text-xs max-w-48 truncate" title={provider.login_url}>
                  {provider.login_url}
                </td>
                <td class="px-4 py-3 text-neutral-600 font-mono text-xs max-w-48 truncate" title={provider.export_url}>
                  {provider.export_url}
                </td>
                <td class="px-4 py-3 text-center">
                  {#if provider.has_credentials}
                    <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-success-100 text-success-800">
                      Set
                    </span>
                  {:else}
                    <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-warning-100 text-warning-700">
                      Not set
                    </span>
                  {/if}
                </td>
                <td class="px-4 py-3 text-neutral-500 whitespace-nowrap">{formatDate(provider.created_at)}</td>
                <td class="px-4 py-3 text-right whitespace-nowrap">
                  <button
                    onclick={() => startEdit(provider)}
                    class="text-primary-600 hover:text-primary-800 font-medium text-sm mr-3"
                  >
                    Edit
                  </button>
                  <button
                    onclick={() => deleteProvider(provider)}
                    class="text-danger-600 hover:text-danger-800 font-medium text-sm"
                  >
                    Delete
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
