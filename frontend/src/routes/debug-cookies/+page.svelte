<script lang="ts">
  import { onMount } from 'svelte';

  let allCookies = $state('');
  let serverCookies = $state<any[]>([]);

  onMount(() => {
    allCookies = document.cookie;
  });
</script>

<svelte:head>
  <title>Debug Cookies</title>
</svelte:head>

<div class="p-8">
  <h1 class="text-2xl font-bold mb-4">Cookie Debug Page</h1>

  <div class="mb-6">
    <h2 class="text-xl font-semibold mb-2">Client-Side Cookies (document.cookie):</h2>
    <pre class="bg-gray-100 p-4 rounded overflow-auto">{allCookies || 'No cookies'}</pre>
  </div>

  <div class="mb-6">
    <h2 class="text-xl font-semibold mb-2">Actions:</h2>
    <button
      onclick={() => {
        document.cookie = 'csrftoken=; path=/; max-age=0';
        document.cookie = 'sessionid=; path=/; max-age=0';
        allCookies = document.cookie;
        alert('Cookies cleared! Refresh to see result.');
      }}
      class="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600 mr-2"
    >
      Clear All Auth Cookies
    </button>
    <button
      onclick={() => {
        allCookies = document.cookie;
      }}
      class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
    >
      Refresh
    </button>
  </div>

  <div class="mb-6">
    <p class="text-sm text-gray-600">
      Go back to <a href="/login" class="text-blue-500 underline">Login</a>
    </p>
  </div>
</div>
