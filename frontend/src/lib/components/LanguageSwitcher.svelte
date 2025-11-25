<script lang="ts">
  import { locale } from 'svelte-i18n';

  const languages = [
    { code: 'en', label: 'English' },
    { code: 'sv', label: 'Svenska' }
  ];

  function setLanguage(lang: string) {
    locale.set(lang);
    // Save to cookie for Django backend
    document.cookie = `django_language=${lang}; path=/; SameSite=Lax`;
  }
</script>

<div class="flex gap-2">
  {#each languages as lang}
    <button
      onclick={() => setLanguage(lang.code)}
      class="px-3 py-1 rounded text-sm transition-colors {$locale === lang.code ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}"
    >
      {lang.label}
    </button>
  {/each}
</div>
