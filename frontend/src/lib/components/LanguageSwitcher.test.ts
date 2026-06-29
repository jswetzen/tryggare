import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import LanguageSwitcher from './LanguageSwitcher.svelte';
import { locale } from 'svelte-i18n';

// Mock svelte-i18n: locale store (defaults to 'en') + a passthrough `t`.
vi.mock('svelte-i18n', () => ({
  locale: {
    set: vi.fn(),
    subscribe: vi.fn((callback) => {
      callback('en');
      return () => {};
    })
  },
  t: {
    subscribe: vi.fn((callback) => {
      callback((key: string) => key);
      return () => {};
    })
  }
}));

describe('LanguageSwitcher', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('renders a compact toggle showing the current language', () => {
    render(LanguageSwitcher);

    const toggle = screen.getByTestId('language-toggle');
    expect(toggle).toBeInTheDocument();
    expect(toggle).toHaveTextContent('EN');
  });

  it('keeps the language options collapsed until opened', () => {
    render(LanguageSwitcher);

    expect(screen.queryByTestId('language-en')).not.toBeInTheDocument();
    expect(screen.queryByTestId('language-sv')).not.toBeInTheDocument();
  });

  it('opens a dropdown with English and Swedish options', async () => {
    const user = userEvent.setup();
    render(LanguageSwitcher);

    await user.click(screen.getByTestId('language-toggle'));

    const enOption = screen.getByTestId('language-en');
    const svOption = screen.getByTestId('language-sv');

    expect(enOption).toHaveTextContent('English');
    expect(svOption).toHaveTextContent('Svenska');
    // English is the active locale by default
    expect(enOption).toHaveAttribute('aria-selected', 'true');
    expect(svOption).toHaveAttribute('aria-selected', 'false');
  });

  it('switches to Swedish when the Svenska option is clicked', async () => {
    const user = userEvent.setup();
    render(LanguageSwitcher);

    await user.click(screen.getByTestId('language-toggle'));
    await user.click(screen.getByTestId('language-sv'));

    expect(locale.set).toHaveBeenCalledWith('sv');
  });

  it('switches to English when the English option is clicked', async () => {
    const user = userEvent.setup();
    render(LanguageSwitcher);

    await user.click(screen.getByTestId('language-toggle'));
    await user.click(screen.getByTestId('language-en'));

    expect(locale.set).toHaveBeenCalledWith('en');
  });

  it('gives the toggle an accessible label and menu semantics', () => {
    render(LanguageSwitcher);

    const toggle = screen.getByTestId('language-toggle');
    expect(toggle).toHaveAttribute('aria-label');
    expect(toggle).toHaveAttribute('aria-haspopup', 'listbox');
    expect(toggle).toBeEnabled();
  });
});
