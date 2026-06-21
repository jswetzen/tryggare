<script lang="ts">
  import { onMount } from 'svelte';
  import { t } from 'svelte-i18n';
  import { privacyApi } from '$lib/api/services';
  import type { PrivacyInfoResponse } from '$lib/api/types';

  let info = $state<PrivacyInfoResponse | null>(null);

  onMount(() => {
    privacyApi
      .getInfo()
      .then((i) => (info = i))
      .catch((e) => console.error('Failed to load privacy info:', e));
  });

  const hasController = $derived(
    !!(info && (info.controller_name || info.contact_email || info.controller_url))
  );
</script>

<svelte:head>
  <title>{$t('privacy.pageTitle')}</title>
</svelte:head>

<main class="container mx-auto p-6 max-w-2xl">
  <div class="card">
    <h1 class="text-3xl font-bold mb-4">{$t('privacy.title')}</h1>
    <p class="text-neutral-700 mb-6">{$t('privacy.intro')}</p>

    <section class="mb-5">
      <h2 class="text-lg font-semibold mb-1">{$t('privacy.dataWeCollectTitle')}</h2>
      <p class="text-neutral-700">{$t('privacy.dataWeCollect')}</p>
    </section>

    <section class="mb-5">
      <h2 class="text-lg font-semibold mb-1">{$t('privacy.purposeTitle')}</h2>
      <p class="text-neutral-700">{$t('privacy.purpose')}</p>
    </section>

    <section class="mb-5">
      <h2 class="text-lg font-semibold mb-1">{$t('privacy.legalBasisTitle')}</h2>
      <p class="text-neutral-700">{$t('privacy.legalBasis')}</p>
    </section>

    <section class="mb-5">
      <h2 class="text-lg font-semibold mb-1">{$t('privacy.retentionTitle')}</h2>
      <p class="text-neutral-700">
        {$t('privacy.retention', { values: { days: info?.retention_days ?? '—' } })}
      </p>
    </section>

    <section class="mb-5">
      <h2 class="text-lg font-semibold mb-1">{$t('privacy.rightsTitle')}</h2>
      <p class="text-neutral-700">{$t('privacy.rights')}</p>
    </section>

    <section>
      <h2 class="text-lg font-semibold mb-1">{$t('privacy.controllerTitle')}</h2>
      {#if hasController}
        {#if info?.controller_name}
          <div class="text-neutral-800 font-semibold">{info.controller_name}</div>
        {/if}
        {#if info?.contact_email}
          <div class="text-neutral-700">
            {$t('privacy.contactEmail')}:
            <a href={`mailto:${info.contact_email}`} class="text-primary-600 hover:underline"
              >{info.contact_email}</a
            >
          </div>
        {/if}
        {#if info?.controller_url}
          <div class="text-neutral-700">
            {$t('privacy.website')}:
            <a
              href={info.controller_url}
              class="text-primary-600 hover:underline"
              target="_blank"
              rel="noopener noreferrer">{info.controller_url}</a
            >
          </div>
        {/if}
      {:else}
        <p class="text-neutral-600">{$t('privacy.controllerUnconfigured')}</p>
      {/if}

      {#if info?.privacy_policy_url}
        <div class="mt-3">
          <a
            href={info.privacy_policy_url}
            class="text-primary-600 hover:underline"
            target="_blank"
            rel="noopener noreferrer">{$t('privacy.fullPolicyLink')}</a
          >
        </div>
      {/if}
    </section>
  </div>
</main>
