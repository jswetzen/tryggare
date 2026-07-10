<script lang="ts">
  /**
   * Public verification-link landing page — parallel to /qr/[token].
   *
   * Auto-confirms the common case. If the backend routed this registration
   * to pending_review (verified email matches an existing guardian on a
   * different family), that's surfaced here rather than treated as an error.
   */
  import { onMount } from 'svelte';
  import { t } from 'svelte-i18n';
  import { page } from '$app/stores';
  import { registrationApi } from '$lib/api/registrationService';
  import type { RegistrationVerifyResponse } from '$lib/api/types';
  import type { ApiError } from '$lib/api/client';
  import PaymentInstructions from '$lib/components/registrations/PaymentInstructions.svelte';

  const token = $derived($page.params.token ?? '');

  let result = $state<RegistrationVerifyResponse | null>(null);
  let loading = $state(true);
  let expired = $state(false);
  let notFound = $state(false);
  let error = $state(false);

  onMount(async () => {
    try {
      result = await registrationApi.verify(token);
    } catch (err) {
      const apiError = err as ApiError;
      if (apiError?.status === 410) {
        expired = true;
      } else if (apiError?.status === 404) {
        notFound = true;
      } else {
        console.error('Registration verification failed:', err);
        error = true;
      }
    } finally {
      loading = false;
    }
  });
</script>

<svelte:head>
  <title>{$t('register.verifyingTitle')}</title>
</svelte:head>

<main class="container mx-auto p-6 max-w-2xl">
  <div class="bg-white border border-neutral-300 rounded-card p-6 shadow-sm text-center">
    {#if loading}
      <p class="text-neutral-600">{$t('register.verifyingTitle')}</p>
    {:else if expired}
      <h1 class="text-2xl font-bold text-neutral-900 mb-2">{$t('register.verifyExpiredTitle')}</h1>
      <p class="text-neutral-700">{$t('register.verifyExpiredMessage')}</p>
    {:else if notFound}
      <h1 class="text-2xl font-bold text-neutral-900 mb-2">{$t('register.verifyNotFoundTitle')}</h1>
      <p class="text-neutral-700">{$t('register.verifyNotFoundMessage')}</p>
    {:else if error || !result}
      <h1 class="text-2xl font-bold text-neutral-900 mb-2">{$t('register.submitError')}</h1>
    {:else if result.status === 'pending_review'}
      <h1 class="text-2xl font-bold text-neutral-900 mb-2">{$t('register.verifyPendingReviewTitle')}</h1>
      <p class="text-neutral-700 mb-4">{$t('register.verifyPendingReviewMessage')}</p>
      <p class="text-sm text-neutral-500">
        {$t('register.referenceCode', { values: { code: result.reference_code } })}
      </p>
    {:else if result.status === 'pending_payment' && result.amount}
      <h1 class="text-2xl font-bold text-neutral-900 mb-2">{$t('register.paymentPendingTitle')}</h1>
      <p class="text-neutral-700 mb-4">
        {$t('register.paymentPendingMessage', { values: { event: result.event_name } })}
      </p>
      <PaymentInstructions
        amount={result.amount}
        currency={result.currency ?? 'SEK'}
        reference_code={result.reference_code}
        swish_url={result.swish_url ?? null}
        swish_qr_data_url={result.swish_qr_data_url ?? null}
        bankgiro_number={result.bankgiro_number ?? null}
      />
      <p class="text-xs text-neutral-500 mt-4">
        {$t('register.paymentStatusLinkHint')}
        <a href="/register/payment-status?ref={result.reference_code}" class="text-primary-600 hover:underline">
          {$t('register.paymentStatusLink')}
        </a>
      </p>
    {:else}
      <h1 class="text-2xl font-bold text-neutral-900 mb-2">{$t('register.verifyConfirmedTitle')}</h1>
      <p class="text-neutral-700 mb-4">
        {$t('register.verifyConfirmedMessage', { values: { event: result.event_name } })}
      </p>
      <p class="text-sm text-neutral-500">
        {$t('register.referenceCode', { values: { code: result.reference_code } })}
      </p>
    {/if}
  </div>

  <div class="text-center text-xs text-neutral-500 mt-6">
    {$t('register.privacyNotice')}
    <a href="/privacy" class="text-primary-600 hover:underline">{$t('register.privacyLink')}</a>
  </div>
</main>
