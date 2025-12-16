<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    title: string;
    actions?: Snippet;
    class?: string;
  }

  let {
    title,
    actions,
    class: className = ''
  }: Props = $props();
</script>

<div class="mb-5 {className}">
  <div class="flex items-center justify-between gap-4">
    <h1 class="text-3xl font-bold text-blue-900">{title}</h1>

    {#if actions}
      <div class="flex items-center gap-2">
        {@render actions()}
      </div>
    {/if}
  </div>
</div>
