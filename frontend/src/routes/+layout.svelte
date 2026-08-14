<script lang="ts">
  import '$lib/styles/tokens.css';
  import '../app.css';
  import { translationsReady } from '$lib/i18n/i18n';
  import { isLoading } from 'svelte-i18n';
  import TopNav from '$lib/components/TopNav.svelte';
  import { PERMISSION, hasPermission } from '$lib/auth/permissions';

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
    <!-- Three separate questions, not one `is_staff`. Only the last is about
         Django admin, which is the one thing `is_staff` still means. -->
    <TopNav
      userName={data.user.username}
      canViewReports={hasPermission(data.user, PERMISSION.viewReports)}
      canViewImports={hasPermission(data.user, PERMISSION.viewImportSources)}
      canOpenDjangoAdmin={data.user.is_staff ?? false}
    />
  {/if}

  <main class="min-h-screen bg-neutral-100 p-5">
    {@render children()}
  </main>
{/if}
