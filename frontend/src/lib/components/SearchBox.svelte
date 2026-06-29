<script lang="ts">
  import { t } from 'svelte-i18n';
  import Icon from '$lib/components/ui/Icon.svelte';

  interface Props {
    value: string;
    placeholder?: string;
    label?: string;
    onInput?: (value: string) => void;
    onQrScan?: () => void;
  }

  let {
    value = $bindable(''),
    placeholder,
    label,
    onInput,
    onQrScan
  }: Props = $props();

  // Use translation keys as defaults if not provided
  let displayPlaceholder = $derived(placeholder ?? $t('common.searchPlaceholder'));

  // Generate unique ID for label association
  const inputId = `search-input-${Math.random().toString(36).substr(2, 9)}`;

  function handleInput(e: Event) {
    const target = e.target as HTMLInputElement;
    value = target.value;
    if (onInput) {
      onInput(target.value);
    }
  }

  function handleKeyDown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      clearSearch();
    }
  }

  function clearSearch() {
    value = '';
    if (onInput) {
      onInput('');
    }
  }
</script>

{#if label}
  <div class="mb-2">
    <label for={inputId} class="block font-semibold text-primary-900 text-sm">
      {label}
    </label>
  </div>
{/if}

<div class="relative mb-2">
  <Icon
    name="search"
    size="sm"
    class="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400"
  />
  <input
    id={inputId}
    type="text"
    bind:value={value}
    oninput={handleInput}
    onkeydown={handleKeyDown}
    placeholder={displayPlaceholder}
    class="w-full pl-10 py-3 border-2 border-primary-500 rounded-card bg-primary-50 focus:outline-none focus:ring-2 focus:ring-primary-500 {onQrScan ? 'pr-20' : 'pr-10'}"
    data-testid="family-search"
  />
  {#if value}
    <button
      onclick={clearSearch}
      class="absolute top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600 {onQrScan ? 'right-10' : 'right-3'}"
      aria-label="Clear search"
      data-testid="clear-search-button"
    >
      <Icon name="x" size="sm" />
    </button>
  {/if}
  {#if onQrScan}
    <button
      onclick={onQrScan}
      class="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-primary-600"
      aria-label={$t('checkin.qrScanButton')}
      data-testid="qr-scan-button"
    >
      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
        <rect x="14" y="14" width="3" height="3"/><rect x="19" y="14" width="2" height="2"/><rect x="14" y="19" width="2" height="2"/><rect x="19" y="19" width="2" height="2"/>
      </svg>
    </button>
  {/if}
</div>
