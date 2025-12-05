<script lang="ts">
  import type { Snippet } from 'svelte';

  type InputSize = 'sm' | 'md' | 'lg';
  type InputType = 'text' | 'email' | 'password' | 'number' | 'tel' | 'url' | 'search';

  interface Props {
    id?: string;
    name?: string;
    type?: InputType;
    value?: string | number;
    placeholder?: string;
    label?: string;
    error?: string;
    helperText?: string;
    disabled?: boolean;
    required?: boolean;
    size?: InputSize;
    class?: string;
    prefixIcon?: Snippet;
    suffixIcon?: Snippet;
    oninput?: (event: Event) => void;
    onblur?: (event: FocusEvent) => void;
    onfocus?: (event: FocusEvent) => void;
  }

  let {
    id,
    name,
    type = 'text',
    value = $bindable(''),
    placeholder = '',
    label,
    error,
    helperText,
    disabled = false,
    required = false,
    size = 'md',
    class: className = '',
    prefixIcon,
    suffixIcon,
    oninput,
    onblur,
    onfocus
  }: Props = $props();

  const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`;

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

  const inputClass = `${baseStyles} ${sizeStyles[size]} ${stateStyles} ${disabledStyles} ${className}`.trim();
</script>

{#if label}
  <label for={inputId} class="block text-sm font-semibold text-neutral-700 mb-1">
    {label}
    {#if required}
      <span class="text-danger-600">*</span>
    {/if}
  </label>
{/if}

<div class="relative">
  {#if prefixIcon}
    <div class="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-600">
      {@render prefixIcon()}
    </div>
  {/if}

  <input
    {type}
    id={inputId}
    {name}
    bind:value
    {placeholder}
    {disabled}
    {required}
    class={inputClass}
    class:pl-10={prefixIcon}
    class:pr-10={suffixIcon}
    {oninput}
    {onblur}
    {onfocus}
  />

  {#if suffixIcon}
    <div class="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-600">
      {@render suffixIcon()}
    </div>
  {/if}
</div>

{#if error}
  <p class="mt-1 text-sm text-danger-600">{error}</p>
{:else if helperText}
  <p class="mt-1 text-sm text-neutral-600">{helperText}</p>
{/if}
