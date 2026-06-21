/**
 * API service functions for interacting with Django backend
 */

import { apiClient } from './client';
import type { Family, Child, Session, CheckInRecord, AuditLog, PrintQueueItem, QRInfoResponse, PrivacyInfoResponse, Printer, PrinterWithToken, PrintJob, Event } from './types';
import type { FamilyApiResponse } from '$lib/checkin/types';

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
};

/**
 * QR code info endpoint (privacy-first - only returns data when checked in)
 */
export const qrApi = {
  /**
   * Get child info by QR code. Returns data only when actively checked in.
   * Returns 404 if code is invalid or child is not currently checked in.
   */
  getInfo: (code: string) => apiClient.get<QRInfoResponse>(`/qr/${code}/`),
};

/**
 * Privacy / data-controller API endpoints (public)
 */
export const privacyApi = {
  /**
   * Get the operator-configured data-controller details for the privacy page.
   */
  getInfo: () => apiClient.get<PrivacyInfoResponse>('/privacy/'),
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

  undo: (recordId: string) =>
    apiClient.post<void>(`/checkins/${recordId}/undo/`, {}),
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

/**
 * Checkin-specific API endpoints
 */
export const checkinApi = {
  /**
   * Get active sessions
   */
  getActiveSessions: () => apiClient.get<Session[]>('/sessions/active/'),

  /**
   * Check in a child to a session
   */
  checkIn: (data: { child: string; session: string }) =>
    apiClient.post<CheckInRecord>('/checkins/check_in/', data),

  /**
   * Get all families with nested children and parents
   */
  getFamilies: () => apiClient.get<Family[]>('/families/'),

  /**
   * Look up a family by ticket QR code (external_ticket_code)
   */
  lookupByTicket: (code: string) =>
    apiClient.get<FamilyApiResponse>(`/families/by-ticket/?code=${encodeURIComponent(code)}`),

  /**
   * Create a new family with parents and children
   */
  createFamily: (data: {
    last_name: string;
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
 * Printing API endpoints
 */
export const printingApi = {
  /**
   * List all printers
   */
  getPrinters: () => apiClient.get<Printer[]>('/printing/printers/'),

  /**
   * Create a print job for a check-in record
   */
  createJob: (data: { checkin_id: string; printer_id?: string }) =>
    apiClient.post<PrintJob>('/printing/jobs/', data),

  /**
   * Assign or reassign a printer to an existing job
   */
  assignJob: (jobId: string, printerId: string) =>
    apiClient.post<PrintJob>(`/printing/jobs/${jobId}/assign/`, { printer_id: printerId }),

  /**
   * Provision a new printer. The response includes the plaintext token ONCE —
   * copy it into the printer-client config; it is not retrievable later.
   */
  provisionPrinter: (name: string) =>
    apiClient.post<PrinterWithToken>('/printing/printers/provision/', { name }),

  /**
   * Issue a fresh token for a printer (invalidates the old one). Returns it once.
   */
  rotatePrinterToken: (printerId: string) =>
    apiClient.post<PrinterWithToken>(`/printing/printers/${printerId}/rotate-token/`, {}),

  /**
   * Revoke a printer's token without issuing a new one (disables the printer).
   */
  revokePrinterToken: (printerId: string) =>
    apiClient.post<Printer>(`/printing/printers/${printerId}/revoke-token/`, {}),
};

/**
 * Event API endpoints
 */
export const eventApi = {
  list: (): Promise<Event[]> => apiClient.get('/events/'),
};

/**
 * Ticket API endpoints
 */
export const ticketApi = {
  /**
   * Assign an event ticket to a child
   */
  assignEventTicket: (data: { child: string; event: string }) =>
    apiClient.post('/event-tickets/', data),

  /**
   * Assign a session ticket to a child
   */
  assignSessionTicket: (data: { child: string; session: string }) =>
    apiClient.post('/session-tickets/', data),
};
