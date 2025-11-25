<script lang="ts">
  import '../app.css';

  interface LayoutData {
    user: App.Locals['user'];
  }

  let { data, children }: { data: LayoutData; children: any } = $props();

  // Debug logging
  $effect(() => {
    console.log('Layout data:', data);
    console.log('User:', data.user);
  });
</script>

{#if data.user}
  <nav class="bg-gray-800 text-white p-4">
    <div class="container mx-auto flex justify-between items-center">
      <div>
        <a href="/" class="text-xl font-bold">Check-In System</a>
      </div>
      <div class="flex items-center gap-4">
        <span>Welcome, {data.user.username}</span>
        <a href="/checkin" class="hover:text-gray-300">Check-In</a>
        <a href="/checkout" class="hover:text-gray-300">Check-Out</a>
        <a href="/logout" class="hover:text-gray-300">Logout</a>
      </div>
    </div>
  </nav>
{/if}

<main class="container mx-auto p-4">
  {@render children()}
</main>
