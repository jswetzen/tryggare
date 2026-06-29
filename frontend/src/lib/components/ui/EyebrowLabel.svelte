<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    /** Dash + text color. Defaults to the brand primary. */
    color?: string;
    /** Center the label (e.g. above a centered section heading). */
    center?: boolean;
    class?: string;
    children: Snippet;
  }

  let { color = 'var(--brand-primary)', center = false, class: className = '', children }: Props =
    $props();
</script>

<!-- Small uppercase section label with a leading dash. Typographic device only. -->
<div class="eyebrow-label {className}" class:center style="--eyebrow-color: {color}">
  <span class="dash"></span>
  {@render children()}
</div>

<style>
  .eyebrow-label {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: var(--type-eyebrow, 0.78rem);
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--eyebrow-color);
    margin-bottom: 16px;
  }
  .eyebrow-label.center {
    justify-content: center;
  }
  .dash {
    display: block;
    width: 20px;
    height: 2px;
    background: var(--eyebrow-color);
    border-radius: 2px;
  }
</style>
