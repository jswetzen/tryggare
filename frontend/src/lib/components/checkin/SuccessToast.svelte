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

  onMount(() => {
    const timer = setTimeout(onClose, 3000);
    return () => clearTimeout(timer);
  });
</script>

<div
  class="fixed top-4 right-4 bg-green-600 text-white px-4 py-3 rounded-lg shadow-lg flex items-center gap-2 z-50 animate-slide-in"
  role="alert"
  aria-live="polite"
  data-testid="success-toast"
>
  <span class="text-xl">✓</span>
  <span class="font-semibold">{message}</span>
</div>

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
