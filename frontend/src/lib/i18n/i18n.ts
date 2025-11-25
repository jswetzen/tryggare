import { register, init, getLocaleFromNavigator } from 'svelte-i18n';

// Register translation files
register('en', () => import('./locales/en.json'));
register('sv', () => import('./locales/sv.json'));

// Initialize with browser locale or default to English
init({
  fallbackLocale: 'en',
  initialLocale: getLocaleFromNavigator(),
});
