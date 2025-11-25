/**
 * Authentication store for SvelteKit
 * Manages session-based authentication state with Django backend
 */

import { writable } from 'svelte/store';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export interface User {
  id: string;
  username: string;
  name: string;
}

interface AuthState {
  user: User | null;
  loading: boolean;
}

function createAuthStore() {
  const { subscribe, set, update } = writable<AuthState>({
    user: null,
    loading: true,
  });

  /**
   * Fetch CSRF token from Django
   */
  async function getCsrfToken(): Promise<string> {
    const response = await fetch(`${API_BASE_URL}/api/csrf/`, {
      credentials: 'include',
    });
    const data = await response.json();
    return data.csrfToken;
  }

  /**
   * Check authentication status
   */
  async function checkAuth(): Promise<boolean> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/check/`, {
        credentials: 'include',
      });
      const data = await response.json();

      if (data.authenticated) {
        set({ user: data.user, loading: false });
        return true;
      } else {
        set({ user: null, loading: false });
        return false;
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      set({ user: null, loading: false });
      return false;
    }
  }

  /**
   * Login with username and password
   */
  async function login(username: string, password: string): Promise<{ success: boolean; error?: string }> {
    try {
      // Get CSRF token first
      const csrfToken = await getCsrfToken();

      // Attempt login
      const response = await fetch(`${API_BASE_URL}/api/auth/login/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        credentials: 'include',
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        set({ user: data.user, loading: false });
        return { success: true };
      } else {
        return { success: false, error: data.error || 'Login failed' };
      }
    } catch (error) {
      console.error('Login error:', error);
      return { success: false, error: 'Network error' };
    }
  }

  /**
   * Logout current user
   */
  async function logout(): Promise<void> {
    try {
      // Get CSRF token first
      const csrfToken = await getCsrfToken();

      // Attempt logout
      await fetch(`${API_BASE_URL}/api/auth/logout/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrfToken,
        },
        credentials: 'include',
      });

      set({ user: null, loading: false });
    } catch (error) {
      console.error('Logout error:', error);
      set({ user: null, loading: false });
    }
  }

  return {
    subscribe,
    checkAuth,
    login,
    logout,
    getCsrfToken,
  };
}

export const authStore = createAuthStore();
