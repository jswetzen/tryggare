import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import LoginPage from '../../../routes/login/+page.svelte';
import { goto } from '$app/navigation';

// Mock svelte-i18n
vi.mock('svelte-i18n', () => ({
  t: {
    subscribe: vi.fn((callback) => {
      callback((key: string) => {
        const translations: Record<string, string> = {
          'login.pageTitle': 'Login - Conference Check-In',
          'login.title': 'Login',
          'login.username': 'Username',
          'login.password': 'Password',
          'login.usernamePlaceholder': 'Enter username',
          'login.passwordPlaceholder': 'Enter password',
          'login.submit': 'Login',
          'login.loggingIn': 'Logging in...'
        };
        return translations[key] || key;
      });
      return () => {};
    })
  }
}));

// Mock API client
vi.mock('$lib/api/client', () => ({
  apiClient: {
    post: vi.fn()
  }
}));

describe('Login Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    delete (window as any).location;
    (window as any).location = { href: '' };
  });

  it('renders login form with username and password fields', () => {
    render(LoginPage);

    expect(screen.getByLabelText('Username')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Login' })).toBeInTheDocument();
  });

  it('has required attributes on form fields', () => {
    render(LoginPage);

    const usernameInput = screen.getByLabelText('Username');
    const passwordInput = screen.getByLabelText('Password');

    expect(usernameInput).toHaveAttribute('required');
    expect(passwordInput).toHaveAttribute('required');
    expect(passwordInput).toHaveAttribute('type', 'password');
  });

  it('has HTML5 validation on required fields', () => {
    render(LoginPage);

    const usernameInput = screen.getByLabelText('Username');
    const passwordInput = screen.getByLabelText('Password');

    // HTML5 required attribute prevents form submission with empty fields
    expect(usernameInput).toHaveAttribute('required');
    expect(passwordInput).toHaveAttribute('required');

    // Browser would block submission, showing native validation messages
  });

  it('submits form with username and password', async () => {
    const user = userEvent.setup();
    const { apiClient } = await import('$lib/api/client');
    (apiClient.post as any).mockResolvedValue({ success: true });

    render(LoginPage);

    const usernameInput = screen.getByLabelText('Username');
    const passwordInput = screen.getByLabelText('Password');
    const submitButton = screen.getByRole('button', { name: 'Login' });

    await user.type(usernameInput, 'testuser');
    await user.type(passwordInput, 'testpass123');
    await user.click(submitButton);

    expect(apiClient.post).toHaveBeenCalledWith('/auth/login/', {
      username: 'testuser',
      password: 'testpass123'
    });
  });

  it('shows loading state during login', async () => {
    const user = userEvent.setup();
    const { apiClient } = await import('$lib/api/client');

    // Make API call hang to test loading state
    (apiClient.post as any).mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)));

    render(LoginPage);

    const usernameInput = screen.getByLabelText('Username');
    const passwordInput = screen.getByLabelText('Password');
    const submitButton = screen.getByRole('button', { name: 'Login' });

    await user.type(usernameInput, 'testuser');
    await user.type(passwordInput, 'testpass123');
    await user.click(submitButton);

    // Button should show loading text and be disabled
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Logging in...' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Logging in...' })).toBeDisabled();
    });
  });

  it('redirects to check-in page on successful login', async () => {
    const user = userEvent.setup();
    const { apiClient } = await import('$lib/api/client');
    (apiClient.post as any).mockResolvedValue({ success: true });

    render(LoginPage);

    const usernameInput = screen.getByLabelText('Username');
    const passwordInput = screen.getByLabelText('Password');
    const submitButton = screen.getByRole('button', { name: 'Login' });

    await user.type(usernameInput, 'testuser');
    await user.type(passwordInput, 'testpass123');
    await user.click(submitButton);

    await waitFor(() => {
      expect(window.location.href).toBe('/checkin');
    });
  });

  it('displays error message on login failure', async () => {
    const user = userEvent.setup();
    const { apiClient } = await import('$lib/api/client');
    (apiClient.post as any).mockRejectedValue({
      details: { error: 'Invalid credentials' }
    });

    render(LoginPage);

    const usernameInput = screen.getByLabelText('Username');
    const passwordInput = screen.getByLabelText('Password');
    const submitButton = screen.getByRole('button', { name: 'Login' });

    await user.type(usernameInput, 'baduser');
    await user.type(passwordInput, 'badpass');
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
    });
  });

  it('displays generic error message when no specific error provided', async () => {
    const user = userEvent.setup();
    const { apiClient } = await import('$lib/api/client');
    (apiClient.post as any).mockRejectedValue(new Error('Network error'));

    render(LoginPage);

    const usernameInput = screen.getByLabelText('Username');
    const passwordInput = screen.getByLabelText('Password');
    const submitButton = screen.getByRole('button', { name: 'Login' });

    await user.type(usernameInput, 'testuser');
    await user.type(passwordInput, 'testpass123');
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });
  });

  it('re-enables submit button after login failure', async () => {
    const user = userEvent.setup();
    const { apiClient } = await import('$lib/api/client');
    (apiClient.post as any).mockRejectedValue({
      details: { error: 'Invalid credentials' }
    });

    render(LoginPage);

    const usernameInput = screen.getByLabelText('Username');
    const passwordInput = screen.getByLabelText('Password');
    const submitButton = screen.getByRole('button', { name: 'Login' });

    await user.type(usernameInput, 'testuser');
    await user.type(passwordInput, 'testpass123');
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
    });

    // Button should be re-enabled after error
    expect(submitButton).not.toBeDisabled();
    expect(submitButton).toHaveTextContent('Login');
  });
});
