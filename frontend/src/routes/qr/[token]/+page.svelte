<script lang="ts">
  import { onMount } from 'svelte';
  import { t } from 'svelte-i18n';
  import { page } from '$app/stores';
  import { childApi, checkInApi } from '$lib/api/services';
  import type { Child, CheckInRecord } from '$lib/api/types';

  const token = $derived($page.params.token);

  let child = $state<Child | null>(null);
  let activeCheckIn = $state<CheckInRecord | null>(null);
  let loading = $state(true);
  let error = $state<string | null>(null);

  onMount(() => {
    loadChildInfo();
  });

  async function loadChildInfo() {
    loading = true;
    error = null;

    try {
      // Load child by QR token
      child = await childApi.getByQrToken(token);

      // Load active check-in if any
      const allActive = await checkInApi.active();
      activeCheckIn =
        allActive.find((record) => record.child === child?.id) || null;
    } catch (err) {
      console.error('Failed to load child info:', err);
      error = 'Failed to load child information';
    } finally {
      loading = false;
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
        <div class="text-gray-600">{$t('qr.loading')}</div>
      </div>
    </div>
  {:else if error || !child}
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
  {:else}
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
      {:else}
        <div class="bg-gray-50 border border-gray-200 rounded p-4">
          <div class="flex items-center gap-2">
            <div class="w-3 h-3 rounded-full bg-gray-400"></div>
            <span class="font-semibold text-gray-800">{$t('qr.notCheckedIn')}</span>
          </div>
        </div>
      {/if}
    </div>

    <div class="card">
      <h2 class="text-xl font-semibold mb-4">{$t('qr.emergencyContact')}</h2>
      <div class="text-sm text-gray-600 mb-2">
        {$t('qr.emergencyContactHelp')}
      </div>
      <div class="text-sm text-gray-600">{$t('qr.familyId')} {child.family}</div>
    </div>
  {/if}
</main>
