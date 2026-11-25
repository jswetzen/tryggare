<script lang="ts">
  import { t } from 'svelte-i18n';
  import type { ToolStatus } from './assistantStore';

  let { tools }: { tools: ToolStatus[] } = $props();

  const KNOWN = ['get_capabilities', 'get_current_spec', 'validate_spec', 'diff_spec', 'propose_spec'];
  // The wire sends our tool names or "unknown"; anything else still shows a label.
  const label = (tool: string) => $t(`assistant.tool.${KNOWN.includes(tool) ? tool : 'unknown'}`);
</script>

{#if tools.length > 0}
  <ul class="tools" data-testid="assistant-tools">
    {#each tools as tool (tool.callId)}
      <li class="chip" data-state={tool.state}>
        {#if tool.state === 'running'}
          <span class="spinner" aria-hidden="true"></span>
        {:else}
          <span aria-hidden="true">{tool.state === 'done' ? '✓' : '✗'}</span>
        {/if}
        <span>{label(tool.tool)}</span>
        <span class="sr-only">({$t(`assistant.tool.state.${tool.state}`)})</span>
      </li>
    {/each}
  </ul>
{/if}

<style>
  .tools {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2);
    margin: 0;
    padding: 0;
    list-style: none;
  }
  .chip {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-1) var(--space-3);
    border-radius: var(--radius-pill);
    background: var(--surface-2);
    color: var(--ink-soft);
    font-size: var(--type-caption);
    font-weight: var(--weight-medium);
  }
  .chip[data-state='running'] {
    background: var(--brand-primary-tint);
    color: var(--brand-primary-mid);
  }
  .chip[data-state='failed'] {
    background: var(--danger-tint);
    color: var(--danger);
  }
  .spinner {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    border: 2px solid currentColor;
    border-right-color: transparent;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
  /* The spinner is the only motion here; a static ring still reads as "busy". */
  @media (prefers-reduced-motion: reduce) {
    .spinner {
      animation: none;
    }
  }
</style>
