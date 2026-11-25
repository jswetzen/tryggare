/**
 * Edit form for a feature request card: limits, checks and the payload Confirm
 * sends. Limits match the server (docs/roadmap/feature_requests.md, "The record");
 * the server checks again and its 400 is shown next to the card.
 */
import type { AssistantIssue, FeatureRequestCard, FeatureRequestEdits, WorkaroundCost } from './types';

export const FEATURE_LIMITS = {
  title: 100,
  problem: 600,
  desired: 600,
  tried: 300,
  triedItems: 5,
  used: 400
} as const;

export const COSTS: readonly WorkaroundCost[] = ['none', 'extra_steps', 'wrong_result', 'not_possible'];

export interface FeatureForm {
  title: string;
  problem: string;
  desired: string;
  tried: string[];
  used: string;
  cost: WorkaroundCost;
}

export type FeatureField = 'title' | 'problem' | 'desired' | 'used' | `tried.${number}`;

export interface FieldProblem {
  field: FeatureField;
  code: 'required' | 'tooLong';
  max?: number;
}

// Counted in code points, as the server counts (Python len), not UTF-16 units.
const length = (s: string): number => Array.from(s).length;

export function formFrom(card: FeatureRequestCard): FeatureForm {
  return {
    title: card.title,
    problem: card.problem,
    desired: card.desired,
    tried: [...(card.tried ?? [])],
    used: card.workaround?.used ?? '',
    cost: card.workaround?.cost ?? 'none'
  };
}

/** The first problem of each field, in form order. Empty when the form can be sent. */
export function checkForm(form: FeatureForm, hasWorkaround: boolean): FieldProblem[] {
  const problems: FieldProblem[] = [];
  const text = (field: 'title' | 'problem' | 'desired', value: string) => {
    if (value.trim() === '') problems.push({ field, code: 'required' });
    else if (length(value.trim()) > FEATURE_LIMITS[field]) {
      problems.push({ field, code: 'tooLong', max: FEATURE_LIMITS[field] });
    }
  };
  text('title', form.title);
  text('problem', form.problem);
  text('desired', form.desired);
  form.tried.forEach((item, i) => {
    if (item.trim() === '') problems.push({ field: `tried.${i}`, code: 'required' });
    else if (length(item.trim()) > FEATURE_LIMITS.tried) {
      problems.push({ field: `tried.${i}`, code: 'tooLong', max: FEATURE_LIMITS.tried });
    }
  });
  if (hasWorkaround) {
    if (form.used.trim() === '') problems.push({ field: 'used', code: 'required' });
    else if (length(form.used.trim()) > FEATURE_LIMITS.used) {
      problems.push({ field: 'used', code: 'tooLong', max: FEATURE_LIMITS.used });
    }
  }
  return problems;
}

/** The fields Confirm sends after an edit: trimmed, and the workaround only when the card has one. */
export function editsFrom(form: FeatureForm, hasWorkaround: boolean): FeatureRequestEdits {
  const edits: FeatureRequestEdits = {
    title: form.title.trim(),
    problem: form.problem.trim(),
    desired: form.desired.trim(),
    tried: form.tried.map((item) => item.trim())
  };
  if (hasWorkaround) edits.workaround = { used: form.used.trim(), cost: form.cost };
  return edits;
}

/** Which form field a server error path points at, or null when it names none. */
export function fieldOfPath(path: string): 'title' | 'problem' | 'desired' | 'tried' | 'used' | null {
  if (path === 'title' || path === 'problem' || path === 'desired') return path;
  if (path === 'workaround' || path.startsWith('workaround.')) return 'used';
  if (path === 'tried' || path.startsWith('tried')) return 'tried';
  return null;
}

export const fieldIdOf = (prefix: string, field: FeatureField | 'cost'): string =>
  `${prefix}-${field.replace('.', '-')}`;

export const issueList = (issues: unknown): AssistantIssue[] =>
  Array.isArray(issues) ? (issues as AssistantIssue[]) : [];
