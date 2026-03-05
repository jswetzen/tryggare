import { register, init, locale, isLoading } from 'svelte-i18n';
import { derived, get } from 'svelte/store';
import { browser } from '$app/environment';

// Register translation files
register('en', () => import('./locales/en.json'));
register('sv', () => import('./locales/sv.json'));

// Initialize with Swedish as default (will be updated on client-side)
init({
  fallbackLocale: 'en',
  initialLocale: 'sv',
});

// Export a derived store that indicates when translations are ready
export const translationsReady = derived(isLoading, ($isLoading) => !$isLoading);

// Get saved language from localStorage or cookie, fallback to 'sv'
function getSavedLocale(): string {
  if (!browser) {
    return 'sv';
  }

  // Try localStorage first
  try {
    const saved = localStorage.getItem('language');
    if (saved && (saved === 'en' || saved === 'sv')) {
      console.log('[i18n] Loaded language from localStorage:', saved);
      return saved;
    }
  } catch (e) {
    console.warn('[i18n] Could not access localStorage:', e);
  }

  // Try reading cookie as fallback
  try {
    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
      const [name, value] = cookie.trim().split('=');
      if (name === 'django_language' && (value === 'en' || value === 'sv')) {
        console.log('[i18n] Loaded language from cookie:', value);
        return value;
      }
    }
  } catch (e) {
    console.warn('[i18n] Could not read cookies:', e);
  }

  // Default to Swedish
  console.log('[i18n] Using default language: sv');
  return 'sv';
}

// On client-side, load saved locale and set it
if (browser) {
  const savedLocale = getSavedLocale();
  console.log('[i18n] Setting initial locale:', savedLocale);
  locale.set(savedLocale);

  // Subscribe to locale changes and save to localStorage
  locale.subscribe((value) => {
    if (value) {
      try {
        console.log('[i18n] Saving language to localStorage:', value);
        localStorage.setItem('language', value);
        // Also update cookie for Django backend
        document.cookie = `django_language=${value}; path=/; SameSite=Lax; max-age=31536000`;
        // Update HTML lang attribute
        document.documentElement.lang = value;
        console.log('[i18n] Saved language preference and updated HTML lang:', value);
      } catch (e) {
        console.warn('[i18n] Could not save language preference:', e);
      }
    }
  });
}
