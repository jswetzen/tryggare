<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    /** Show the leading accent dot. */
    dot?: boolean;
    class?: string;
    children: Snippet;
  }

  let { dot = true, class: className = '', children }: Props = $props();
</script>

<!-- Accent (green) pill — the trust / "live" signal. Use sparingly. -->
<span class="pill {className}">
  {#if dot}<span class="dot"></span>{/if}
  {@render children()}
</span>

<style>
  .pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: var(--brand-accent-tint);
    color: var(--brand-accent);
    font-size: var(--type-eyebrow, 0.78rem);
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    padding: 5px 12px;
    border-radius: var(--radius-pill, 100px);
  }
  .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--brand-accent);
  }
</style>
