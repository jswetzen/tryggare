<script lang="ts">
  /**
   * Recovery path for a guardian who navigated away from the verify page
   * before paying — verify_registration's token is single-use, so this form
   * (reference code + contact email) is the only way back in.
   */
  import { onMount } from 'svelte';
  import { t } from 'svelte-i18n';
  import { page } from '$app/stores';
  import { registrationApi } from '$lib/api/registrationService';
  import type { RegistrationPaymentStatusResponse } from '$lib/api/types';
  import type { ApiError } from '$lib/api/client';
  import PaymentInstructions from '$lib/components/registrations/PaymentInstructions.svelte';

  let referenceCode = $state($page.url.searchParams.get('ref') ?? '');
  let contactEmail = $state('');
  let result = $state<RegistrationPaymentStatusResponse | null>(null);
  let loading = $state(false);
  let notFound = $state(false);
  let error = $state('');

  onMount(() => {
    referenceCode = referenceCode.trim().toUpperCase();
  });

  async function handleSubmit(e: Event) {
    e.preventDefault();
    error = '';
    notFound = false;
    result = null;
    loading = true;
    try {
      result = await registrationApi.checkPaymentStatus(
        referenceCode.trim(),
        contactEmail.trim()
      );
    } catch (err) {
      const apiError = err as ApiError;
      if (apiError?.status === 404) {
        notFound = true;
      } else {
        console.error('Payment status lookup failed:', err);
        error = $t('register.paymentStatusError');
      }
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head>
  <title>{$t('register.paymentStatusFormTitle')}</title>
</svelte:head>

<main class="container mx-auto p-6 max-w-2xl">
  <div class="bg-white border border-neutral-300 rounded-card p-6 shadow-sm">
    <h1 class="text-2xl font-bold text-neutral-900 mb-4 text-center">
      {$t('register.paymentStatusFormTitle')}
    </h1>

    {#if result}
      <h2 class="text-lg font-semibold text-neutral-900 mb-2 text-center">
        {$t('register.verifyConfirmedMessage', { values: { event: result.event_name } })}
      </h2>
      {#if result.status === 'pending_payment'}
        <PaymentInstructions
          amount={result.amount}
          currency={result.currency}
          reference_code={result.reference_code}
          swish_url={result.swish_url}
          swish_qr_data_url={result.swish_qr_data_url}
          bankgiro_number={result.bankgiro_number}
        />
      {:else}
        <p class="text-neutral-700 text-center">
          {$t('register.paymentStatusCurrentStatus', { values: { status: result.status } })}
        </p>
      {/if}
    {:else}
      <form on:submit={handleSubmit}>
        {#if notFound}
          <div class="mb-4 p-2 bg-danger-50 border border-danger-200 rounded text-danger-700 text-sm">
            {$t('register.paymentStatusNotFound')}
          </div>
        {/if}
        {#if error}
          <div class="mb-4 p-2 bg-danger-50 border border-danger-200 rounded text-danger-700 text-sm">
            {error}
          </div>
        {/if}

        <div class="mb-4">
          <label for="reference-code" class="block text-sm font-semibold text-neutral-700 mb-1">
            {$t('register.paymentStatusReferenceLabel')}
          </label>
          <input
            id="reference-code"
            type="text"
            bind:value={referenceCode}
            required
            class="w-full px-3 py-2 border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>

        <div class="mb-4">
          <label for="contact-email" class="block text-sm font-semibold text-neutral-700 mb-1">
            {$t('register.paymentStatusEmailLabel')}
          </label>
          <input
            id="contact-email"
            type="email"
            bind:value={contactEmail}
            required
            class="w-full px-3 py-2 border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>

        <div class="flex justify-end">
          <button
            type="submit"
            disabled={loading}
            class="px-4 py-2 bg-primary-600 text-white font-semibold rounded-button hover:bg-primary-700 transition-colors disabled:opacity-50"
          >
            {loading ? $t('register.submitting') : $t('register.paymentStatusSubmit')}
          </button>
        </div>
      </form>
    {/if}
  </div>
</main>
