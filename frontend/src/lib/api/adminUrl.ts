// Django admin lives on the backend origin: separate from the SvelteKit one in dev
// (VITE_PUBLIC_API_BASE_URL=http://localhost:8000/api), the same origin in prod-like.
const API_BASE_URL: string =
  import.meta.env.VITE_PUBLIC_API_BASE_URL || (import.meta.env.DEV ? 'http://localhost:8000/api' : '/api');

export function adminUrl(path: string): string {
  return `${API_BASE_URL.replace(/\/api\/?$/, '')}${path}`;
}

export function registrationAdminUrl(registrationId: string): string {
  return adminUrl(`/admin/registrations/registration/${registrationId}/change/`);
}
