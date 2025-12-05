<script lang="ts">
  import type { Snippet } from 'svelte';

  type AlertType = 'success' | 'error' | 'warning' | 'info';

  interface Props {
    type: AlertType;
    title?: string;
    dismissible?: boolean;
    children?: Snippet;
    class?: string;
    ondismiss?: () => void;
  }

  let {
    type,
    title,
    dismissible = false,
    children,
    class: className = '',
    ondismiss
  }: Props = $props();

  let visible = $state(true);

  const baseStyles = 'p-4 rounded-md border';

  const typeStyles = {
    success: 'bg-success-50 text-success-700 border-success-600',
    error: 'bg-danger-50 text-danger-800 border-danger-200',
    warning: 'bg-warning-50 text-warning-800 border-warning-600',
    info: 'bg-info-50 text-primary-700 border-primary-500'
  };

  const alertClass = `${baseStyles} ${typeStyles[type]} ${className}`.trim();

  function handleDismiss() {
    visible = false;
    ondismiss?.();
  }
</script>

{#if visible}
  <div class={alertClass} role="alert">
    <div class="flex items-start justify-between gap-3">
      <div class="flex-1">
        {#if title}
          <h3 class="font-semibold mb-1">{title}</h3>
        {/if}
        {#if children}
          <div class="text-sm">
            {@render children()}
          </div>
        {/if}
      </div>
      {#if dismissible}
        <button
          type="button"
          class="flex-shrink-0 text-current hover:opacity-70 transition-opacity"
          onclick={handleDismiss}
          aria-label="Dismiss"
        >
          <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
          </svg>
        </button>
      {/if}
    </div>
  </div>
{/if}
