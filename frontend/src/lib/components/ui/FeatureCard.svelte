<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    title: string;
    /** Icon-tile tone: blue (primary) or green (accent). */
    tone?: 'blue' | 'green';
    /** Optional icon snippet (stroke-only SVG, currentColor). */
    icon?: Snippet;
    class?: string;
    /** Body text. */
    children: Snippet;
  }

  let { title, tone = 'blue', icon, class: className = '', children }: Props = $props();
</script>

<div class="feature-card {className}" data-tone={tone}>
  {#if icon}
    <div class="icon-tile">{@render icon()}</div>
  {/if}
  <h3 class="title">{title}</h3>
  <p class="body">{@render children()}</p>
</div>

<style>
  .feature-card {
    background: var(--surface);
    border: 1px solid var(--ink-line);
    border-radius: var(--radius-lg);
    padding: 28px 28px 24px;
    transition:
      box-shadow 0.2s ease,
      transform 0.2s ease;
  }
  .feature-card:hover {
    box-shadow: var(--shadow-sm);
    transform: translateY(-2px);
  }
  .icon-tile {
    width: 44px;
    height: 44px;
    border-radius: 11px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 18px;
    background: var(--brand-primary-tint);
    color: var(--brand-primary);
  }
  .feature-card[data-tone='green'] .icon-tile {
    background: var(--brand-accent-tint);
    color: var(--brand-accent);
  }
  .title {
    font-size: 1rem;
    font-weight: 700;
    letter-spacing: -0.01em;
    margin: 0 0 7px;
  }
  .body {
    font-size: 0.875rem;
    color: var(--ink-soft);
    line-height: 1.55;
    margin: 0;
  }
</style>
