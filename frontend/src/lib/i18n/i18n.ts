import { register, init, locale } from 'svelte-i18n';

// Register translation files
register('en', () => import('./locales/en.json'));
register('sv', () => import('./locales/sv.json'));

// Initialize with English as default
// The locale can be changed later based on user preference or browser settings
init({
  fallbackLocale: 'en',
  initialLocale: 'en',
});

// Explicitly set locale to ensure it's initialized
// This fixes issues with headless browsers and SSR
locale.set('en');
