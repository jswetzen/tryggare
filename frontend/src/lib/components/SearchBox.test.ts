import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import SearchBox from './SearchBox.svelte';

// Mock svelte-i18n
vi.mock('svelte-i18n', () => ({
  t: {
    subscribe: vi.fn((callback) => {
      callback((key: string) => {
        const translations: Record<string, string> = {
          'common.searchPlaceholder': 'Search by family name...',
          'common.searchFamilies': 'Search Families'
        };
        return translations[key] || key;
      });
      return () => {};
    })
  }
}));

describe('SearchBox', () => {
  it('renders search input with default label and placeholder', () => {
    render(SearchBox);

    const input = screen.getByTestId('family-search');
    const label = screen.getByText('Search Families');

    expect(input).toBeInTheDocument();
    expect(label).toBeInTheDocument();
    expect(input).toHaveAttribute('placeholder', 'Search by family name...');
  });

  it('renders with custom label', () => {
    render(SearchBox, { props: { label: 'Custom Label' } });

    expect(screen.getByText('Custom Label')).toBeInTheDocument();
  });

  it('renders with custom placeholder', () => {
    render(SearchBox, { props: { placeholder: 'Custom placeholder' } });

    const input = screen.getByTestId('family-search');
    expect(input).toHaveAttribute('placeholder', 'Custom placeholder');
  });

  it('accepts text input', async () => {
    const user = userEvent.setup();
    render(SearchBox);

    const input = screen.getByTestId('family-search') as HTMLInputElement;
    await user.type(input, 'Smith');

    expect(input.value).toBe('Smith');
  });

  it('calls onInput callback when text is entered', async () => {
    const user = userEvent.setup();
    const onInputMock = vi.fn();
    render(SearchBox, { props: { onInput: onInputMock } });

    const input = screen.getByTestId('family-search');
    await user.type(input, 'Jones');

    // onInput should be called for each character
    expect(onInputMock).toHaveBeenCalled();
    expect(onInputMock).toHaveBeenCalledWith('J');
    expect(onInputMock).toHaveBeenCalledWith('Jo');
    expect(onInputMock).toHaveBeenCalledWith('Jon');
    expect(onInputMock).toHaveBeenCalledWith('Jone');
    expect(onInputMock).toHaveBeenCalledWith('Jones');
  });

  it('updates bindable value when text is entered', async () => {
    const user = userEvent.setup();
    let searchValue = '';

    const { component } = render(SearchBox, {
      props: {
        value: searchValue,
        onInput: (val) => { searchValue = val; }
      }
    });

    const input = screen.getByTestId('family-search');
    await user.type(input, 'Test');

    expect(searchValue).toBe('Test');
  });

  it('has proper label association for accessibility', () => {
    render(SearchBox);

    const input = screen.getByTestId('family-search');
    const label = screen.getByText('Search Families');

    // Label should have 'for' attribute pointing to input's id
    const inputId = input.getAttribute('id');
    expect(label).toHaveAttribute('for', inputId);
  });

  it('updates input value when onInput callback changes it', async () => {
    const user = userEvent.setup();
    let searchValue = 'Initial';

    render(SearchBox, {
      props: {
        value: searchValue,
        onInput: (val) => { searchValue = val; }
      }
    });

    const input = screen.getByTestId('family-search') as HTMLInputElement;
    expect(input.value).toBe('Initial');

    // Clear the input
    await user.clear(input);
    expect(searchValue).toBe('');
  });
});
