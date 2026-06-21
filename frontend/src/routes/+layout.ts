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
    id: string;
    username: string;
    name: string;
    is_staff: boolean;
  };
}

export async function load({ url }) {
  // Skip auth check entirely on login page, the privacy notice, or if not in
  // browser — both are publicly accessible without logging in. QR pages are
  // also publicly accessible but are handled separately below: they still
  // attempt an auth check (without redirecting) so logged-in staff see the
  // fuller view.
  if (!browser || url.pathname === '/login' || url.pathname === '/privacy') {
    return { user: null };
  }

  if (url.pathname.startsWith('/qr/')) {
    // QR pages are publicly accessible; still check auth so logged-in staff
    // see full child details instead of the limited public view.
    try {
      const data = await apiClient.get<AuthCheckResponse>('/auth/check/');
      return { user: data.authenticated && data.user ? data.user : null };
    } catch {
      return { user: null };
    }
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
