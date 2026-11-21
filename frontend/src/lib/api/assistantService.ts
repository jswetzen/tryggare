import { get } from 'svelte/store';
import { locale } from 'svelte-i18n';
import { apiClient } from './client';
import type {
  AssistantPreview,
  ConversationState,
  DraftPayload
} from '$lib/assistant/types';

/**
 * Event assistant endpoints (staff only; every call is re-checked server-side).
 * Refusals are `{errors: [{path, code, message}], warnings: []}` on the
 * thrown ApiError's `details`.
 */
const base = (eventId: string) => `/assistant/events/${eventId}`;

// The client sends no Accept-Language, so the draft's warning texts follow the UI language.
const lang = () => `?lang=${get(locale) === 'sv' ? 'sv' : 'en'}`;

export const assistantApi = {
  getConversation: (eventId: string): Promise<ConversationState> =>
    apiClient.get(`${base(eventId)}/conversation/`),

  clearConversation: (eventId: string): Promise<unknown> =>
    apiClient.delete(`${base(eventId)}/conversation/`),

  acceptNotice: (eventId: string): Promise<{ notice_accepted: true }> =>
    apiClient.post(`${base(eventId)}/conversation/notice/`),

  getDraft: (eventId: string): Promise<DraftPayload> => apiClient.get(`${base(eventId)}/draft/${lang()}`),

  // `version` is required by the server: a discard names the draft it saw.
  discardDraft: (eventId: string, version: number, token?: string): Promise<unknown> =>
    apiClient.delete(
      `${base(eventId)}/draft/?version=${version}${token ? `&token=${encodeURIComponent(token)}` : ''}`
    ),

  // Apply is the existing spec endpoint (same guards, last write wins); the
  // caller discards the draft afterwards.
  applySpec: (eventId: string, spec: unknown): Promise<unknown> =>
    apiClient.put(`/events/${eventId}/spec/`, spec),

  getPreview: (eventId: string): Promise<AssistantPreview> =>
    apiClient.get(`${base(eventId)}/preview/${lang()}`)
};
