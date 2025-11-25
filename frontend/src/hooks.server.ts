/**
 * Server-side authentication hook
 * Runs on every server-side request to verify authentication
 */

import type { Handle } from '@sveltejs/kit';
import { redirect } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';

const API_BASE_URL = env.VITE_API_BASE_URL || 'http://localhost:8000';

// Public paths that don't require authentication
const PUBLIC_PATHS = ['/login', '/qr', '/debug-cookies'];

export const handle: Handle = async ({ event, resolve }) => {
  const path = event.url.pathname;

  // Check if path is public (starts with any public path)
  const isPublicPath = PUBLIC_PATHS.some(publicPath => path.startsWith(publicPath));

  // Get session cookie from request - build cookie header manually
  // to ensure we're sending exactly what Django needs
  const csrftoken = event.cookies.get('csrftoken');
  const sessionid = event.cookies.get('sessionid');

  const cookieParts: string[] = [];
  if (csrftoken) cookieParts.push(`csrftoken=${csrftoken}`);
  if (sessionid) cookieParts.push(`sessionid=${sessionid}`);
  const cookies = cookieParts.join('; ');

  let data;
  try {
    // Check authentication with Django
    const response = await fetch(`${API_BASE_URL}/api/auth/check/`, {
      headers: {
        'Cookie': cookies,
      },
      credentials: 'include',
    });

    data = await response.json();
  } catch (error) {
    // Network error or auth check failed
    event.locals.user = null;

    // Redirect to login if trying to access protected route
    if (!isPublicPath) {
      throw redirect(302, '/login');
    }

    return resolve(event);
  }

  if (data.authenticated) {
    // User is authenticated
    event.locals.user = data.user;

    // Redirect away from login page if already authenticated
    if (path === '/login') {
      throw redirect(302, '/');
    }
  } else {
    // User is not authenticated
    event.locals.user = null;

    // Redirect to login if trying to access protected route
    if (!isPublicPath) {
      throw redirect(302, '/login');
    }
  }

  return resolve(event);
};
