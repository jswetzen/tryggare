<script lang="ts">
  import { onMount } from 'svelte';
  import { apiClient } from '$lib/api/client';

  onMount(async () => {
    try {
      // Call logout API
      await apiClient.post('/auth/logout/', {});
    } catch (error) {
      // Ignore errors - we're logging out anyway
    }

    // Clear cookies client-side
    document.cookie = 'csrftoken=; path=/; max-age=0; expires=Thu, 01 Jan 1970 00:00:00 UTC';
    document.cookie = 'sessionid=; path=/; max-age=0; expires=Thu, 01 Jan 1970 00:00:00 UTC';

    // Redirect to login
    window.location.href = '/login';
  });
</script>

<div class="fixed inset-0 flex items-center justify-center bg-neutral-100">
  <div class="text-center">
    <p class="text-xl text-neutral-700">Logging out...</p>
  </div>
</div>
