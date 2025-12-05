<script lang="ts">
  type SelectSize = 'sm' | 'md' | 'lg';

  interface Props {
    id?: string;
    name?: string;
    value?: string | number;
    label?: string;
    error?: string;
    helperText?: string;
    disabled?: boolean;
    required?: boolean;
    size?: SelectSize;
    options: Array<{ value: string | number; label: string }>;
    placeholder?: string;
    class?: string;
    onchange?: (event: Event) => void;
  }

  let {
    id,
    name,
    value = $bindable(''),
    label,
    error,
    helperText,
    disabled = false,
    required = false,
    size = 'md',
    options,
    placeholder,
    class: className = '',
    onchange
  }: Props = $props();

  const selectId = id || `select-${Math.random().toString(36).substr(2, 9)}`;

  const baseStyles = 'w-full rounded-input border transition-colors focus:outline-none focus:ring-2 focus:ring-offset-0';

  const sizeStyles = {
    sm: 'px-2 py-1 text-sm',
    md: 'px-3 py-2 text-base',
    lg: 'px-4 py-3 text-lg'
  };

  const stateStyles = error
    ? 'border-danger-600 focus:ring-danger-500 focus:border-danger-600'
    : 'border-neutral-300 focus:ring-primary-500 focus:border-primary-600';

  const disabledStyles = disabled ? 'bg-neutral-100 cursor-not-allowed opacity-60' : 'bg-white';

  const selectClass = `${baseStyles} ${sizeStyles[size]} ${stateStyles} ${disabledStyles} ${className}`.trim();
</script>

{#if label}
  <label for={selectId} class="block text-sm font-semibold text-neutral-700 mb-1">
    {label}
    {#if required}
      <span class="text-danger-600">*</span>
    {/if}
  </label>
{/if}

<select
  id={selectId}
  {name}
  bind:value
  {disabled}
  {required}
  class={selectClass}
  {onchange}
>
  {#if placeholder}
    <option value="" disabled selected={!value}>{placeholder}</option>
  {/if}
  {#each options as option}
    <option value={option.value}>{option.label}</option>
  {/each}
</select>

{#if error}
  <p class="mt-1 text-sm text-danger-600">{error}</p>
{:else if helperText}
  <p class="mt-1 text-sm text-neutral-600">{helperText}</p>
{/if}
