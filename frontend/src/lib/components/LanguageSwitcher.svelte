<script lang="ts">
  import { locale } from 'svelte-i18n';

  const languages = [
    { code: 'en', label: 'English' },
    { code: 'sv', label: 'Svenska' }
  ];

  function setLanguage(lang: string) {
    locale.set(lang);
    // localStorage and cookie are now handled automatically by i18n.ts
  }
</script>

<div class="flex gap-2">
  {#each languages as lang}
    <button
      data-testid="language-{lang.code}"
      onclick={() => setLanguage(lang.code)}
      class="px-3 py-1 rounded-button text-sm transition-colors {$locale === lang.code ? 'bg-primary-600 text-white' : 'bg-neutral-200 text-neutral-700 hover:bg-neutral-300'}"
    >
      {lang.label}
    </button>
  {/each}
</div>
