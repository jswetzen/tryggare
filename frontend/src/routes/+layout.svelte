<script lang="ts">
  import '../app.css';
  import { translationsReady } from '$lib/i18n/i18n';
  import { isLoading } from 'svelte-i18n';
  import TopNav from '$lib/components/TopNav.svelte';

  interface LayoutData {
    user: App.Locals['user'];
  }

  let { data, children }: { data: LayoutData; children: any } = $props();
</script>

{#if $isLoading}
  <!-- Show minimal loading state while translations load -->
  <div class="min-h-screen bg-neutral-100 flex items-center justify-center">
    <div class="text-neutral-600">Loading...</div>
  </div>
{:else}
  {#if data.user}
    <TopNav userName={data.user.username} isAdmin={data.user.is_staff ?? false} />
  {/if}

  <main class="min-h-screen bg-neutral-100 p-5">
    {@render children()}
  </main>
{/if}
