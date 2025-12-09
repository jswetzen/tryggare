/**
 * Type definitions for the check-in system
 * Based on the specification in checkin-experiment/docs/CHECKIN_UX_SPEC.md section 8
 */

export type TicketType = 'event' | 'session' | 'none';

export interface Child {
  id: string;
  first_name: string;
  last_name: string;
  name: string; // Computed from first_name + last_name
  ticket: TicketType;
  ticket_type: TicketType; // Backend field name
  ticket_details?: {
    event_tickets: Array<{
      id: string;
      event: string;
      event_name: string;
    }>;
    session_tickets: Array<{
      id: string;
      session: string;
      session_name: string;
    }>;
  };
  checkedIn: boolean;
  checkInTime?: string; // "9:15 AM"
  checkInActionId?: string; // UUID linking to undo action
  checkInRecordId?: string; // Backend check-in record ID for API calls
  family: string; // Family ID
  birthdate?: string;
  allergies?: string;
  notes?: string;
  qr_token?: string;
}

export interface Parent {
  id: string;
  name: string;
  phone?: string;
  email?: string;
  relationship_type: string;
}

export interface Family {
  id: string;
  last_name: string;
  display_name: string;
  name: string; // Computed from display_name for backward compatibility
  children: Child[];
  parents: Parent[];
  lastCheckInTime?: number; // Unix timestamp
  last_participation_date?: string;
}

export interface Session {
  id: string;
  event: string;
  name: string;
  start_time: string;
  end_time?: string;
  is_active: boolean;
  event_name: string;
}

export interface UndoAction {
  id: string; // UUID
  familyId: string;
  childIds: string[]; // Children affected by this action
  timestamp: number; // Unix timestamp when action occurred
  expiresAt: number; // timestamp + 30000 (30 seconds)
}

export const GRACE_PERIOD_MS = 30000; // 30 seconds

// API Response types
export interface FamilyApiResponse {
  id: string;
  last_name: string;
  display_name: string;
  parents: Parent[];
  children: Array<{
    id: string;
    first_name: string;
    last_name: string;
    ticket_type: string;
    ticket_details?: {
      event_tickets: Array<{
        id: string;
        event: string;
        event_name: string;
      }>;
      session_tickets: Array<{
        id: string;
        session: string;
        session_name: string;
      }>;
    };
    family: string;
    birthdate?: string;
    allergies?: string;
    notes?: string;
    qr_token?: string;
    is_checked_in?: boolean;
    active_checkin_id?: string | null;
  }>;
  last_participation_date?: string;
}

export interface CheckInResponse {
  id: string;
  child: string;
  child_name: string;
  session: string;
  session_name: string;
  check_in_time: string;
  check_in_staff: string;
  check_in_staff_name: string;
}
