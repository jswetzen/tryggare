import { describe, it, expect, beforeEach, vi } from 'vitest';

// svelte-i18n's init(initialLocale) starts loading every locale; a later
// locale.set() of a saved choice then resolves at once and the init's own
// locale lands after it. So the saved choice has to be the initialLocale,
// with no second locale.set at start-up.
const i18n = vi.hoisted(() => ({
  init: vi.fn(),
  set: vi.fn(),
  register: vi.fn()
}));
vi.mock('svelte-i18n', async () => {
  const { writable } = await import('svelte/store');
  const store = writable<string | null>(null);
  return {
    register: i18n.register,
    init: i18n.init,
    isLoading: writable(false),
    locale: { subscribe: store.subscribe, set: i18n.set }
  };
});

describe('i18n start-up locale', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    vi.mocked(localStorage.getItem).mockReturnValue(null);
    document.cookie = 'django_language=; max-age=0; path=/';
  });

  it('starts in the saved language instead of setting it after an sv init', async () => {
    vi.mocked(localStorage.getItem).mockImplementation((k) => (k === 'language' ? 'en' : null));
    await import('./i18n');
    expect(i18n.init).toHaveBeenCalledWith(expect.objectContaining({ initialLocale: 'en' }));
    expect(i18n.set).not.toHaveBeenCalled();
  });

  it('falls back to the cookie, then to Swedish', async () => {
    document.cookie = 'django_language=en; path=/';
    await import('./i18n');
    expect(i18n.init).toHaveBeenCalledWith(expect.objectContaining({ initialLocale: 'en' }));

    vi.resetModules();
    vi.clearAllMocks();
    document.cookie = 'django_language=; max-age=0; path=/';
    await import('./i18n');
    expect(i18n.init).toHaveBeenCalledWith(expect.objectContaining({ initialLocale: 'sv' }));
  });
});
