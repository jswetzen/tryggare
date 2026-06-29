<script lang="ts">
  interface Props {
    /** true → accent ✓ row; false → danger ✗ row. */
    yes?: boolean;
    title: string;
    sub?: string;
    class?: string;
  }

  let { yes = true, title, sub = '', class: className = '' }: Props = $props();
</script>

<div class="comparison-row {className}" class:no={!yes}>
  <div class="disc">{yes ? '✓' : '✗'}</div>
  <div>
    <div class="title">{title}</div>
    {#if sub}<div class="sub">{sub}</div>{/if}
  </div>
</div>

<style>
  .comparison-row {
    display: flex;
    align-items: center;
    gap: 14px;
    background: #fff;
    border-radius: var(--radius, 10px);
    padding: 14px 18px;
    box-shadow: var(--shadow-xs);
  }
  .disc {
    width: 26px;
    height: 26px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.75rem;
    flex-shrink: 0;
    background: var(--brand-accent-tint);
    color: var(--brand-accent);
  }
  .comparison-row.no .disc {
    background: var(--danger-tint);
    color: var(--danger);
  }
  .title {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--ink);
  }
  .comparison-row.no .title {
    color: var(--ink-soft);
  }
  .sub {
    font-size: 0.78rem;
    color: var(--ink-faint);
  }
</style>
