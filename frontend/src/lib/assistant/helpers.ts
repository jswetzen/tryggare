/** Pure helpers shared by the register page and the /setup route. */
import type { ApiError } from '$lib/api/client';
import type { AssistantIssue, DraftDiffEntry } from './types';

export function setupRedirectUrl(eventId: string): string {
  return `/register/${encodeURIComponent(eventId)}?preview=1&assistant=1`;
}

export const isAssistantRequested = (params: URLSearchParams): boolean =>
  params.get('assistant') === '1';

// assistant=1 implies preview, so the existing preview behaviour (window
// gates bypassed, submit disabled) applies with no second code path.
export const isPreviewRequested = (params: URLSearchParams): boolean =>
  params.get('preview') === '1' || isAssistantRequested(params);

// Statuses on which the page falls back to the saved spec (plan: Auth).
const FALLBACK_STATUSES = new Set([401, 403, 404, 409, 503]);
export const isFallbackStatus = (err: unknown): boolean =>
  FALLBACK_STATUSES.has((err as ApiError | undefined)?.status ?? -1);

export type UnavailableKind =
  | 'unauthenticated'
  | 'forbidden'
  | 'notFound'
  | 'blocked'
  | 'notEnabled'
  | 'unknown';

export interface Unavailable {
  kind: UnavailableKind;
  // 409 only: i18n key suffix (or the server's own message) per blocker.
  blockers: { code: string; message: string }[];
}

const NOT_ELIGIBLE = 'event_not_eligible';

function issuesOf(err: unknown): AssistantIssue[] {
  const errors = ((err as ApiError | undefined)?.details as { errors?: unknown } | undefined)
    ?.errors;
  return Array.isArray(errors) ? (errors as AssistantIssue[]) : [];
}

/** Why the assistant cannot run, from a failed assistant request. */
export function describeUnavailable(err: unknown): Unavailable {
  const status = (err as ApiError | undefined)?.status;
  const blockers = issuesOf(err)
    .filter((i) => i.code !== NOT_ELIGIBLE)
    .map((i) => ({ code: i.code, message: i.message }));
  switch (status) {
    case 401:
      return { kind: 'unauthenticated', blockers: [] };
    case 403:
      return { kind: 'forbidden', blockers: [] };
    case 404:
      return { kind: 'notFound', blockers: [] };
    case 409:
      return { kind: 'blocked', blockers };
    case 503:
      return { kind: 'notEnabled', blockers: [] };
    default:
      return { kind: 'unknown', blockers: [] };
  }
}

/**
 * Wraps an async job so that calls arriving while it runs trigger exactly one
 * more run afterwards (with the latest argument) instead of being dropped or
 * stacked. The returned promise settles when the whole chain is quiet.
 */
export function coalesce<A>(job: (arg: A) => Promise<void>): (arg: A) => Promise<void> {
  let running: Promise<void> | null = null;
  let queued: { arg: A } | null = null;

  // `running` is cleared in the same tick that finds the queue empty; a later
  // `.finally` would let a call in between join a chain that already stopped.
  async function drain(first: A): Promise<void> {
    let arg = first;
    try {
      for (;;) {
        await job(arg);
        if (!queued) return;
        arg = queued.arg;
        queued = null;
      }
    } finally {
      running = null;
      queued = null;
    }
  }

  return (arg) => {
    if (running) {
      queued = { arg };
      return running;
    }
    running = drain(arg);
    return running;
  };
}

export interface DiffLine {
  kind: string;
  name: string;
  change: 'added' | 'removed' | 'changed';
  price: string | null;
  // Field names only; values can be long or hold the spec's own wording.
  fields: string[];
}

const DIFF_CHANGES = new Set(['added', 'removed', 'changed']);

/** The review list: one line per change, naming the row and, when it has one, its price. */
export function summariseDiff(diff: DraftDiffEntry[]): DiffLine[] {
  return diff
    .filter((d) => d && DIFF_CHANGES.has(d.change))
    .map((d) => {
      const row = d.new ?? d.old ?? {};
      const name = row.name ?? (d.fields?.name?.new as unknown) ?? d.key ?? '';
      const price = d.fields?.price ? d.fields.price.new : row.price;
      return {
        kind: d.kind,
        name: String(name),
        change: d.change,
        price: price === undefined || price === null || price === '' ? null : String(price),
        fields: d.change === 'changed' ? Object.keys(d.fields ?? {}) : []
      };
    });
}

/** Where a refused socket's close code leads: a reason from `assistant.unavailable.*`. */
export function refusalReason(code: number | null): 'unauthenticated' | 'forbidden' | 'notFound' | 'blocked' | 'notEnabled' {
  switch (code) {
    case 4401:
      return 'unauthenticated';
    case 4404:
      return 'notFound';
    case 4409:
      return 'blocked';
    case 4503:
      return 'notEnabled';
    default:
      return 'forbidden';
  }
}

// Failures a second attempt can plausibly fix; the rest need a person or a
// different request (blocked, switched off, wrong key, a stop the user asked for).
const RETRYABLE = new Set(['timeout', 'model_error', 'provider_unreachable', 'rate_limited', 'busy', 'limit']);
export const isRetryable = (code: string): boolean => RETRYABLE.has(code);

export const ERROR_CODES = [
  'rate_limited', 'not_enabled', 'busy', 'notice_required', 'blocked', 'timeout', 'limit',
  'model_error', 'auth_failed', 'provider_unreachable', 'cancelled', 'bad_request'
] as const;
