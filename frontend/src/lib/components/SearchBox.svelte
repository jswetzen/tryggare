<script lang="ts">
  import { t } from 'svelte-i18n';

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
  let displayLabel = $derived(label ?? $t('common.searchFamilies'));

  // Generate unique ID for label association
  const inputId = `search-input-${Math.random().toString(36).substr(2, 9)}`;

  function handleInput(e: Event) {
    const target = e.target as HTMLInputElement;
    value = target.value;
    if (onInput) {
      onInput(target.value);
    }
  }
</script>

<div class="border-2 border-primary-500 rounded-card p-3 mb-5 bg-primary-50">
  <label for={inputId} class="block font-semibold text-primary-900 mb-2 text-sm">
    {displayLabel}
  </label>
  <input
    id={inputId}
    data-testid="family-search"
    type="text"
    {value}
    oninput={handleInput}
    placeholder={displayPlaceholder}
    class="w-full px-3 py-2 border border-neutral-300 rounded-input bg-white text-sm focus:border-primary-600 focus:ring-2 focus:ring-primary-500"
  />
</div>
