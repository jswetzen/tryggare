/**
 * API client for Django backend
 * Handles session-based authentication, HTTP requests, and error handling
 */

// Use PUBLIC_API_BASE_URL for browser (client-side) requests
// In production (same origin), use relative URL
// In development, use full URL to separate backend
const API_BASE_URL = import.meta.env.VITE_PUBLIC_API_BASE_URL || (
  import.meta.env.DEV ? 'http://localhost:8000/api' : '/api'
);

export interface ApiError {
  message: string;
  status: number;
  details?: unknown;
}

/**
 * Pulls a human-readable message out of a DRF error body. Covers the
 * shapes actually in use across this backend: plain views returning
 * {"error": "..."} (most custom @api_view/@action endpoints), DRF's own
 * {"detail": "..."} (permission/throttle/404 errors), serializer
 * {"non_field_errors": [...]}, and per-field validation errors
 * ({"field_name": ["..."]}) — falls back to the HTTP status text if none
 * of those shapes match.
 */
function extractErrorMessage(details: unknown, fallback: string): string {
  if (!details || typeof details !== 'object') return fallback;
  const body = details as Record<string, unknown>;

  if (typeof body.error === 'string') return body.error;
  if (typeof body.detail === 'string') return body.detail;

  const nonFieldErrors = body.non_field_errors;
  if (Array.isArray(nonFieldErrors) && typeof nonFieldErrors[0] === 'string') {
    return nonFieldErrors[0];
  }

  for (const value of Object.values(body)) {
    if (Array.isArray(value) && typeof value[0] === 'string') return value[0];
    if (typeof value === 'string') return value;
  }

  return fallback;
}

export class ApiClient {
  private baseUrl: string;
  private csrfToken: string | null = null;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Absolute base URL for the API, e.g. for building file-download links
   * (<a href>) that need to hit the backend directly with session cookies.
   */
  getBaseUrl(): string {
    return this.baseUrl;
  }

  /**
   * Get CSRF token from cookie or Django
   */
  async getCsrfToken(): Promise<string> {
    // First try to get from cookie
    const cookieToken = this.getCsrfTokenFromCookie();
    if (cookieToken) {
      this.csrfToken = cookieToken;
      return cookieToken;
    }

    // If not in cookie, fetch from API
    if (this.csrfToken) {
      return this.csrfToken;
    }

    const response = await fetch(`${this.baseUrl.replace('/api', '')}/api/csrf/`, {
      credentials: 'include',
    });
    const data = await response.json();
    this.csrfToken = data.csrfToken;
    return this.csrfToken;
  }

  /**
   * Get CSRF token from cookie
   */
  private getCsrfTokenFromCookie(): string | null {
    const name = 'csrftoken';
    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
      const trimmed = cookie.trim();
      if (trimmed.startsWith(name + '=')) {
        return decodeURIComponent(trimmed.substring(name.length + 1));
      }
    }
    return null;
  }

  /**
   * Clear cached CSRF token
   */
  clearCsrfToken() {
    this.csrfToken = null;
  }

  /**
   * Make authenticated request with session cookies
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    // Add CSRF token for non-GET requests
    if (options.method && options.method !== 'GET') {
      const csrfToken = await this.getCsrfToken();
      headers['X-CSRFToken'] = csrfToken;
    }

    const url = `${this.baseUrl}${endpoint}`;

    try {
      const response = await fetch(url, {
        ...options,
        headers,
        credentials: 'include', // Always send cookies for session-based auth
      });

      if (!response.ok) {
        const error: ApiError = {
          message: response.statusText,
          status: response.status,
        };

        try {
          error.details = await response.json();
          // The backend already returns a descriptive, request-locale-aware
          // message (Django's LocaleMiddleware reads the django_language
          // cookie i18n.ts sets on every locale switch) — response.statusText
          // is just the raw HTTP status line ("Bad Request") and was masking
          // it entirely. Extract the real message so callers' error toasts
          // show something a guardian/staff member can act on.
          error.message = extractErrorMessage(error.details, response.statusText);
        } catch {
          // Response body is not JSON
        }

        throw error;
      }

      // Handle 204 No Content
      if (response.status === 204) {
        return {} as T;
      }

      return await response.json();
    } catch (error) {
      if ((error as ApiError).status) {
        throw error;
      }
      throw {
        message: 'Network error',
        status: 0,
        details: error,
      } as ApiError;
    }
  }

  /**
   * GET request
   */
  async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  /**
   * POST request
   */
  async post<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * PUT request
   */
  async put<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * PATCH request
   */
  async patch<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * DELETE request
   */
  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }
}

// Export singleton instance
export const apiClient = new ApiClient();
