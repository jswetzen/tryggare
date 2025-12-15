<script lang="ts">
  /**
   * SuccessToast Component
   *
   * Displays a success message in the top-right corner
   * Auto-dismisses after 3 seconds with slide-in animation
   */
  import { onMount } from 'svelte';

  let {
    message,
    onClose
  }: {
    message: string;
    onClose: () => void;
  } = $props();

  let visible = $state(true);

  onMount(() => {
    const timer = setTimeout(() => {
      visible = false;
      setTimeout(onClose, 300); // Wait for fade-out animation
    }, 3000);
    return () => clearTimeout(timer);
  });

  function handleDismiss() {
    visible = false;
    setTimeout(onClose, 300); // Wait for fade-out animation
  }
</script>

{#if visible}
  <div
    class="fixed top-4 right-4 bg-success-50 text-success-700 border border-success-600 px-4 py-3 rounded-md shadow-lg flex items-center gap-3 z-50 animate-slide-in"
    role="alert"
    aria-live="polite"
    data-testid="success-toast"
  >
    <span class="text-xl flex-shrink-0">✓</span>
    <span class="font-semibold flex-1">{message}</span>
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
  </div>
{/if}

<style>
  @keyframes slide-in {
    from {
      transform: translateX(100%);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }

  .animate-slide-in {
    animation: slide-in 0.3s ease-out;
  }
</style>
