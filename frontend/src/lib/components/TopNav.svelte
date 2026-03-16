<script lang="ts">
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { t } from 'svelte-i18n';
  import SessionIndicator from './SessionIndicator.svelte';
  import LanguageSwitcher from './LanguageSwitcher.svelte';

  interface Props {
    userName?: string;
    isAdmin?: boolean;
    currentEvent?: string;
    currentSession?: string;
    sessionTime?: string;
    onChangeSession?: () => void;
  }

  let {
    userName = 'User',
    isAdmin = false,
    currentEvent,
    currentSession,
    sessionTime,
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

  function handleLogout() {
    goto('/logout');
  }
</script>

<nav class="bg-white border-b-2 border-neutral-300 shadow-sm">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <!-- Top Bar -->
    <div class="flex justify-between items-center h-16">
      <!-- Logo/Title -->
      <div class="flex items-center">
        <h1 class="text-xl font-bold text-primary-900">{$t('nav.title')}</h1>
      </div>

      <!-- Desktop Navigation -->
      <div class="hidden md:flex items-center space-x-6">
        <a
          href="/checkin"
          class="px-4 py-2 rounded-button font-semibold transition-colors {isActive('/checkin')
            ? 'bg-primary-600 text-white'
            : 'text-neutral-700 hover:bg-neutral-100'}"
        >
          {$t('nav.checkin')}
        </a>
        <a
          href="/checkout"
          class="px-4 py-2 rounded-button font-semibold transition-colors {isActive('/checkout')
            ? 'bg-primary-600 text-white'
            : 'text-neutral-700 hover:bg-neutral-100'}"
        >
          {$t('nav.checkout')}
        </a>
        <a
          href="/print-queue"
          class="px-4 py-2 rounded-button font-semibold transition-colors {isActive('/print-queue')
            ? 'bg-primary-600 text-white'
            : 'text-neutral-700 hover:bg-neutral-100'}"
        >
          {$t('nav.printQueue')}
        </a>
        {#if isAdmin}
          <a
            href="/import"
            class="px-4 py-2 rounded-button font-semibold transition-colors {currentPath.startsWith('/import')
              ? 'bg-primary-600 text-white'
              : 'text-neutral-700 hover:bg-neutral-100'}"
          >
            {$t('import.nav')}
          </a>
          <a
            href="/admin/"
            class="px-4 py-2 rounded-button font-semibold transition-colors text-neutral-700 hover:bg-neutral-100"
          >
            {$t('nav.admin')}
          </a>
        {/if}

        <div class="border-l border-neutral-300 pl-6 ml-2 flex items-center space-x-4">
          <LanguageSwitcher />
          <span class="text-sm text-neutral-600">
            {$t('nav.welcomeMobile')}, <span class="font-semibold text-primary-900">{userName}</span>
          </span>
          <button
            onclick={handleLogout}
            class="text-sm text-danger-600 font-semibold hover:underline"
          >
            {$t('nav.logout')}
          </button>
        </div>
      </div>

      <!-- Mobile menu button -->
      <div class="md:hidden">
        <button
          onclick={toggleMobileMenu}
          class="inline-flex items-center justify-center p-2 rounded-button text-neutral-700 hover:bg-neutral-100 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-primary-500"
          aria-expanded={mobileMenuOpen}
        >
          <span class="sr-only">{$t('nav.openMenu')}</span>
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
    <div class="md:hidden border-t border-neutral-200">
      <div class="px-2 pt-2 pb-3 space-y-1">
        <a
          href="/checkin"
          onclick={closeMobileMenu}
          class="block px-3 py-2 rounded-button font-semibold {isActive('/checkin')
            ? 'bg-primary-600 text-white'
            : 'text-neutral-700 hover:bg-neutral-100'}"
        >
          {$t('nav.checkin')}
        </a>
        <a
          href="/checkout"
          onclick={closeMobileMenu}
          class="block px-3 py-2 rounded-button font-semibold {isActive('/checkout')
            ? 'bg-primary-600 text-white'
            : 'text-neutral-700 hover:bg-neutral-100'}"
        >
          {$t('nav.checkout')}
        </a>
        <a
          href="/print-queue"
          onclick={closeMobileMenu}
          class="block px-3 py-2 rounded-button font-semibold {isActive('/print-queue')
            ? 'bg-primary-600 text-white'
            : 'text-neutral-700 hover:bg-neutral-100'}"
        >
          {$t('nav.printQueue')}
        </a>
        {#if isAdmin}
          <a
            href="/import"
            onclick={closeMobileMenu}
            class="block px-3 py-2 rounded-button font-semibold {currentPath.startsWith('/import')
              ? 'bg-primary-600 text-white'
              : 'text-neutral-700 hover:bg-neutral-100'}"
          >
            {$t('import.nav')}
          </a>
          <a
            href="/admin/"
            onclick={closeMobileMenu}
            class="block px-3 py-2 rounded-button font-semibold text-neutral-700 hover:bg-neutral-100"
          >
            {$t('nav.admin')}
          </a>
        {/if}
      </div>
      <div class="pt-4 pb-3 border-t border-neutral-200">
        <div class="px-5">
          <div class="mb-3">
            <LanguageSwitcher />
          </div>
          <div class="text-sm text-neutral-600 mb-2">
            {$t('nav.loggedInAs')} <span class="font-semibold text-primary-900">{userName}</span>
          </div>
          <button
            onclick={() => {
              closeMobileMenu();
              handleLogout();
            }}
            class="w-full text-left px-3 py-2 rounded-button text-danger-600 font-semibold hover:bg-danger-50"
          >
            {$t('nav.logout')}
          </button>
        </div>
      </div>
    </div>
  {/if}
</nav>
