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
  requires_ticket: boolean;
}

export interface Event {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
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
  supervised: boolean;
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
  qr_code: string | null;
  session_name: string;
  check_in_time: string;
  parents: Parent[];
  allergies?: string;
  notes?: string;
  label_printed: boolean;
  print_job?: {
    id: string;
    printer: string | null;
    printer_name: string | null;
    status: string;
  } | null;
}

export interface Printer {
  id: string;
  name: string;
  is_online: boolean;
  last_seen_at?: string | null;
  created_at?: string;
  token_active?: boolean;
}

/** Returned only by provision / rotate-token — includes the plaintext token once. */
export interface PrinterWithToken extends Printer {
  token: string;
}

export interface PrintJob {
  id: string;
  checkin: string;
  printer: string | null;
  printer_name: string | null;
  status: 'pending' | 'sent' | 'completed' | 'failed';
  created_at?: string;
  sent_at?: string | null;
  completed_at?: string | null;
}

// WebSocket message types
export interface CheckInMessage {
  type: 'child_checked_in';
  data: {
    record_id: string;
    child_id: string;
    child_name: string;
    child_last_name: string;
    session_id: string;
    session_name: string;
    check_in_time: string;
    qr_code: string;
    supervised: boolean;
    allergies?: string;
    notes?: string;
    parents?: Parent[];
  };
}

// QR page response type (new privacy-first API)
export interface QRInfoResponse {
  qr_code: string;
  checkin_record_id: string;
  child: {
    id: string;
    first_name: string;
    last_name: string;
    birthdate?: string;
    allergies?: string;
    notes?: string;
  };
  current_session: {
    id: string;
    name: string;
    check_in_time: string;
  };
  parents: Array<{
    id: string;
    name: string;
    phone?: string;
    email?: string;
    relationship_type: string;
  }>;
  family_id: string;
  supervised: boolean;
}

export interface PrivacyInfoResponse {
  controller_name: string;
  contact_email: string;
  controller_url: string;
  privacy_policy_url: string;
  retention_days: number;
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

export interface CheckInUndoneMessage {
  type: 'checkin_undone';
  data: {
    record_id: string;
    child_id: string;
    child_name: string;
    session_id: string;
    session_name: string;
  };
}

export interface CheckOutUndoneMessage {
  type: 'checkout_undone';
  data: {
    record_id: string;
    child_id: string;
    child_name: string;
    session_id: string;
    session_name: string;
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

export interface PrinterStatusChangedMessage {
  type: 'printer_status_changed';
  data: {
    uuid: string;
    name: string;
    is_online: boolean;
  };
}

export interface PrinterRegisteredMessage {
  type: 'printer_registered';
  data: {
    uuid: string;
    name: string;
    is_online: boolean;
  };
}

export interface PrintJobMessage {
  type: 'print_job';
  data: {
    job_id: string;
    printer_id: string;
    label_url: string;
  };
}

export interface PrintJobCompletedMessage {
  type: 'print_job_completed';
  data: {
    job_id: string;
    record_id: string;
  };
}

export type WebSocketMessage =
  | CheckInMessage
  | CheckOutMessage
  | CheckInUndoneMessage
  | CheckOutUndoneMessage
  | SessionStartedMessage
  | SessionEndedMessage
  | ConnectionEstablishedMessage
  | PrinterStatusChangedMessage
  | PrinterRegisteredMessage
  | PrintJobMessage
  | PrintJobCompletedMessage;

export interface DiscoveredPrefix {
  prefix: string;
  sample_children: string[];
  booking_count: number;
}

export interface DiscoverPrefixesResponse {
  prefixes: DiscoveredPrefix[];
  total_bookings: number;
}

export interface FestivalProConfig {
  login_url: string;
  export_url: string;
  export_body: string;
  field_mappings: Record<string, string>;
}

export interface ImportSource {
  id: string;
  name: string;
  provider_type: 'festivalpro' | 'planningcenter';
  event: string | null;
  has_credentials: boolean;
  festivalpro_config?: FestivalProConfig;
  created_at: string;
  updated_at: string;
}

export interface ImportSourceWrite {
  name: string;
  provider_type: 'festivalpro' | 'planningcenter';
  event?: string | null;
  username?: string;
  password?: string;
  festivalpro_config?: Partial<FestivalProConfig>;
}

export interface ImportRunSummary {
  total_bookings?: number;
  total_households?: number;
  families_created?: number;
  families_skipped?: number;
  parents_created?: number;
  children_created?: number;
  children_skipped?: number;
  tickets_created?: number;
  errors?: string[];
  warnings?: string[];
}

export interface ImportRunLog {
  booking_key: string;
  action: string;
  details: string;
}

export interface ImportRun {
  id: string;
  source: string;
  triggered_by: string | null;
  triggered_by_name: string | null;
  status: 'pending' | 'running' | 'completed' | 'failed';
  started_at: string | null;
  finished_at: string | null;
  source_file_name: string;
  summary: ImportRunSummary;
  log?: ImportRunLog[];
  raw_data?: Record<string, unknown> | null;
}
