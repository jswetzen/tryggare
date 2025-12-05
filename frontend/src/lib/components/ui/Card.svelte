<script lang="ts">
  import type { Snippet } from 'svelte';

  type CardVariant = 'default' | 'bordered' | 'elevated';
  type CardPadding = 'none' | 'sm' | 'md' | 'lg';

  interface Props {
    variant?: CardVariant;
    padding?: CardPadding;
    hover?: boolean;
    header?: Snippet;
    children?: Snippet;
    footer?: Snippet;
    class?: string;
  }

  let {
    variant = 'default',
    padding = 'md',
    hover = false,
    header,
    children,
    footer,
    class: className = ''
  }: Props = $props();

  const baseStyles = 'bg-white rounded-card';

  const variantStyles = {
    default: 'border-2 border-neutral-300',
    bordered: 'border border-neutral-300',
    elevated: 'shadow-elevation-2'
  };

  const hoverStyle = hover ? 'hover:shadow-elevation-3 transition-shadow cursor-pointer' : '';

  const containerClass = `${baseStyles} ${variantStyles[variant]} ${hoverStyle} ${className}`.trim();

  const paddingStyles = {
    none: '',
    sm: 'p-3',
    md: 'p-5',
    lg: 'p-6'
  };
</script>

<div class={containerClass}>
  {#if header}
    <div class="{paddingStyles[padding]} border-b border-neutral-200">
      {@render header()}
    </div>
  {/if}

  {#if children}
    <div class={paddingStyles[padding]}>
      {@render children()}
    </div>
  {/if}

  {#if footer}
    <div class="{paddingStyles[padding]} border-t border-neutral-200">
      {@render footer()}
    </div>
  {/if}
</div>
