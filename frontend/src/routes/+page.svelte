<script lang="ts">
  import { t } from 'svelte-i18n';

  let { data }: { data: { user: { username: string; name: string; is_staff: boolean } | null } } = $props();
</script>

<svelte:head>
  <title>{$t('home.pageTitle')}</title>
</svelte:head>

<div class="max-w-4xl mx-auto">
  <div class="mb-8">
    <h1 class="text-3xl font-bold text-primary-900">
      {$t('home.welcome', { values: { name: data.user?.name || data.user?.username || '' } })}
    </h1>
    <p class="mt-2 text-neutral-600">{$t('home.subtitle')}</p>
  </div>

  <section class="mb-8">
    <h2 class="text-lg font-semibold text-neutral-700 mb-4">{$t('home.quickActions')}</h2>
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <a href="/checkin" class="block bg-white rounded-card border-2 border-neutral-300 p-5 hover:shadow-elevation-3 hover:border-primary-500 transition-all">
        <div class="flex items-center gap-3 mb-2">
          <div class="w-10 h-10 rounded-card bg-success-50 flex items-center justify-center">
            <svg class="w-5 h-5 text-success-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 class="font-semibold text-primary-900">{$t('nav.checkin')}</h3>
        </div>
        <p class="text-sm text-neutral-600">{$t('home.checkinDesc')}</p>
      </a>

      <a href="/checkout" class="block bg-white rounded-card border-2 border-neutral-300 p-5 hover:shadow-elevation-3 hover:border-primary-500 transition-all">
        <div class="flex items-center gap-3 mb-2">
          <div class="w-10 h-10 rounded-card bg-danger-50 flex items-center justify-center">
            <svg class="w-5 h-5 text-danger-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
          </div>
          <h3 class="font-semibold text-primary-900">{$t('nav.checkout')}</h3>
        </div>
        <p class="text-sm text-neutral-600">{$t('home.checkoutDesc')}</p>
      </a>

      <a href="/print-queue" class="block bg-white rounded-card border-2 border-neutral-300 p-5 hover:shadow-elevation-3 hover:border-primary-500 transition-all">
        <div class="flex items-center gap-3 mb-2">
          <div class="w-10 h-10 rounded-card bg-primary-50 flex items-center justify-center">
            <svg class="w-5 h-5 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
            </svg>
          </div>
          <h3 class="font-semibold text-primary-900">{$t('nav.printQueue')}</h3>
        </div>
        <p class="text-sm text-neutral-600">{$t('home.printQueueDesc')}</p>
      </a>
    </div>
  </section>

  {#if data.user?.is_staff}
    <section class="mb-8">
      <h2 class="text-lg font-semibold text-neutral-700 mb-4">{$t('home.adminSection')}</h2>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <a href="/import" class="block bg-white rounded-card border-2 border-neutral-300 p-5 hover:shadow-elevation-3 hover:border-primary-500 transition-all">
          <div class="flex items-center gap-3 mb-2">
            <div class="w-10 h-10 rounded-card bg-warning-50 flex items-center justify-center">
              <svg class="w-5 h-5 text-warning-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
            </div>
            <h3 class="font-semibold text-primary-900">{$t('import.nav')}</h3>
          </div>
          <p class="text-sm text-neutral-600">{$t('home.importDesc')}</p>
        </a>

        <a href="/admin/" class="block bg-white rounded-card border-2 border-neutral-300 p-5 hover:shadow-elevation-3 hover:border-primary-500 transition-all">
          <div class="flex items-center gap-3 mb-2">
            <div class="w-10 h-10 rounded-card bg-neutral-100 flex items-center justify-center">
              <svg class="w-5 h-5 text-neutral-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
            <h3 class="font-semibold text-primary-900">{$t('nav.admin')}</h3>
          </div>
          <p class="text-sm text-neutral-600">{$t('home.adminDesc')}</p>
        </a>
      </div>
    </section>
  {/if}

  <div class="bg-primary-50 border border-primary-200 rounded-card p-4 text-sm text-primary-900">
    <span class="font-semibold">{$t('home.tipLabel')}</span>{$t('home.tip')}
  </div>
</div>
