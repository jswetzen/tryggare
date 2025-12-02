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

<div class="border-2 border-blue-500 rounded-md p-3 mb-5 bg-blue-50">
  <label for={inputId} class="block font-semibold text-blue-900 mb-2 text-sm">
    {displayLabel}
  </label>
  <input
    id={inputId}
    data-testid="family-search"
    type="text"
    {value}
    oninput={handleInput}
    placeholder={displayPlaceholder}
    class="w-full px-3 py-2 border border-slate-300 rounded bg-white text-sm"
  />
</div>
