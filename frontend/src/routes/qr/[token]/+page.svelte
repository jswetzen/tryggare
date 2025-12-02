<script lang="ts">
  import { onMount } from 'svelte';
  import { t } from 'svelte-i18n';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { childApi, checkInApi } from '$lib/api/services';
  import type { Child, CheckInRecord } from '$lib/api/types';

  const token = $derived($page.params.token);

  let child = $state<Child | null>(null);
  let activeCheckIn = $state<CheckInRecord | null>(null);
  let recentCheckOut = $state<CheckInRecord | null>(null);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let actionInProgress = $state(false);
  let successMessage = $state<string | null>(null);
  let pickedUpBy = $state('');
  let showCheckoutModal = $state(false);
  let showQrCode = $state(false);

  onMount(() => {
    loadChildInfo();
  });

  async function loadChildInfo() {
    loading = true;
    error = null;

    try {
      // Load child by QR token
      child = await childApi.getByQrToken(token);

      // Load all check-in records for this child
      const allCheckIns = await checkInApi.list();
      const childCheckIns = allCheckIns.filter((record) => record.child === child?.id);

      // Find active check-in (not checked out)
      activeCheckIn =
        childCheckIns.find((record) => !record.check_out_time) || null;

      // Find most recent check-out (if any)
      const checkedOut = childCheckIns.filter((record) => record.check_out_time);
      if (checkedOut.length > 0) {
        // Sort by check_out_time descending
        checkedOut.sort((a, b) =>
          new Date(b.check_out_time!).getTime() - new Date(a.check_out_time!).getTime()
        );
        recentCheckOut = checkedOut[0];
      }
    } catch (err) {
      console.error('Failed to load child info:', err);
      error = 'Failed to load child information';
    } finally {
      loading = false;
    }
  }

  async function handleCheckOut() {
    if (!activeCheckIn) return;

    actionInProgress = true;
    error = null;

    try {
      await checkInApi.checkOut(activeCheckIn.id, pickedUpBy);
      successMessage = $t('qr.checkOutSuccess');
      showCheckoutModal = false;
      pickedUpBy = '';
      await loadChildInfo(); // Reload data
    } catch (err) {
      console.error('Failed to check out:', err);
      error = $t('qr.checkOutError');
    } finally {
      actionInProgress = false;
    }
  }

  async function handleUndoCheckout() {
    if (!recentCheckOut) return;

    actionInProgress = true;
    error = null;

    try {
      await checkInApi.undoCheckout(recentCheckOut.id);
      successMessage = $t('qr.undoSuccess');
      await loadChildInfo(); // Reload data
    } catch (err: any) {
      console.error('Failed to undo checkout:', err);
      // Check if it's a time limit error
      if (err?.message?.includes('too much time')) {
        error = $t('qr.undoTooLate');
      } else {
        error = $t('qr.undoError');
      }
    } finally {
      actionInProgress = false;
    }
  }

  function handleEditChild() {
    if (!child) return;
    // Redirect to Django Admin edit page
    window.location.href = `/admin/children/child/${child.id}/change/`;
  }

  function handleReprintLabel() {
    showQrCode = true;
  }

  function canUndoCheckout(): boolean {
    if (!recentCheckOut || !recentCheckOut.check_out_time) return false;

    const checkoutTime = new Date(recentCheckOut.check_out_time);
    const now = new Date();
    const minutesSinceCheckout = (now.getTime() - checkoutTime.getTime()) / 1000 / 60;

    return minutesSinceCheckout <= 5;
  }

  function formatTimeSince(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);
    const minutes = Math.floor(seconds / 60);

    if (minutes < 1) return `${seconds} seconds ago`;
    if (minutes === 1) return '1 minute ago';
    return `${minutes} minutes ago`;
  }
</script>

<svelte:head>
  <title>{$t('qr.pageTitle')}</title>
</svelte:head>

<main class="container mx-auto p-6 max-w-2xl">
  {#if loading}
    <div class="card">
      <div class="text-center py-8">
        <div class="text-gray-600">{$t('qr.loading')}</div>
      </div>
    </div>
  {:else if error && !child}
    <div class="card">
      <div class="text-center py-8">
        <div class="text-red-600 font-semibold mb-2">
          {error || $t('qr.notFound')}
        </div>
        <div class="text-gray-600">
          {$t('qr.notFoundHelp')}
        </div>
      </div>
    </div>
  {:else if child}
    <!-- Success/Error Messages -->
    {#if successMessage}
      <div class="bg-green-50 border border-green-200 rounded p-4 mb-4">
        <div class="text-green-800 font-semibold">{successMessage}</div>
      </div>
    {/if}
    {#if error}
      <div class="bg-red-50 border border-red-200 rounded p-4 mb-4">
        <div class="text-red-800 font-semibold">{error}</div>
      </div>
    {/if}

    <!-- Child Information -->
    <div class="card mb-6">
      <h1 class="text-3xl font-bold mb-6">{$t('qr.title')}</h1>

      <div class="space-y-4">
        <div>
          <div class="text-sm text-gray-600">{$t('qr.name')}</div>
          <div class="text-xl font-semibold">
            {child.first_name}
            {child.last_name}
          </div>
        </div>

        {#if child.date_of_birth}
          <div>
            <div class="text-sm text-gray-600">{$t('qr.dateOfBirth')}</div>
            <div class="text-lg">{child.date_of_birth}</div>
          </div>
        {/if}

        {#if child.allergies}
          <div>
            <div class="text-sm text-gray-600">{$t('qr.allergies')}</div>
            <div class="text-lg text-red-600 font-semibold">{child.allergies}</div>
          </div>
        {/if}

        {#if child.medical_conditions}
          <div>
            <div class="text-sm text-gray-600">{$t('qr.medicalConditions')}</div>
            <div class="text-lg text-orange-600 font-semibold">
              {child.medical_conditions}
            </div>
          </div>
        {/if}

        {#if child.special_needs}
          <div>
            <div class="text-sm text-gray-600">{$t('qr.specialNeeds')}</div>
            <div class="text-lg">{child.special_needs}</div>
          </div>
        {/if}
      </div>
    </div>

    <!-- Check-In Status -->
    <div class="card mb-6">
      <h2 class="text-xl font-semibold mb-4">{$t('qr.checkInStatus')}</h2>

      {#if activeCheckIn}
        <div class="bg-green-50 border border-green-200 rounded p-4">
          <div class="flex items-center gap-2 mb-2">
            <div class="w-3 h-3 rounded-full bg-green-500"></div>
            <span class="font-semibold text-green-800">{$t('qr.currentlyCheckedIn')}</span>
          </div>
          <div class="text-sm text-gray-700">
            {$t('qr.session')} {activeCheckIn.session}
          </div>
          <div class="text-sm text-gray-700">
            {$t('qr.since')} {new Date(activeCheckIn.check_in_time).toLocaleString()}
          </div>
        </div>
      {:else if recentCheckOut}
        <div class="bg-gray-50 border border-gray-200 rounded p-4">
          <div class="flex items-center gap-2 mb-2">
            <div class="w-3 h-3 rounded-full bg-gray-400"></div>
            <span class="font-semibold text-gray-800">{$t('qr.notCheckedIn')}</span>
          </div>
          <div class="text-sm text-gray-600">
            {$t('qr.checkedOutAt')} {new Date(recentCheckOut.check_out_time!).toLocaleString()}
          </div>
          {#if canUndoCheckout()}
            <div class="text-sm text-blue-600 mt-1">
              {$t('qr.canUndo')} ({formatTimeSince(recentCheckOut.check_out_time!)})
            </div>
          {/if}
        </div>
      {:else}
        <div class="bg-gray-50 border border-gray-200 rounded p-4">
          <div class="flex items-center gap-2">
            <div class="w-3 h-3 rounded-full bg-gray-400"></div>
            <span class="font-semibold text-gray-800">{$t('qr.notCheckedIn')}</span>
          </div>
        </div>
      {/if}
    </div>

    <!-- Action Buttons -->
    <div class="card mb-6">
      <h2 class="text-xl font-semibold mb-4">{$t('qr.actions')}</h2>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {#if activeCheckIn}
          <button
            class="bg-red-600 hover:bg-red-700 text-white font-semibold px-5 py-3 rounded"
            onclick={() => showCheckoutModal = true}
            disabled={actionInProgress}
          >
            {$t('qr.checkOut')}
          </button>
        {/if}

        {#if recentCheckOut && canUndoCheckout()}
          <button
            class="bg-orange-600 hover:bg-orange-700 text-white font-semibold px-5 py-3 rounded"
            onclick={handleUndoCheckout}
            disabled={actionInProgress}
          >
            {$t('qr.undoCheckOut')}
          </button>
        {/if}

        <button
          class="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-5 py-3 rounded"
          onclick={handleEditChild}
          disabled={actionInProgress}
        >
          {$t('qr.editChild')}
        </button>

        <button
          class="bg-green-600 hover:bg-green-700 text-white font-semibold px-5 py-3 rounded"
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
      <div class="text-sm text-gray-600 mb-2">
        {$t('qr.emergencyContactHelp')}
      </div>
      {#if child.parent_names && child.parent_names.length > 0}
        <div class="mb-2">
          <div class="text-sm font-semibold text-gray-700">Parents/Guardians:</div>
          <div class="text-lg">
            {child.parent_names.join(', ')}
          </div>
        </div>
      {/if}
      <div class="text-sm text-gray-600">{$t('qr.familyId')} {child.family}</div>
    </div>
  {/if}
</main>

<!-- Checkout Modal -->
{#if showCheckoutModal}
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
    <div class="bg-white rounded-lg p-6 max-w-md w-full">
      <h3 class="text-xl font-bold mb-4">{$t('qr.checkOutConfirm')}</h3>

      <div class="mb-4">
        <label class="block text-sm font-semibold text-gray-700 mb-2">
          {$t('qr.pickedUpBy')}
        </label>
        <input
          type="text"
          class="w-full px-4 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder={$t('qr.pickedUpByPlaceholder')}
          bind:value={pickedUpBy}
        />
      </div>

      <div class="flex gap-3">
        <button
          class="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold px-5 py-2 rounded"
          onclick={() => { showCheckoutModal = false; pickedUpBy = ''; }}
          disabled={actionInProgress}
        >
          {$t('common.cancel')}
        </button>
        <button
          class="flex-1 bg-red-600 hover:bg-red-700 text-white font-semibold px-5 py-2 rounded"
          onclick={handleCheckOut}
          disabled={actionInProgress}
        >
          {actionInProgress ? $t('common.loading') : $t('qr.checkOut')}
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- QR Code Display Modal -->
{#if showQrCode && child?.qr_token}
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
    <div class="bg-white rounded-lg p-6 max-w-md w-full">
      <h3 class="text-xl font-bold mb-4">{$t('qr.qrCode')}</h3>

      <div class="flex flex-col items-center mb-4">
        <div class="text-center mb-4">
          <p class="font-semibold">{child.first_name} {child.last_name}</p>
          <p class="text-sm text-gray-600">{child.qr_token}</p>
        </div>

        <!-- QR Code would be generated here -->
        <!-- For now, display the token and URL -->
        <div class="bg-gray-100 p-6 rounded">
          <div class="text-center">
            <p class="text-sm text-gray-600 mb-2">QR URL:</p>
            <p class="text-xs font-mono break-all">
              {window.location.origin}/qr/{child.qr_token}
            </p>
          </div>
        </div>
      </div>

      <button
        class="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold px-5 py-2 rounded"
        onclick={() => showQrCode = false}
      >
          {$t('common.close')}
      </button>
    </div>
  </div>
{/if}
