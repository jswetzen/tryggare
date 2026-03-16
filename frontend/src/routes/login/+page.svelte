<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { t } from 'svelte-i18n';
  import { apiClient } from '$lib/api/client';
  import LanguageSwitcher from '$lib/components/LanguageSwitcher.svelte';

  let errorMessage = $state('');
  let isLoading = $state(false);

  async function handleSubmit(event: Event) {
    event.preventDefault();
    const form = event.target as HTMLFormElement;
    const formData = new FormData(form);
    const username = formData.get('username') as string;
    const password = formData.get('password') as string;

    if (!username || !password) {
      errorMessage = $t('login.fieldsRequired');
      return;
    }

    isLoading = true;
    errorMessage = '';

    try {
      // Login using API client
      await apiClient.post('/auth/login/', { username, password });

      // On success, redirect to check-in page
      window.location.href = '/checkin';
    } catch (error: any) {
      isLoading = false;
      if (error.details?.error) {
        errorMessage = error.details.error;
      } else if (error.message) {
        errorMessage = error.message;
      } else {
        errorMessage = $t('login.loginFailed');
      }
    }
  }
</script>

<svelte:head>
  <title>{$t('login.pageTitle')}</title>
</svelte:head>

<div class="fixed inset-0 flex items-center justify-center bg-neutral-100">
  <div class="bg-white p-8 rounded-card shadow-elevation-3 w-full max-w-md z-10">
    <div class="flex justify-end mb-4">
      <LanguageSwitcher />
    </div>
    <h1 class="text-h1 mb-6 text-center">{$t('login.title')}</h1>

    {#if errorMessage}
      <div class="bg-danger-50 border border-danger-200 text-danger-800 px-4 py-3 rounded-card mb-4">
        {errorMessage}
      </div>
    {/if}

    <form onsubmit={handleSubmit}>
      <div class="mb-4">
        <label for="username" class="block text-neutral-700 text-sm font-bold mb-2">
          {$t('login.username')}
        </label>
        <input
          type="text"
          id="username"
          name="username"
          required
          class="shadow-sm appearance-none border border-neutral-300 rounded-input w-full py-2 px-3 text-neutral-700 leading-tight focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-600"
          placeholder={$t('login.usernamePlaceholder')}
        />
      </div>

      <div class="mb-6">
        <label for="password" class="block text-neutral-700 text-sm font-bold mb-2">
          {$t('login.password')}
        </label>
        <input
          type="password"
          id="password"
          name="password"
          required
          class="shadow-sm appearance-none border border-neutral-300 rounded-input w-full py-2 px-3 text-neutral-700 leading-tight focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-600"
          placeholder={$t('login.passwordPlaceholder')}
        />
      </div>

      <div class="flex items-center justify-between">
        <button
          type="submit"
          disabled={isLoading}
          class="bg-primary-600 hover:bg-primary-700 text-white font-bold py-2 px-4 rounded-button focus:outline-none focus:ring-2 focus:ring-primary-500 w-full disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? $t('login.loggingIn') : $t('login.submit')}
        </button>
      </div>
    </form>
  </div>
</div>
