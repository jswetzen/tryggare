<script lang="ts">
  import { locale, t } from 'svelte-i18n';
  import Icon from '$lib/components/ui/Icon.svelte';

  const languages = [
    { code: 'en', label: 'English' },
    { code: 'sv', label: 'Svenska' }
  ];

  let open = $state(false);
  let container: HTMLDivElement;

  // svelte-i18n locale may be region-tagged (e.g. "en-US"); take the base.
  const current = $derived(($locale ?? 'en').slice(0, 2).toLowerCase());

  function setLanguage(lang: string) {
    locale.set(lang);
    // localStorage + cookie are handled by i18n.ts
    open = false;
  }

  function handleWindowClick(e: MouseEvent) {
    if (open && container && !container.contains(e.target as Node)) {
      open = false;
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') open = false;
  }
</script>

<svelte:window onclick={handleWindowClick} onkeydown={handleKeydown} />

<div class="relative" bind:this={container}>
  <button
    type="button"
    onclick={() => (open = !open)}
    class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-button text-sm font-semibold text-neutral-700 hover:bg-neutral-100 hover:text-neutral-900 transition-colors"
    aria-haspopup="listbox"
    aria-expanded={open}
    aria-label={$t('nav.changeLanguage')}
    data-testid="language-toggle"
  >
    <!-- Globe — stroke-only, Lucide-style -->
    <svg
      width="15"
      height="15"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      class="opacity-70"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="10" />
      <path d="M2 12h20M12 2a15.3 15.3 0 010 20M12 2a15.3 15.3 0 000 20" />
    </svg>
    <span>{current.toUpperCase()}</span>
    <Icon name="chevron-down" size="xs" class="opacity-70" />
  </button>

  {#if open}
    <div
      class="absolute right-0 top-[calc(100%+6px)] min-w-[140px] bg-white rounded-card shadow-elevation-3 ring-1 ring-neutral-200 overflow-hidden z-50 py-1"
      role="listbox"
    >
      {#each languages as lang}
        {@const active = current === lang.code}
        <button
          type="button"
          data-testid="language-{lang.code}"
          onclick={() => setLanguage(lang.code)}
          class="flex items-center gap-2 w-full text-left px-3.5 py-2 text-sm font-semibold transition-colors hover:bg-neutral-100 {active
            ? 'text-neutral-900'
            : 'text-neutral-700'}"
          role="option"
          aria-selected={active}
        >
          <span>{lang.label}</span>
          <span class="ml-auto text-success-600 {active ? '' : 'opacity-0'}" aria-hidden="true">✓</span>
        </button>
      {/each}
    </div>
  {/if}
</div>
