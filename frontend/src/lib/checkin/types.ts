/**
 * Type definitions for the check-in system
 * Based on the specification in checkin-experiment/docs/CHECKIN_UX_SPEC.md section 8
 */

export type TicketType = 'event' | 'session' | 'none';

export interface Child {
  id: number;
  name: string;
  ticket: TicketType;
  checkedIn: boolean;
  checkInTime?: string; // "9:15 AM"
  checkInActionId?: string; // UUID linking to undo action
}

export interface Family {
  id: number;
  name: string;
  children: Child[];
  lastCheckInTime?: number; // Unix timestamp
}

export interface UndoAction {
  id: string; // UUID
  familyId: number;
  childIds: number[]; // Children affected by this action
  timestamp: number; // Unix timestamp when action occurred
  expiresAt: number; // timestamp + 30000 (30 seconds)
}

export const GRACE_PERIOD_MS = 30000; // 30 seconds
