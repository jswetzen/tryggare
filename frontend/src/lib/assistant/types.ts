/**
 * Wire types for the event assistant: the WebSocket protocol and the REST
 * bodies. Plan: docs/event-assistant-plan.md ("WebSocket protocol",
 * "Backend modules and endpoints"); the server side is backend/assistant.
 */
import type { RegistrationFormSpec } from '$lib/api/types';

export type RunFailedCode =
  | 'timeout'
  | 'limit'
  | 'model_error'
  | 'provider_unreachable'
  | 'auth_failed'
  | 'cancelled'
  | 'busy'
  | 'notice_required'
  | 'blocked'
  | 'rate_limited'
  | 'not_enabled';

// Client to server.
export type ClientFrame =
  | { type: 'user_message'; id: string; text: string; confirm_personal_data?: true }
  | { type: 'cancel' };

// Server to client.
export type ServerEvent =
  | {
      type: 'ready';
      conversation_id: string;
      running: boolean;
      draft_version: number;
      notice_required: boolean;
    }
  | { type: 'run_started'; run_id: string; reply_to: string }
  | { type: 'tool_started'; run_id: string; call_id: string; tool: string }
  | { type: 'tool_finished'; run_id: string; call_id: string; tool: string; ok: boolean }
  | { type: 'text_delta'; run_id: string; text: string }
  | { type: 'draft_updated'; run_id: string; draft_version: number }
  | { type: 'run_finished'; run_id: string }
  | { type: 'run_failed'; run_id: string | null; reply_to?: string; code: RunFailedCode }
  | { type: 'warning'; code: 'personal_data'; reply_to: string }
  | { type: 'error'; code: string };

// Close codes the server uses before accepting (consumers.py).
export const CLOSE_UNAUTHENTICATED = 4401;
export const CLOSE_FORBIDDEN = 4403;
export const CLOSE_NO_EVENT = 4404;
export const CLOSE_NOT_ELIGIBLE = 4409;
export const CLOSE_NOT_ENABLED = 4503;
export const REFUSED_CLOSE_CODES: readonly number[] = [
  CLOSE_UNAUTHENTICATED,
  CLOSE_FORBIDDEN,
  CLOSE_NO_EVENT,
  CLOSE_NOT_ELIGIBLE,
  CLOSE_NOT_ENABLED
];

export interface TranscriptEntry {
  role: 'user' | 'assistant';
  text: string;
}

export interface AssistantIssue {
  path: string;
  code: string;
  message: string;
}

export interface ConversationState {
  available: boolean;
  conversation_id: string | null;
  transcript: TranscriptEntry[];
  running: boolean;
  notice_accepted: boolean;
  draft_version: number;
}

// One change from event_spec's diff: `new` for added, `old` for removed and
// `fields` ({name: {old, new}}) for changed. Choices carry a `parent` extra key.
export interface DraftDiffEntry {
  kind: string;
  key: string | null;
  change: 'added' | 'removed' | 'changed';
  parent?: string;
  new?: Record<string, unknown>;
  old?: Record<string, unknown>;
  fields?: Record<string, { old: unknown; new: unknown }>;
}

export interface DraftPayload {
  spec: unknown;
  diff: DraftDiffEntry[];
  warnings: AssistantIssue[];
  stale: boolean;
  token: string;
  version: number;
}

export interface AssistantPreview {
  source: 'draft' | 'saved';
  stale: boolean;
  draft_unusable: boolean;
  form_spec: RegistrationFormSpec;
  diff: DraftDiffEntry[];
  warnings: AssistantIssue[];
}
