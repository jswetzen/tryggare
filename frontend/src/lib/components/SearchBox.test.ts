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

// Mock Icon component
vi.mock('$lib/components/ui/Icon.svelte', () => ({
  default: vi.fn()
}));

describe('SearchBox', () => {
  it('renders search input with default placeholder', () => {
    render(SearchBox);

    const input = screen.getByTestId('family-search');

    expect(input).toBeInTheDocument();
    expect(input).toHaveAttribute('placeholder', 'Search by family name...');
  });

  it('renders with custom label when provided', () => {
    render(SearchBox, { props: { label: 'Custom Label' } });

    expect(screen.getByText('Custom Label')).toBeInTheDocument();
  });

  it('does not render label when not provided', () => {
    render(SearchBox);

    expect(screen.queryByText('Search Families')).not.toBeInTheDocument();
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

  it('does not show clear button when input is empty', () => {
    render(SearchBox);

    const clearButton = screen.queryByTestId('clear-search-button');
    expect(clearButton).not.toBeInTheDocument();
  });

  it('shows clear button when input has text', async () => {
    const user = userEvent.setup();
    render(SearchBox);

    const input = screen.getByTestId('family-search') as HTMLInputElement;
    await user.type(input, 'Smith');

    const clearButton = screen.getByTestId('clear-search-button');
    expect(clearButton).toBeInTheDocument();
  });

  it('clears input when clear button is clicked', async () => {
    const user = userEvent.setup();
    const onInputMock = vi.fn();
    render(SearchBox, { props: { onInput: onInputMock } });

    const input = screen.getByTestId('family-search') as HTMLInputElement;
    await user.type(input, 'Smith');
    expect(input.value).toBe('Smith');

    const clearButton = screen.getByTestId('clear-search-button');
    await user.click(clearButton);

    expect(input.value).toBe('');
    expect(onInputMock).toHaveBeenCalledWith('');
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

  it('clears the search field when ESC is pressed', async () => {
    const user = userEvent.setup();
    const onInputMock = vi.fn();
    let searchValue = '';

    render(SearchBox, {
      props: {
        value: searchValue,
        onInput: (val) => {
          searchValue = val;
          onInputMock(val);
        }
      }
    });

    const input = screen.getByTestId('family-search') as HTMLInputElement;

    // Type some text
    await user.type(input, 'SearchText');
    expect(input.value).toBe('SearchText');
    expect(searchValue).toBe('SearchText');

    // Press ESC key
    await user.keyboard('{Escape}');

    // Should clear the field
    expect(input.value).toBe('');
    expect(searchValue).toBe('');
    expect(onInputMock).toHaveBeenCalledWith('');
  });
});
