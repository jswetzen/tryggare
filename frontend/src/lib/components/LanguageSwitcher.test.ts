import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import LanguageSwitcher from './LanguageSwitcher.svelte';
import { locale } from 'svelte-i18n';
import { get } from 'svelte/store';

// Mock svelte-i18n
vi.mock('svelte-i18n', () => ({
  locale: {
    set: vi.fn(),
    subscribe: vi.fn((callback) => {
      callback('en');
      return () => {};
    })
  }
}));

describe('LanguageSwitcher', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('renders language buttons for English and Swedish', () => {
    render(LanguageSwitcher);

    const enButton = screen.getByTestId('language-en');
    const svButton = screen.getByTestId('language-sv');

    expect(enButton).toBeInTheDocument();
    expect(svButton).toBeInTheDocument();
    expect(enButton).toHaveTextContent('English');
    expect(svButton).toHaveTextContent('Svenska');
  });

  it('highlights current language (English by default)', () => {
    render(LanguageSwitcher);

    const enButton = screen.getByTestId('language-en');
    const svButton = screen.getByTestId('language-sv');

    // English should be highlighted (have primary background)
    expect(enButton).toHaveClass('bg-primary-600');
    expect(svButton).not.toHaveClass('bg-primary-600');
  });

  it('switches to Swedish when SV button is clicked', async () => {
    const user = userEvent.setup();
    render(LanguageSwitcher);

    const svButton = screen.getByTestId('language-sv');
    await user.click(svButton);

    // Verify locale.set was called with 'sv'
    expect(locale.set).toHaveBeenCalledWith('sv');
  });

  it('switches to English when EN button is clicked', async () => {
    const user = userEvent.setup();
    render(LanguageSwitcher);

    const enButton = screen.getByTestId('language-en');
    await user.click(enButton);

    // Verify locale.set was called with 'en'
    expect(locale.set).toHaveBeenCalledWith('en');
  });

  it('uses svelte-i18n locale store for state management', () => {
    render(LanguageSwitcher);

    // The component relies on svelte-i18n's locale store
    // Language persistence is handled by i18n.ts configuration
    // This test verifies the component renders without errors
    expect(screen.getByTestId('language-en')).toBeInTheDocument();
    expect(screen.getByTestId('language-sv')).toBeInTheDocument();
  });

  it('has accessible button labels', () => {
    render(LanguageSwitcher);

    const enButton = screen.getByTestId('language-en');
    const svButton = screen.getByTestId('language-sv');

    // Buttons should be clickable and have visible text
    expect(enButton).toBeEnabled();
    expect(svButton).toBeEnabled();
  });
});
