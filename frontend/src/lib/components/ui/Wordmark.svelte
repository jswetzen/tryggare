<script lang="ts">
  interface Props {
    /**
     * Show the provisional ".app" suffix. Default false: the canonical
     * wordmark in the app is "Tryggare" alone (the .app domain isn't owned).
     */
    showTld?: boolean;
    /** Extra classes (e.g. a Tailwind font-size like text-xl). */
    class?: string;
  }

  let { showTld = false, class: className = '' }: Props = $props();
</script>

<!-- Brand wordmark. "Tryggare" is a proper noun — not translated. -->
<span class="wordmark {className}">
  Tryggare{#if showTld}<span class="tld">.app</span>{/if}
</span>

<style>
  .wordmark {
    font-weight: 700;
    letter-spacing: -0.02em;
    color: var(--ink);
    white-space: nowrap;
  }
  .tld {
    color: var(--brand-primary);
  }
</style>
