<script lang="ts">
  const checklist = [
    'Django backend served by Daphne',
    'PostgreSQL + Valkey services via Docker Compose',
    'SvelteKit + Tailwind starter with i18n-ready plumbing',
    'REST + realtime hooks planned for check-in/out flows'
  ];
</script>

<svelte:head>
  <title>Check-ins Migration Preview</title>
  <meta name="description" content="Django + SvelteKit reboot placeholder" />
</svelte:head>

<main>
  <div class="card">
    <div class="badge">Django + SvelteKit Migration</div>
    <h1>Welcome to the refreshed frontend</h1>
    <p>
      This SvelteKit shell is ready to connect to the new Django REST + Channels backend. Configure your
      environment variables and start iterating on check-in, ticketing, and QR flows.
    </p>
    <ul>
      {#each checklist as item}
        <li>• {item}</li>
      {/each}
    </ul>
  </div>
</main>
