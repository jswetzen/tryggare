<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    maxWidth?: '3xl' | '4xl' | '5xl' | '6xl' | '7xl' | 'full';
    children?: Snippet;
    class?: string;
  }

  let { maxWidth = '7xl', children, class: className = '' }: Props = $props();

  const maxWidthClasses = {
    '3xl': 'max-w-3xl',
    '4xl': 'max-w-4xl',
    '5xl': 'max-w-5xl',
    '6xl': 'max-w-6xl',
    '7xl': 'max-w-7xl',
    'full': 'max-w-full'
  };
</script>

<div class="{maxWidthClasses[maxWidth]} mx-auto {className}">
  {@render children?.()}
</div>
