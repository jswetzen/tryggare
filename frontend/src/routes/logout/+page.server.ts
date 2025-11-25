/**
 * Server-side logout handler
 * Calls Django logout endpoint and redirects to login
 */

import { redirect } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';

const API_BASE_URL = env.VITE_API_BASE_URL || 'http://localhost:8000';

export const load = async ({ cookies, request }: { cookies: any; request: Request }) => {
  try {
    // Get CSRF token
    const csrfResponse = await fetch(`${API_BASE_URL}/api/csrf/`, {
      credentials: 'include',
      headers: {
        'Cookie': request.headers.get('cookie') || '',
      },
    });
    const { csrfToken } = await csrfResponse.json();

    // Perform logout
    await fetch(`${API_BASE_URL}/api/auth/logout/`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'X-CSRFToken': csrfToken,
        'Cookie': request.headers.get('cookie') || '',
      },
    });

    console.log('Logout successful, clearing cookies');
  } catch (error) {
    console.error('Logout error:', error);
  }

  // Delete cookies from browser
  cookies.delete('csrftoken', { path: '/' });
  cookies.delete('sessionid', { path: '/' });
  console.log('Cookies deleted');

  // Redirect to login regardless of success/failure
  throw redirect(302, '/login');
};
