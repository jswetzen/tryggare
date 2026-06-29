<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    /** Glyph in the tile. Allowed glyphs only: ✓ ✗ →. */
    icon?: string;
    class?: string;
    children: Snippet;
  }

  let { icon = '✓', class: className = '', children }: Props = $props();
</script>

<!-- Floating white "Checked in" style badge with an accent tile. -->
<span class="status-badge {className}">
  <span class="tile">{icon}</span>
  {@render children()}
</span>

<style>
  .status-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: #fff;
    border-radius: 12px;
    padding: 10px 14px;
    box-shadow: var(--shadow-md);
    font-size: 0.8rem;
    font-weight: 600;
    white-space: nowrap;
  }
  .tile {
    width: 28px;
    height: 28px;
    border-radius: 8px;
    background: var(--brand-accent-tint);
    color: var(--brand-accent);
    display: flex;
    align-items: center;
    justify-content: center;
  }
</style>
