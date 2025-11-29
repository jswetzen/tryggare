/**
 * Root layout configuration
 * Disable SSR for pure client-side rendering in static deployment
 * Load user data client-side via API
 */

import { apiClient } from '$lib/api/client';
import { goto } from '$app/navigation';
import { browser } from '$app/environment';

export const ssr = false;
export const prerender = false;

interface AuthCheckResponse {
  authenticated: boolean;
  user?: {
    id: number;
    username: string;
    full_name: string;
  };
}

export async function load({ url }) {
  // Skip auth check on login page or if not in browser
  if (!browser || url.pathname === '/login') {
    return { user: null };
  }

  try {
    // Check authentication with Django
    const data = await apiClient.get<AuthCheckResponse>('/auth/check/');

    if (data.authenticated && data.user) {
      return { user: data.user };
    } else {
      // Not authenticated, redirect to login
      goto('/login');
      return { user: null };
    }
  } catch (error) {
    console.error('Auth check failed:', error);
    // Redirect to login on error
    goto('/login');
    return { user: null };
  }
}
