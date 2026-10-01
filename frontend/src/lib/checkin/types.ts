/**
 * Type definitions for the check-in system
 * Based on the specification in checkin-experiment/docs/CHECKIN_UX_SPEC.md section 8
 */

export type TicketType = 'event' | 'session' | 'none';

/** Why someone may be checked in without holding a ticket for the session: the rule does not
 *  ask their kind of person for one, or they are a guardian-only adult on a confirmed
 *  registration. Display only; the allow/block decision is `ticket !== 'none'`. */
export type TicketExemption = 'not_required' | 'guardian_only';

export interface Child {
  id: string;
  first_name: string;
  last_name: string;
  name: string; // Computed from first_name + last_name
  ticket: TicketType;
  ticket_type: TicketType; // Backend field name
  ticketExemption?: TicketExemption;
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
  /** Null when the viewer may not read the text — see has_safety_info. */
  allergies?: string | null;
  notes?: string | null;
  /**
   * There is allergy/emergency-medical text on this record. Always present,
   * for every viewer. A viewer who may not read the text still needs to know
   * it exists — a door volunteer is the person who most needs to know about a
   * peanut allergy — and reveals it through an explicit, audited action.
   */
  has_safety_info?: boolean;
  health_consent_status?: 'not_applicable' | 'granted' | 'declined' | 'withdrawn' | 'needs_reconfirmation';
  qr_token?: string;
}

export interface Parent {
  id: string;
  first_name: string;
  last_name: string;
  name: string;
  phone?: string;
  email?: string;
  relationship_type: string;
  ticket: TicketType;
  ticket_type: TicketType;
  ticketExemption?: TicketExemption;
  /** The session never checks adults in (adults_not_checked_in). */
  notCheckedInHere?: boolean;
  /** Adults: names of the OTHER sessions they are currently checked in to (check-in is per session). */
  checkedInElsewhere?: string[];
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
  checkInTime?: string;
  checkInActionId?: string;
  checkInRecordId?: string;
  family?: string;
  is_parent?: boolean;
  /** Null when the viewer may not read the text — see has_safety_info. */
  allergies?: string | null;
  notes?: string | null;
  /** See Child.has_safety_info. Adults carry these fields too. */
  has_safety_info?: boolean;
  health_consent_status?: 'not_applicable' | 'granted' | 'declined' | 'withdrawn' | 'needs_reconfirmation';
}

export interface PendingPayment {
  registration_id: string;
  reference_code: string;
  amount_owed: string;
  currency: string;
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
  pending_payment?: PendingPayment | null;
}

export type ParentCheckinPolicy = 'disabled' | 'open' | 'ticket_required';

/** Who needs a ticket to be checked in to a session (server-enforced; see
 *  checkins/eligibility.py). A blank Session.ticket_rule inherits the event default. */
export type TicketRule = 'open' | 'children' | 'all';

export interface Session {
  id: string;
  event: string;
  name: string;
  start_time: string;
  end_time?: string;
  is_active: boolean;
  event_name: string;
  requires_ticket: boolean;
  /** The session's own ticket rule; blank inherits the event default. */
  ticket_rule?: TicketRule | '';
  /** The rule actually in force (own rule, else the event default). The check-in UI
   *  reads this and adults_not_checked_in; requires_ticket and
   *  effective_parent_checkin_policy are derived, read-only compatibility values the
   *  server still derives from these (mergeFamilies falls back to them only when this is missing). */
  effective_ticket_rule?: TicketRule;
  /** True for drop-off sessions where no adult is checked in (guardians included). */
  adults_not_checked_in?: boolean;
  /** DEPRECATED: no longer returned by the API (the column drives nothing).
   *  Blank meant "inherit the event's default" — read effective_parent_checkin_policy instead.
   *  Optional (rather than required) only to avoid widening the pre-existing structural
   *  mismatch with the separate Session type in $lib/api/types — both are always present
   *  on the actual API response. */
  parent_checkin_policy?: ParentCheckinPolicy | '';
  effective_parent_checkin_policy?: ParentCheckinPolicy;
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
  parents: Array<{
    id: string;
    first_name: string;
    last_name: string;
    name: string;
    phone?: string;
    email?: string;
    relationship_type: string;
    ticket_type: string | null;
    /** Events where this adult is a guardian-only adult on a CONFIRMED registration. */
    guardian_only_event_ids?: string[];
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
    } | null;
    family: string;
    allergies?: string | null;
    notes?: string | null;
    has_safety_info?: boolean;
    health_consent_status?: 'not_applicable' | 'granted' | 'declined' | 'withdrawn' | 'needs_reconfirmation';
    last_participation_date?: string;
    is_checked_in?: boolean;
    active_checkin_id?: string | null;
    /** Names of the OTHER sessions this adult is checked in to; only sent with ?session=. */
    checked_in_elsewhere?: string[];
  }>;
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
    allergies?: string | null;
    notes?: string | null;
    has_safety_info?: boolean;
    health_consent_status?: 'not_applicable' | 'granted' | 'declined' | 'withdrawn' | 'needs_reconfirmation';
    qr_token?: string;
    is_checked_in?: boolean;
    active_checkin_id?: string | null;
  }>;
  last_participation_date?: string;
  pending_payment?: PendingPayment | null;
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
