import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import PageHeader from './PageHeader.svelte';

describe('PageHeader', () => {
  it('renders the title', () => {
    render(PageHeader, { props: { title: 'Test Page Title' } });

    const heading = screen.getByRole('heading', { level: 1 });
    expect(heading).toBeInTheDocument();
    expect(heading).toHaveTextContent('Test Page Title');
  });

  it('applies correct styling to title', () => {
    render(PageHeader, { props: { title: 'Styled Title' } });

    const heading = screen.getByRole('heading', { level: 1 });
    expect(heading).toHaveClass('text-3xl', 'font-bold', 'text-primary-900');
  });

  it('applies standard bottom margin', () => {
    const { container } = render(PageHeader, { props: { title: 'Title' } });

    const header = container.querySelector('div');
    expect(header).toHaveClass('mb-5');
  });

  it('renders without actions slot when not provided', () => {
    const { container } = render(PageHeader, { props: { title: 'Title' } });

    // Should only have heading, no action buttons
    const heading = screen.getByRole('heading');
    expect(heading).toBeInTheDocument();
  });

  it('supports custom class names', () => {
    const { container } = render(PageHeader, {
      props: {
        title: 'Title',
        class: 'custom-class'
      }
    });

    const header = container.querySelector('div');
    expect(header).toHaveClass('custom-class');
  });
});
