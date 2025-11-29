<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { t } from 'svelte-i18n';
  import { apiClient } from '$lib/api/client';

  let errorMessage = $state('');
  let isLoading = $state(false);

  async function handleSubmit(event: Event) {
    event.preventDefault();
    const form = event.target as HTMLFormElement;
    const formData = new FormData(form);
    const username = formData.get('username') as string;
    const password = formData.get('password') as string;

    if (!username || !password) {
      errorMessage = 'Username and password are required';
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
        errorMessage = 'Login failed. Please try again.';
      }
    }
  }
</script>

<svelte:head>
  <title>{$t('login.pageTitle')}</title>
</svelte:head>

<div class="fixed inset-0 flex items-center justify-center bg-gray-100">
  <div class="bg-white p-8 rounded-lg shadow-md w-full max-w-md z-10">
    <h1 class="text-2xl font-bold mb-6 text-center">{$t('login.title')}</h1>

    {#if errorMessage}
      <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
        {errorMessage}
      </div>
    {/if}

    <form onsubmit={handleSubmit}>
      <div class="mb-4">
        <label for="username" class="block text-gray-700 text-sm font-bold mb-2">
          {$t('login.username')}
        </label>
        <input
          type="text"
          id="username"
          name="username"
          required
          class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
          placeholder={$t('login.usernamePlaceholder')}
        />
      </div>

      <div class="mb-6">
        <label for="password" class="block text-gray-700 text-sm font-bold mb-2">
          {$t('login.password')}
        </label>
        <input
          type="password"
          id="password"
          name="password"
          required
          class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
          placeholder={$t('login.passwordPlaceholder')}
        />
      </div>

      <div class="flex items-center justify-between">
        <button
          type="submit"
          disabled={isLoading}
          class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline w-full disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? $t('login.loggingIn') : $t('login.submit')}
        </button>
      </div>
    </form>
  </div>
</div>
