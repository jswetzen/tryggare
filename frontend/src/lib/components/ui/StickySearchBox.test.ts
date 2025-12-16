import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import StickySearchBox from './StickySearchBox.svelte';

// Mock svelte-i18n
vi.mock('svelte-i18n', () => ({
  t: {
    subscribe: vi.fn((callback) => {
      callback((key: string) => {
        const translations: Record<string, string> = {
          'common.searchPlaceholder': 'Search by family name...'
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

describe('StickySearchBox', () => {
  it('renders with sticky positioning', () => {
    const { container } = render(StickySearchBox, {
      props: { value: '' }
    });

    const wrapper = container.querySelector('div');
    expect(wrapper).toHaveClass('sticky', 'top-0', 'z-10');
  });

  it('applies correct background color', () => {
    const { container } = render(StickySearchBox, {
      props: { value: '' }
    });

    const wrapper = container.querySelector('div');
    expect(wrapper).toHaveClass('bg-slate-100');
  });

  it('applies responsive padding pattern', () => {
    const { container } = render(StickySearchBox, {
      props: { value: '' }
    });

    const wrapper = container.querySelector('div');
    expect(wrapper).toHaveClass('-mx-3', 'px-3', 'md:-mx-5', 'md:px-5');
  });

  it('applies bottom padding', () => {
    const { container } = render(StickySearchBox, {
      props: { value: '' }
    });

    const wrapper = container.querySelector('div');
    expect(wrapper).toHaveClass('pb-2');
  });

  it('accepts and binds value prop', async () => {
    const user = userEvent.setup();
    let searchValue = '';

    render(StickySearchBox, {
      props: {
        value: searchValue,
        onInput: (val) => { searchValue = val; }
      }
    });

    const input = screen.getByTestId('family-search') as HTMLInputElement;
    await user.type(input, 'Test');

    expect(searchValue).toBe('Test');
  });

  it('forwards placeholder to SearchBox', () => {
    render(StickySearchBox, {
      props: {
        value: '',
        placeholder: 'Custom placeholder'
      }
    });

    const input = screen.getByTestId('family-search');
    expect(input).toHaveAttribute('placeholder', 'Custom placeholder');
  });

  it('forwards onInput callback to SearchBox', async () => {
    const user = userEvent.setup();
    const onInputMock = vi.fn();

    render(StickySearchBox, {
      props: {
        value: '',
        onInput: onInputMock
      }
    });

    const input = screen.getByTestId('family-search');
    await user.type(input, 'Test');

    expect(onInputMock).toHaveBeenCalled();
  });

  it('supports custom class names', () => {
    const { container } = render(StickySearchBox, {
      props: {
        value: '',
        class: 'custom-class'
      }
    });

    const wrapper = container.querySelector('div');
    expect(wrapper).toHaveClass('custom-class');
  });
});
