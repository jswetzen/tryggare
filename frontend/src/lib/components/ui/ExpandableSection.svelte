<script lang="ts">
  import type { Snippet } from 'svelte';
  import Icon from './Icon.svelte';
  import Badge from './Badge.svelte';

  interface Props {
    title: string;
    count?: number;
    expanded?: boolean;
    hint?: string;
    children?: Snippet;
    class?: string;
    ontoggle?: () => void;
  }

  let {
    title,
    count,
    expanded = $bindable(false),
    hint,
    children,
    class: className = '',
    ontoggle
  }: Props = $props();

  function toggle(e: MouseEvent) {
    e.preventDefault(); // Prevent default details/summary behavior
    expanded = !expanded;
    if (ontoggle) {
      ontoggle();
    }
  }
</script>

<details bind:open={expanded} class="rounded-card border border-neutral-300 {className}">
  <summary
    class="flex items-center justify-between p-4 cursor-pointer hover:bg-neutral-50 transition-colors select-none"
    onclick={toggle}
  >
    <div class="flex items-center gap-3">
      <Icon
        name={expanded ? 'chevron-down' : 'chevron-right'}
        size="sm"
        class="transition-transform text-neutral-600"
      />
      <h3 class="font-semibold text-neutral-700">{title}</h3>
      {#if count !== undefined}
        <Badge color="primary" size="sm">{count}</Badge>
      {/if}
    </div>
    {#if hint && !expanded}
      <span class="text-sm text-neutral-500 italic">{hint}</span>
    {/if}
  </summary>

  {#if expanded}
    <div class="p-4 pt-0 border-t border-neutral-200 mt-2">
      {@render children?.()}
    </div>
  {/if}
</details>
