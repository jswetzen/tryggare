<script lang="ts">
  import { page } from '$app/stores';
  import SessionIndicator from './SessionIndicator.svelte';

  interface Props {
    userName?: string;
    currentEvent?: string;
    currentSession?: string;
    sessionTime?: string;
    onLogout?: () => void;
    onChangeSession?: () => void;
  }

  let {
    userName = 'User',
    currentEvent,
    currentSession,
    sessionTime,
    onLogout,
    onChangeSession
  }: Props = $props();

  let mobileMenuOpen = $state(false);
  let currentPath = $derived($page.url.pathname);

  function toggleMobileMenu() {
    mobileMenuOpen = !mobileMenuOpen;
  }

  function closeMobileMenu() {
    mobileMenuOpen = false;
  }

  function isActive(path: string): boolean {
    return currentPath === path;
  }
</script>

<nav class="bg-white border-b-2 border-slate-300 shadow-sm">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <!-- Top Bar -->
    <div class="flex justify-between items-center h-16">
      <!-- Logo/Title -->
      <div class="flex items-center">
        <h1 class="text-xl font-bold text-blue-900">Check-In System</h1>
      </div>

      <!-- Desktop Navigation -->
      <div class="hidden md:flex items-center space-x-6">
        <a
          href="/checkin"
          class="px-4 py-2 rounded-md font-semibold transition-colors {isActive('/checkin')
            ? 'bg-blue-600 text-white'
            : 'text-slate-700 hover:bg-slate-100'}"
        >
          Check-In
        </a>
        <a
          href="/checkout"
          class="px-4 py-2 rounded-md font-semibold transition-colors {isActive('/checkout')
            ? 'bg-blue-600 text-white'
            : 'text-slate-700 hover:bg-slate-100'}"
        >
          Check-Out
        </a>

        <div class="border-l border-slate-300 pl-6 ml-2 flex items-center space-x-4">
          <span class="text-sm text-slate-600">
            Welcome, <span class="font-semibold text-blue-900">{userName}</span>
          </span>
          {#if onLogout}
            <button
              onclick={onLogout}
              class="text-sm text-red-600 font-semibold hover:underline"
            >
              Logout
            </button>
          {/if}
        </div>
      </div>

      <!-- Mobile menu button -->
      <div class="md:hidden">
        <button
          onclick={toggleMobileMenu}
          class="inline-flex items-center justify-center p-2 rounded-md text-slate-700 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500"
          aria-expanded={mobileMenuOpen}
        >
          <span class="sr-only">Open main menu</span>
          {#if !mobileMenuOpen}
            <!-- Hamburger icon -->
            <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          {:else}
            <!-- Close icon -->
            <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          {/if}
        </button>
      </div>
    </div>

    <!-- Session Indicator (minimal, only shown if session is active) -->
    {#if currentEvent && currentSession && sessionTime}
      <div class="py-2">
        <SessionIndicator
          eventName={currentEvent}
          sessionName={currentSession}
          {sessionTime}
          {onChangeSession}
        />
      </div>
    {/if}
  </div>

  <!-- Mobile menu -->
  {#if mobileMenuOpen}
    <div class="md:hidden border-t border-slate-200">
      <div class="px-2 pt-2 pb-3 space-y-1">
        <a
          href="/checkin"
          onclick={closeMobileMenu}
          class="block px-3 py-2 rounded-md font-semibold {isActive('/checkin')
            ? 'bg-blue-600 text-white'
            : 'text-slate-700 hover:bg-slate-100'}"
        >
          Check-In
        </a>
        <a
          href="/checkout"
          onclick={closeMobileMenu}
          class="block px-3 py-2 rounded-md font-semibold {isActive('/checkout')
            ? 'bg-blue-600 text-white'
            : 'text-slate-700 hover:bg-slate-100'}"
        >
          Check-Out
        </a>
      </div>
      <div class="pt-4 pb-3 border-t border-slate-200">
        <div class="px-5">
          <div class="text-sm text-slate-600 mb-2">
            Logged in as <span class="font-semibold text-blue-900">{userName}</span>
          </div>
          {#if onLogout}
            <button
              onclick={() => {
                closeMobileMenu();
                if (onLogout) onLogout();
              }}
              class="w-full text-left px-3 py-2 rounded-md text-red-600 font-semibold hover:bg-red-50"
            >
              Logout
            </button>
          {/if}
        </div>
      </div>
    </div>
  {/if}
</nav>
