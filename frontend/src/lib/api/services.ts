/**
 * API service functions for interacting with Django backend
 */

import { apiClient } from './client';
import type { Family, Child, Session, CheckInRecord, AuditLog, PrintQueueItem } from './types';

/**
 * Family API endpoints
 */
export const familyApi = {
  list: () => apiClient.get<Family[]>('/families/'),
  get: (id: string) => apiClient.get<Family>(`/families/${id}/`),
  search: (query: string) => apiClient.get<Family[]>(`/families/?search=${encodeURIComponent(query)}`),
  create: (data: {
    parents: Array<{
      name: string;
      phone?: string;
      email?: string;
      relationship_type: string;
    }>;
    children: Array<{
      first_name: string;
      last_name: string;
      birthdate: string;
      allergies?: string;
      notes?: string;
    }>;
  }) => apiClient.post<Family>('/families/', data),
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
  getByQrToken: (token: string) => apiClient.get<Child>(`/qr/${token}/`),
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

  undoCheckout: (recordId: string) =>
    apiClient.post<CheckInRecord>(`/checkins/${recordId}/undo_checkout/`, {}),
};

/**
 * Audit log API endpoints
 */
export const auditLogApi = {
  list: () => apiClient.get<AuditLog[]>('/audit_logs/'),
  get: (id: string) => apiClient.get<AuditLog>(`/audit_logs/${id}/`),
};

/**
 * Print Queue API endpoints
 */
export const printQueueApi = {
  /**
   * Get all unprintable check-ins (checked in, not printed, not checked out)
   */
  getQueue: () => apiClient.get<PrintQueueItem[]>('/print-queue/'),

  /**
   * Mark one or more check-ins as printed
   */
  markPrinted: (checkinIds: string[]) =>
    apiClient.post<{ message: string; count: number }>('/print-queue/mark_printed/', {
      checkin_ids: checkinIds,
    }),

  /**
   * Mark a single check-in as printed
   */
  markSinglePrinted: (checkinId: string) =>
    apiClient.post<PrintQueueItem>(`/print-queue/${checkinId}/mark_single_printed/`, {}),

  /**
   * Get recently printed check-ins (last 50)
   */
  getRecentlyPrinted: () => apiClient.get<PrintQueueItem[]>('/print-queue/recently_printed/'),

  /**
   * Get the URL for downloading PDF labels
   */
  getPrintUrl: (checkinIds: string[]) => `/api/print-queue/generate_pdf/?ids=${checkinIds.join(',')}`,

  /**
   * Get the URL for the print page (opens in new window for printing)
   */
  getPrintPageUrl: (checkinId: string) => `/api/print-queue/${checkinId}/print_page/`,
};

/**
 * Authentication endpoints
 * NOTE: Authentication is now handled by the auth store (lib/stores/auth.ts)
 * which uses session-based authentication instead of token-based.
 * This old authApi is kept for backwards compatibility but should not be used.
 */
