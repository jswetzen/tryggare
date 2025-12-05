<script lang="ts">
  type ButtonVariant = 'checkin' | 'checkout' | 'checked-in' | 'checked-out' | 'family-checkin' | 'family-checkout';

  interface Props {
    variant: ButtonVariant;
    tooltip: string;
    onclick?: () => void;
    disabled?: boolean;
  }

  let { variant, tooltip, onclick, disabled = false }: Props = $props();

  const styles = {
    checkin: 'bg-success-600 hover:bg-success-700',
    checkout: 'bg-danger-600 hover:bg-danger-700',
    'checked-in': 'bg-neutral-500',
    'checked-out': 'bg-neutral-500',
    'family-checkin': 'bg-primary-600 hover:bg-primary-700',
    'family-checkout': 'bg-warning-600 hover:bg-warning-700'
  };

  const icons = {
    checkin: '✓',
    checkout: '→',
    'checked-in': '✓',
    'checked-out': '✓',
    'family-checkin': '✓✓',
    'family-checkout': '→→'
  };
</script>

<button
  {onclick}
  {disabled}
  title={tooltip}
  class="
    w-8 h-8 rounded-md text-white font-bold flex items-center justify-center
    {styles[variant]} {disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
    relative group
  "
>
  <span class={variant.includes('family') ? 'text-xs' : ''}>{icons[variant]}</span>
  <span class="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-1 bg-neutral-800 text-white text-xs rounded-button whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-10">
    {tooltip}
  </span>
</button>
