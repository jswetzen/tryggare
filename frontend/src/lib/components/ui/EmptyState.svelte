<script lang="ts">
  import type { Snippet } from 'svelte';

  type StateType = 'empty' | 'loading' | 'error' | 'success';

  interface Props {
    type?: StateType;
    title: string;
    description?: string;
    icon?: Snippet;
    action?: Snippet;
    class?: string;
  }

  let {
    type = 'empty',
    title,
    description,
    icon,
    action,
    class: className = ''
  }: Props = $props();

  const typeColors = {
    empty: 'text-slate-400',
    loading: 'text-primary-500',
    error: 'text-danger-500',
    success: 'text-success-500'
  };
</script>

<div class="text-center p-8 bg-slate-50 border-2 border-dashed border-slate-300 rounded-card {className}">
  {#if icon}
    <div class="mx-auto h-12 w-12 mb-4 {typeColors[type]}">
      {@render icon()}
    </div>
  {/if}

  <h3 class="text-lg font-semibold text-slate-700 mb-2">
    {title}
  </h3>

  {#if description}
    <p class="text-slate-500 text-sm mb-4">
      {description}
    </p>
  {/if}

  {#if action}
    <div class="mt-4">
      {@render action()}
    </div>
  {/if}
</div>
