<script lang="ts">
  import { onMount } from 'svelte';
  import { t } from 'svelte-i18n';
  import { page } from '$app/stores';
  import { qrApi, checkInApi, printingApi, printQueueApi } from '$lib/api/services';
  import { authStore } from '$lib/stores/auth';
  import type { QRInfoResponse, Printer } from '$lib/api/types';

  // Support both old 'token' param and new 'code' naming
  const code = $derived($page.params.token);

  let data = $state<QRInfoResponse | null>(null);
  let loading = $state(true);
  let notFound = $state(false);
  let error = $state<string | null>(null);
  let actionInProgress = $state(false);
  let successMessage = $state<string | null>(null);
  let pickedUpBy = $state('');
  let showCheckoutModal = $state(false);
  let printers = $state<Printer[]>([]);
  let showPrinterPicker = $state(false);

  // Age computed from birthdate (whole years)
  const age = $derived.by(() => {
    if (!data?.child.birthdate) return null;
    const dob = new Date(data.child.birthdate);
    if (isNaN(dob.getTime())) return null;
    const now = new Date();
    let years = now.getFullYear() - dob.getFullYear();
    const m = now.getMonth() - dob.getMonth();
    if (m < 0 || (m === 0 && now.getDate() < dob.getDate())) years--;
    return years >= 0 ? years : null;
  });

  onMount(() => {
    loadQRInfo();
  });

  // Only logged-in staff can print; load printers when authenticated.
  $effect(() => {
    if ($authStore.user && printers.length === 0) {
      printingApi
        .getPrinters()
        .then((p) => (printers = p))
        .catch((e) => console.error('Failed to load printers:', e));
    }
  });

  async function loadQRInfo() {
    loading = true;
    error = null;
    notFound = false;
    successMessage = null;

    try {
      // New privacy-first API: only returns data when child is actively checked in
      data = await qrApi.getInfo(code);
    } catch (err: any) {
      console.error('Failed to load QR info:', err);
      if (err?.status === 404 || err?.message?.includes('404')) {
        // Code not found or child is not currently checked in
        notFound = true;
      } else {
        error = 'Failed to load information';
      }
    } finally {
      loading = false;
    }
  }

  async function handleCheckOut() {
    if (!data) return;

    actionInProgress = true;
    error = null;

    try {
      await checkInApi.checkOut(data.checkin_record_id, pickedUpBy);
      successMessage = $t('qr.checkOutSuccess');
      showCheckoutModal = false;
      pickedUpBy = '';
      // After checkout, the QR code will no longer be valid
      // Show success for a moment, then mark as not found
      setTimeout(() => {
        notFound = true;
        data = null;
      }, 2000);
    } catch (err) {
      console.error('Failed to check out:', err);
      error = $t('qr.checkOutError');
    } finally {
      actionInProgress = false;
    }
  }

  function handleEditChild() {
    if (!data) return;
    // Redirect to Django Admin edit page
    window.location.href = `/admin/families/child/${data.child.id}/change/`;
  }

  function handleReprintLabel() {
    if (!data) return;

    const onlinePrinters = printers.filter((p) => p.is_online);

    // Not logged in or no online printer: fall back to the print page,
    // which opens in a new tab and bounces to login if needed.
    if (!$authStore.user || onlinePrinters.length === 0) {
      successMessage = $t('qr.reprintOpeningPage');
      window.open(printQueueApi.getPrintPageUrl(data.checkin_record_id), '_blank');
      return;
    }

    // Exactly one online printer: send straight to it.
    if (onlinePrinters.length === 1) {
      sendToPrinter(onlinePrinters[0].id);
      return;
    }

    // Multiple online printers: let staff choose.
    showPrinterPicker = true;
  }

  async function sendToPrinter(printerId: string) {
    if (!data) return;

    showPrinterPicker = false;
    actionInProgress = true;
    error = null;
    successMessage = $t('qr.reprintSending');

    try {
      await printingApi.createJob({
        checkin_id: data.checkin_record_id,
        printer_id: printerId,
      });
      successMessage = $t('qr.reprintSuccess');
    } catch (err) {
      console.error('Failed to reprint label:', err);
      successMessage = null;
      error = $t('qr.reprintError');
    } finally {
      actionInProgress = false;
    }
  }
</script>

<svelte:head>
  <title>{$t('qr.pageTitle')}</title>
</svelte:head>

<main class="container mx-auto p-6 max-w-2xl">
  {#if loading}
    <div class="card">
      <div class="text-center py-8">
        <div class="text-neutral-600">{$t('qr.loading')}</div>
      </div>
    </div>
  {:else if notFound}
    <div class="card">
      <div class="text-center py-8">
        <div class="text-neutral-600 font-semibold mb-2">
          {$t('qr.notCheckedIn')}
        </div>
        <div class="text-neutral-500">
          {$t('qr.notCheckedInHelp')}
        </div>
      </div>
    </div>
  {:else if error && !data}
    <div class="card">
      <div class="text-center py-8">
        <div class="text-danger-600 font-semibold mb-2">
          {error || $t('qr.notFound')}
        </div>
        <div class="text-neutral-600">
          {$t('qr.notFoundHelp')}
        </div>
      </div>
    </div>
  {:else if data}
    <!-- Success/Error Messages -->
    {#if successMessage}
      <div class="bg-success-50 border border-success-200 rounded-card p-4 mb-4">
        <div class="text-success-800 font-semibold">{successMessage}</div>
      </div>
    {/if}
    {#if error}
      <div class="bg-danger-50 border border-danger-200 rounded-card p-4 mb-4">
        <div class="text-danger-800 font-semibold">{error}</div>
      </div>
    {/if}

    <!-- Allergy alert: most safety-critical info, surfaced at the very top -->
    {#if data.child.allergies}
      <div
        class="bg-danger-50 border-2 border-danger-400 rounded-card p-4 mb-4 flex items-start gap-3"
        role="alert"
      >
        <span class="text-2xl leading-none" aria-hidden="true">⚠️</span>
        <div>
          <div class="text-sm font-bold uppercase tracking-wide text-danger-700">
            {$t('qr.allergyAlert')}
          </div>
          <div class="text-lg text-danger-800 font-semibold">{data.child.allergies}</div>
        </div>
      </div>
    {/if}

    <!-- Child Information -->
    <div class="card mb-6">
      <div class="flex items-baseline justify-between gap-3 mb-4">
        <h1 class="text-3xl font-bold">
          {data.child.first_name}
          {data.child.last_name}
        </h1>
        {#if age !== null}
          <span class="text-lg text-neutral-600 whitespace-nowrap">
            {$t('qr.ageYears', { values: { years: age } })}
          </span>
        {/if}
      </div>

      <div class="space-y-4">
        {#if data.child.birthdate}
          <div>
            <div class="text-sm text-neutral-600">{$t('qr.dateOfBirth')}</div>
            <div class="text-lg">{data.child.birthdate}</div>
          </div>
        {/if}

        {#if data.child.notes}
          <div>
            <div class="text-sm text-neutral-600">{$t('qr.medicalConditions')}</div>
            <div class="text-lg text-orange-600 font-semibold">
              {data.child.notes}
            </div>
          </div>
        {/if}
      </div>
    </div>

    <!-- Check-In Status (always checked in when we have data) -->
    <div class="card mb-6">
      <h2 class="text-xl font-semibold mb-4">{$t('qr.checkInStatus')}</h2>

      <div class="bg-success-50 border border-success-200 rounded-card p-4">
        <div class="flex items-center gap-2 mb-2">
          <div class="w-3 h-3 rounded-full bg-success-500"></div>
          <span class="font-semibold text-success-800">{$t('qr.currentlyCheckedIn')}</span>
          {#if data.supervised}
            <span class="text-xs bg-primary-100 text-primary-700 px-2 py-0.5 rounded-full">
              {$t('qr.supervised')}
            </span>
          {/if}
        </div>
        <div class="text-sm text-neutral-700">
          {$t('qr.session')} {data.current_session.name}
        </div>
        <div class="text-sm text-neutral-700">
          {$t('qr.since')} {new Date(data.current_session.check_in_time).toLocaleString()}
        </div>
      </div>
    </div>

    <!-- Action Buttons -->
    <div class="card mb-6">
      <h2 class="text-xl font-semibold mb-4">{$t('qr.actions')}</h2>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <button
          class="bg-danger-600 hover:bg-danger-700 text-white font-semibold px-5 py-3 rounded-card"
          onclick={() => showCheckoutModal = true}
          disabled={actionInProgress}
        >
          {$t('qr.checkOut')}
        </button>

        <button
          class="bg-primary-600 hover:bg-primary-700 text-white font-semibold px-5 py-3 rounded-card"
          onclick={handleEditChild}
          disabled={actionInProgress}
        >
          {$t('qr.editChild')}
        </button>

        <button
          class="bg-success-600 hover:bg-success-700 text-white font-semibold px-5 py-3 rounded-card"
          onclick={handleReprintLabel}
          disabled={actionInProgress}
        >
          {$t('qr.reprintLabel')}
        </button>
      </div>
    </div>

    <!-- Emergency Contact Info -->
    <div class="card">
      <h2 class="text-xl font-semibold mb-4">{$t('qr.emergencyContact')}</h2>
      <div class="text-sm text-neutral-600 mb-2">
        {$t('qr.emergencyContactHelp')}
      </div>
      {#if data.parents && data.parents.length > 0}
        <div class="mb-2">
          <div class="text-sm font-semibold text-neutral-700">{$t('qr.parentsGuardians')}</div>
          {#each data.parents as parent}
            <div class="text-lg">
              {parent.name}
              {#if parent.phone}
                <span class="text-sm text-neutral-600">({parent.phone})</span>
              {/if}
            </div>
          {/each}
        </div>
      {/if}
      <div class="text-sm text-neutral-600">{$t('qr.familyId')} {data.family_id}</div>
    </div>
  {/if}
</main>

<!-- Checkout Modal -->
{#if showCheckoutModal}
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
    <div class="bg-white rounded-card p-6 max-w-md w-full">
      <h3 class="text-xl font-bold mb-4">{$t('qr.checkOutConfirm')}</h3>

      <div class="mb-4">
        <label for="picked-up-by" class="block text-sm font-semibold text-neutral-700 mb-2">
          {$t('qr.pickedUpBy')}
        </label>
        <input
          id="picked-up-by"
          type="text"
          class="w-full px-4 py-2 border border-neutral-300 rounded-card focus:outline-none focus:ring-2 focus:ring-primary-500"
          placeholder={$t('qr.pickedUpByPlaceholder')}
          bind:value={pickedUpBy}
        />
      </div>

      <div class="flex gap-3">
        <button
          class="flex-1 bg-neutral-200 hover:bg-neutral-300 text-neutral-800 font-semibold px-5 py-2 rounded-card"
          onclick={() => { showCheckoutModal = false; pickedUpBy = ''; }}
          disabled={actionInProgress}
        >
          {$t('common.cancel')}
        </button>
        <button
          class="flex-1 bg-danger-600 hover:bg-danger-700 text-white font-semibold px-5 py-2 rounded-card"
          onclick={handleCheckOut}
          disabled={actionInProgress}
        >
          {actionInProgress ? $t('common.loading') : $t('qr.checkOut')}
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- Printer Picker Modal (only shown when multiple online printers are available) -->
{#if showPrinterPicker && data}
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
    <div class="bg-white rounded-card p-6 max-w-md w-full">
      <h3 class="text-xl font-bold mb-2">{$t('qr.choosePrinter')}</h3>
      <p class="text-sm text-neutral-600 mb-4">{$t('qr.choosePrinterHelp')}</p>

      <div class="space-y-2 mb-4">
        {#each printers.filter((p) => p.is_online) as printer}
          <button
            class="w-full flex items-center gap-2 text-left bg-neutral-50 hover:bg-primary-50 border border-neutral-200 hover:border-primary-300 px-4 py-3 rounded-card"
            onclick={() => sendToPrinter(printer.id)}
            disabled={actionInProgress}
          >
            <span class="w-2.5 h-2.5 rounded-full bg-success-500"></span>
            <span class="font-semibold">{printer.name}</span>
          </button>
        {/each}
      </div>

      <button
        class="w-full bg-neutral-200 hover:bg-neutral-300 text-neutral-800 font-semibold px-5 py-2 rounded-card"
        onclick={() => (showPrinterPicker = false)}
        disabled={actionInProgress}
      >
        {$t('common.cancel')}
      </button>
    </div>
  </div>
{/if}
