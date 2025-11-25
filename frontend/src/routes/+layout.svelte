<script lang="ts">
  import '../app.css';
  import '$lib/i18n/i18n';
  import { t } from 'svelte-i18n';
  import TopNav from '$lib/components/TopNav.svelte';

  interface LayoutData {
    user: App.Locals['user'];
  }

  let { data, children }: { data: LayoutData; children: any } = $props();
</script>

{#if data.user}
  <TopNav userName={data.user.username} />
{/if}

<main class="min-h-screen bg-slate-100 p-5">
  {@render children()}
</main>
