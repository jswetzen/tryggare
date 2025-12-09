/**
 * TypeScript types for Django API models
 */

export interface User {
  id: string;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
}

export interface Family {
  id: string;
  last_name: string;
  display_name: string;
  parents: Parent[];
  children: Child[]; // Always populated from API
  last_participation_date?: string;
}

export interface Child {
  id: string;
  family: string;
  first_name: string;
  last_name: string;
  birthdate?: string;
  allergies?: string;
  notes?: string;
  qr_token?: string;
  last_participation_date?: string;
  ticket_type: 'event' | 'session' | 'none';
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
}

export interface Session {
  id: string;
  event: string;
  event_name: string;
  name: string;
  session_type: 'SERVICE' | 'CHILDCARE' | 'EVENT' | 'OTHER';
  start_time: string;
  end_time?: string;
  location?: string;
  capacity?: number;
  min_age_months?: number;
  max_age_months?: number;
  description?: string;
  is_active: boolean;
}

export interface CheckInRecord {
  id: string;
  child: string;
  child_name: string;
  session: string;
  session_name: string;
  check_in_staff: string;
  check_in_staff_name: string;
  check_out_staff?: string;
  check_out_staff_name?: string;
  check_in_time: string;
  check_out_time?: string;
  notes?: string;
  picked_up_by?: string;
}

export interface AuditLog {
  id: string;
  user: string;
  action: string;
  entity_type: string;
  entity_id: string;
  details?: Record<string, unknown>;
  timestamp: string;
}

export interface Parent {
  id: string;
  name: string;
  phone?: string;
  email?: string;
  relationship_type: 'MOM' | 'DAD' | 'OTHER';
}

export interface PrintQueueItem {
  id: string;
  child_name: string;
  child_last_name: string;
  qr_token: string;
  session_name: string;
  check_in_time: string;
  parents: Parent[];
  allergies?: string;
  notes?: string;
  label_printed: boolean;
}

// WebSocket message types
export interface CheckInMessage {
  type: 'child_checked_in';
  data: {
    record_id: string;
    child_id: string;
    child_name: string;
    session_id: string;
    session_name: string;
    check_in_time: string;
    qr_token: string;
  };
}

export interface CheckOutMessage {
  type: 'child_checked_out';
  data: {
    record_id: string;
    child_id: string;
    child_name: string;
    session_id: string;
    session_name: string;
    check_out_time: string;
    picked_up_by: string;
  };
}

export interface SessionStartedMessage {
  type: 'session_started';
  data: {
    session_id: string;
    session_name: string;
  };
}

export interface SessionEndedMessage {
  type: 'session_ended';
  data: {
    session_id: string;
    session_name: string;
  };
}

export interface ConnectionEstablishedMessage {
  type: 'connection_established';
  message: string;
}

export type WebSocketMessage =
  | CheckInMessage
  | CheckOutMessage
  | SessionStartedMessage
  | SessionEndedMessage
  | ConnectionEstablishedMessage;
