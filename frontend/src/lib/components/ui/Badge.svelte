<script lang="ts">
  import type { Snippet } from 'svelte';

  type BadgeColor = 'primary' | 'secondary' | 'success' | 'danger' | 'warning' | 'info';
  type BadgeSize = 'sm' | 'md' | 'lg';
  type BadgeVariant = 'solid' | 'outline' | 'soft';

  interface Props {
    color?: BadgeColor;
    size?: BadgeSize;
    variant?: BadgeVariant;
    dot?: boolean;
    children?: Snippet;
    icon?: Snippet;
    class?: string;
  }

  let {
    color = 'primary',
    size = 'md',
    variant = 'solid',
    dot = false,
    children,
    icon,
    class: className = ''
  }: Props = $props();

  const baseStyles = 'inline-flex items-center font-semibold rounded-full whitespace-nowrap';

  const sizeStyles = {
    sm: 'px-2 py-0.5 text-xs gap-1',
    md: 'px-2.5 py-0.5 text-sm gap-1',
    lg: 'px-3 py-1 text-base gap-1.5'
  };

  const variantColorStyles = {
    solid: {
      primary: 'bg-primary-600 text-white',
      secondary: 'bg-neutral-600 text-white',
      success: 'bg-success-600 text-white',
      danger: 'bg-danger-600 text-white',
      warning: 'bg-warning-600 text-white',
      info: 'bg-info-500 text-white'
    },
    outline: {
      primary: 'bg-white text-primary-600 border-2 border-primary-600',
      secondary: 'bg-white text-neutral-600 border-2 border-neutral-600',
      success: 'bg-white text-success-600 border-2 border-success-600',
      danger: 'bg-white text-danger-600 border-2 border-danger-600',
      warning: 'bg-white text-warning-600 border-2 border-warning-600',
      info: 'bg-white text-info-500 border-2 border-info-500'
    },
    soft: {
      primary: 'bg-primary-100 text-primary-700',
      secondary: 'bg-neutral-200 text-neutral-700',
      success: 'bg-success-50 text-success-700',
      danger: 'bg-danger-50 text-danger-700',
      warning: 'bg-warning-50 text-warning-700',
      info: 'bg-info-50 text-primary-700'
    }
  };

  const badgeClass = `${baseStyles} ${sizeStyles[size]} ${variantColorStyles[variant][color]} ${className}`.trim();
</script>

<span class={badgeClass}>
  {#if dot}
    <span class="w-1.5 h-1.5 rounded-full bg-current"></span>
  {/if}
  {#if icon}
    {@render icon()}
  {/if}
  {#if children}
    {@render children()}
  {/if}
</span>
