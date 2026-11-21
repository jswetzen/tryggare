import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';

const search = vi.hoisted(() => ({ value: '' }));
vi.mock('$app/stores', () => ({
  page: {
    subscribe: (cb: (v: unknown) => void) => {
      cb({ url: new URL(`http://x/login${search.value}`) });
      return () => {};
    }
  }
}));
vi.mock('$app/navigation', () => ({ goto: vi.fn() }));
vi.mock('$lib/api/client', () => ({
  apiClient: { get: vi.fn().mockResolvedValue({}), post: vi.fn().mockResolvedValue({}) }
}));
vi.mock('$lib/components/LanguageSwitcher.svelte', () => ({ default: function () {} }));
vi.mock('svelte-i18n', () => {
  const store = { subscribe: (cb: (v: (k: string) => string) => void) => (cb((k) => k), () => {}) };
  return { t: store, _: store, locale: { subscribe: (cb: (v: string) => void) => (cb('en'), () => {}) } };
});

import Login from './+page.svelte';

async function signIn(query: string) {
  search.value = query;
  const hrefSet = vi.fn();
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: { set href(v: string) { hrefSet(v); } }
  });
  render(Login);
  await userEvent.type(document.getElementById('username')!, 'u');
  await userEvent.type(document.getElementById('password')!, 'p');
  await userEvent.click(screen.getByRole('button', { name: 'login.submit' }));
  await waitFor(() => expect(hrefSet).toHaveBeenCalled());
  return hrefSet.mock.calls[0][0];
}

describe('/login return target', () => {
  beforeEach(() => vi.clearAllMocks());

  it('goes to /checkin without next', async () => {
    expect(await signIn('')).toBe('/checkin');
  });

  it('honours a safe next path', async () => {
    expect(await signIn('?next=%2Fevents%2Fe1%2Fsetup')).toBe('/events/e1/setup');
  });

  it.each(['//evil.example', 'https://evil.example', '/\\evil.example'])('ignores unsafe next %s', async (n) => {
    expect(await signIn(`?next=${encodeURIComponent(n)}`)).toBe('/checkin');
  });
});
