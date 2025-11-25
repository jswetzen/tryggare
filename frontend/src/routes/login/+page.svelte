<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';

  interface CookieData {
    value: string;
    options: {
      path?: string;
      maxAge?: number;
      sameSite?: string;
    };
  }

  interface PageData {
    error?: string;
    success?: boolean;
    cookies?: Record<string, CookieData>;
  }

  let { form }: { form: PageData | null } = $props();

  // Handle successful login - set cookies client-side and redirect
  $effect(() => {
    if (form?.success && form?.cookies) {
      // First, clear any existing auth cookies to prevent conflicts
      document.cookie = 'csrftoken=; path=/; max-age=0; expires=Thu, 01 Jan 1970 00:00:00 UTC';
      document.cookie = 'sessionid=; path=/; max-age=0; expires=Thu, 01 Jan 1970 00:00:00 UTC';
      document.cookie = 'csrftoken=; max-age=0; expires=Thu, 01 Jan 1970 00:00:00 UTC';
      document.cookie = 'sessionid=; max-age=0; expires=Thu, 01 Jan 1970 00:00:00 UTC';

      // Set each cookie
      Object.entries(form.cookies).forEach(([name, data]) => {
        const { value, options } = data;
        let cookieString = `${name}=${value}`;

        if (options.path) cookieString += `; path=${options.path}`;
        if (options.maxAge) cookieString += `; max-age=${options.maxAge}`;
        if (options.sameSite) cookieString += `; samesite=${options.sameSite}`;

        document.cookie = cookieString;
      });

      // Wait a moment for cookies to be set, then do full page reload
      setTimeout(() => {
        window.location.href = '/checkin';
      }, 100);
    }
  });
</script>

<svelte:head>
  <title>Login - Check-In System</title>
</svelte:head>

<div class="min-h-screen flex items-center justify-center bg-gray-100">
  <div class="bg-white p-8 rounded-lg shadow-md w-full max-w-md">
    <h1 class="text-2xl font-bold mb-6 text-center">Check-In System Login</h1>

    {#if form?.success}
      <div class="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
        Login successful! Redirecting...
      </div>
    {:else if form?.error}
      <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
        {form.error}
      </div>
    {/if}

    <form method="POST">
      <div class="mb-4">
        <label for="username" class="block text-gray-700 text-sm font-bold mb-2">
          Username
        </label>
        <input
          type="text"
          id="username"
          name="username"
          required
          class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
          placeholder="Enter your username"
        />
      </div>

      <div class="mb-6">
        <label for="password" class="block text-gray-700 text-sm font-bold mb-2">
          Password
        </label>
        <input
          type="password"
          id="password"
          name="password"
          required
          class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
          placeholder="Enter your password"
        />
      </div>

      <div class="flex items-center justify-between">
        <button
          type="submit"
          class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline w-full"
        >
          Login
        </button>
      </div>
    </form>
  </div>
</div>
