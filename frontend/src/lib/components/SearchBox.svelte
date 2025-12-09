<script lang="ts">
  import { t } from 'svelte-i18n';
  import Icon from '$lib/components/ui/Icon.svelte';

  interface Props {
    value: string;
    placeholder?: string;
    label?: string;
    onInput?: (value: string) => void;
  }

  let {
    value = $bindable(''),
    placeholder,
    label,
    onInput
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

<div class="relative mb-4">
  <Icon
    name="search"
    size="sm"
    class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
  />
  <input
    id={inputId}
    type="text"
    bind:value={value}
    oninput={handleInput}
    onkeydown={handleKeyDown}
    placeholder={displayPlaceholder}
    class="w-full pl-10 pr-10 py-3 border-2 border-blue-500 rounded-lg bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
    data-testid="family-search"
  />
  {#if value}
    <button
      onclick={clearSearch}
      class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
      aria-label="Clear search"
      data-testid="clear-search-button"
    >
      <Icon name="x" size="sm" />
    </button>
  {/if}
</div>
