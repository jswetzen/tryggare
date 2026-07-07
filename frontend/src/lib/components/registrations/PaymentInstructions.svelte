<script lang="ts">
  /**
   * Swish QR + Bankgiro fallback for a pending_payment registration. Shared
   * between the verify page (inline, right after email confirmation) and
   * the payment-status recovery page (looked up later by reference code +
   * email, since the verify link is single-use).
   */
  import { t } from 'svelte-i18n';
  import type { PaymentInstructionsPayload } from '$lib/api/types';

  let {
    amount,
    currency,
    reference_code: referenceCode,
    swish_url: swishUrl,
    swish_qr_data_url: swishQrDataUrl,
    bankgiro_number: bankgiroNumber
  }: PaymentInstructionsPayload = $props();
</script>

<div class="text-left">
  <p class="text-neutral-700 mb-4">
    {$t('register.paymentAmountLabel', { values: { amount, currency } })}
  </p>

  {#if swishUrl}
    <div class="border border-neutral-200 rounded-card p-4 bg-neutral-50 mb-3 text-center">
      <p class="text-sm font-semibold text-neutral-700 mb-2">{$t('register.paymentSwishTitle')}</p>
      {#if swishQrDataUrl}
        <img
          src={swishQrDataUrl}
          alt={$t('register.paymentSwishQrAlt')}
          class="mx-auto w-48 h-48 mb-2"
        />
      {/if}
      <a
        href={swishUrl}
        class="inline-block px-4 py-2 bg-primary-600 text-white font-semibold rounded-button hover:bg-primary-700 transition-colors"
      >
        {$t('register.paymentOpenSwish')}
      </a>
    </div>
  {/if}

  {#if bankgiroNumber}
    <div class="border border-neutral-200 rounded-card p-4 bg-neutral-50 mb-3">
      <p class="text-sm font-semibold text-neutral-700 mb-1">{$t('register.paymentBankgiroTitle')}</p>
      <p class="text-sm text-neutral-700">
        {$t('register.paymentBankgiroInstructions', { values: { bankgiro: bankgiroNumber, code: referenceCode } })}
      </p>
    </div>
  {/if}

  <p class="text-sm text-neutral-500">
    {$t('register.referenceCode', { values: { code: referenceCode } })}
  </p>
</div>
