/**
 * Server-side login handler
 * Handles login on the server to ensure session cookies are properly set
 */

import { redirect, fail } from '@sveltejs/kit';
import type { Actions } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';

const API_BASE_URL = env.VITE_API_BASE_URL || 'http://localhost:8000';

export const actions: Actions = {
  default: async ({ request, cookies }) => {
    console.log('=== LOGIN ACTION START ===');
    console.log('Cookies in login request:', cookies.getAll());

    const data = await request.formData();
    const username = data.get('username');
    const password = data.get('password');

    if (!username || !password) {
      return fail(400, { error: 'Username and password are required' });
    }

    let cookieData: Record<string, { value: string; options: any }> = {};

    try {
      // Get CSRF token
      const csrfResponse = await fetch(`${API_BASE_URL}/api/csrf/`, {
        credentials: 'include',
      });

      // Extract cookies from Django response
      const djangoCookies: string[] = [];
      csrfResponse.headers.forEach((value, key) => {
        if (key.toLowerCase() === 'set-cookie') {
          djangoCookies.push(value);
        }
      });

      const { csrfToken } = await csrfResponse.json();

      // Build cookie header from Django's Set-Cookie headers
      const cookieHeader = djangoCookies
        .map(cookie => cookie.split(';')[0])
        .join('; ');

      // Perform login with cookies
      const loginResponse = await fetch(`${API_BASE_URL}/api/auth/login/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
          'Cookie': cookieHeader,
        },
        body: JSON.stringify({ username, password }),
      });

      if (!loginResponse.ok) {
        const errorData = await loginResponse.json();
        return fail(401, { error: errorData.error || 'Invalid credentials' });
      }

      const result = await loginResponse.json();

      if (!result.success) {
        return fail(401, { error: 'Login failed' });
      }

      console.log('Login successful, processing cookies...');
      console.log('All response headers:', Array.from(loginResponse.headers.entries()));

      // Extract ALL cookies from BOTH csrf and login responses
      // We need both the CSRF cookie and the session cookie
      const allCookies = new Map<string, { value: string; options: any }>();

      // Helper function to parse Set-Cookie header
      const parseCookie = (cookieHeader: string) => {
        const cookieParts = cookieHeader.split(';');
        const cookieNameValue = cookieParts[0].trim();
        const [cookieName, cookieValue] = cookieNameValue.split('=');

        if (!cookieName || cookieValue === undefined) {
          console.error('Invalid cookie:', cookieHeader);
          return null;
        }

        // Extract cookie options
        const options: any = {
          path: '/',
          httpOnly: false, // Must be false so cookies are accessible to forward to Django
          sameSite: 'lax', // Important for security and functionality
        };

        cookieParts.slice(1).forEach(part => {
          const trimmedPart = part.trim().toLowerCase();

          // Skip httponly flag - we need httpOnly: false
          if (trimmedPart === 'httponly') {
            return;
          }

          const eqIndex = trimmedPart.indexOf('=');
          if (eqIndex === -1) {
            // Handle flags without values
            if (trimmedPart === 'secure') {
              options.secure = true;
            }
            return;
          }

          const key = trimmedPart.substring(0, eqIndex);
          const val = trimmedPart.substring(eqIndex + 1);

          if (key === 'path') options.path = val;
          if (key === 'max-age') options.maxAge = parseInt(val);
          if (key === 'samesite') options.sameSite = val;
        });

        return { cookieName, cookieValue, options };
      };

      // Get cookies from CSRF response
      csrfResponse.headers.forEach((value, key) => {
        if (key.toLowerCase() === 'set-cookie') {
          const parsed = parseCookie(value);
          if (parsed) {
            allCookies.set(parsed.cookieName, {
              value: parsed.cookieValue,
              options: parsed.options
            });
            console.log(`Captured CSRF cookie: ${parsed.cookieName}`);
          }
        }
      });

      // Get cookies from login response (may override CSRF cookies)
      loginResponse.headers.forEach((value, key) => {
        if (key.toLowerCase() === 'set-cookie') {
          const parsed = parseCookie(value);
          if (parsed) {
            allCookies.set(parsed.cookieName, {
              value: parsed.cookieValue,
              options: parsed.options
            });
            console.log(`Captured login cookie: ${parsed.cookieName}`);
          }
        }
      });

      console.log('All cookies to set:', Array.from(allCookies.keys()));

      // Prepare cookie data to send to client
      allCookies.forEach((cookie, cookieName) => {
        console.log(`Preparing cookie for client: ${cookieName} = ${cookie.value.substring(0, 20)}...`);
        cookieData[cookieName] = {
          value: cookie.value,
          options: cookie.options
        };
        // Also set on server side
        cookies.set(cookieName, cookie.value, cookie.options);
      });

      console.log('Cookies set successfully');
      console.log('Cookies after setting:', cookies.getAll());
    } catch (error) {
      console.error('Login error:', error);
      return fail(500, { error: 'Network error' });
    }

    // Return success with cookie data for client-side setting
    console.log('=== LOGIN ACTION END - SUCCESS ===');
    return { success: true, cookies: cookieData };
  },
};
