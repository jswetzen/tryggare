/**
 * API service functions for interacting with Django backend
 */

import { apiClient } from './client';
import type { Family, Child, Session, CheckInRecord, AuditLog } from './types';

/**
 * Family API endpoints
 */
export const familyApi = {
  list: () => apiClient.get<Family[]>('/families/'),
  get: (id: string) => apiClient.get<Family>(`/families/${id}/`),
  search: (query: string) => apiClient.get<Family[]>(`/families/?search=${encodeURIComponent(query)}`),
};

/**
 * Child API endpoints
 */
export const childApi = {
  list: (familyId?: string) => {
    const url = familyId ? `/children/?family=${familyId}` : '/children/';
    return apiClient.get<Child[]>(url);
  },
  get: (id: string) => apiClient.get<Child>(`/children/${id}/`),
  getByQrToken: (token: string) => apiClient.get<Child>(`/children/by_qr_token/?token=${token}`),
};

/**
 * Session API endpoints
 */
export const sessionApi = {
  list: () => apiClient.get<Session[]>('/sessions/'),
  get: (id: string) => apiClient.get<Session>(`/sessions/${id}/`),
  active: () => apiClient.get<Session[]>('/sessions/active/'),
};

/**
 * Check-in API endpoints
 */
export const checkInApi = {
  list: () => apiClient.get<CheckInRecord[]>('/checkins/'),
  get: (id: string) => apiClient.get<CheckInRecord>(`/checkins/${id}/`),
  active: () => apiClient.get<CheckInRecord[]>('/checkins/active/'),

  checkIn: (data: { child: string; session: string }) =>
    apiClient.post<CheckInRecord>('/checkins/check_in/', data),

  checkOut: (recordId: string, pickedUpBy?: string) =>
    apiClient.post<CheckInRecord>(`/checkins/${recordId}/check_out/`, {
      picked_up_by: pickedUpBy || '',
    }),
};

/**
 * Audit log API endpoints
 */
export const auditLogApi = {
  list: () => apiClient.get<AuditLog[]>('/audit_logs/'),
  get: (id: string) => apiClient.get<AuditLog>(`/audit_logs/${id}/`),
};

/**
 * Authentication endpoints
 * NOTE: Authentication is now handled by the auth store (lib/stores/auth.ts)
 * which uses session-based authentication instead of token-based.
 * This old authApi is kept for backwards compatibility but should not be used.
 */
