import { apiClient } from './client';
import type {
  RegistrationEventInfo,
  RegistrationSubmitPayload,
  RegistrationSubmitResponse,
  RegistrationVerifyResponse,
} from './types';

/**
 * Public self-serve registration API endpoints (all unauthenticated).
 */
export const registrationApi = {
  getEvent: (eventId: string): Promise<RegistrationEventInfo> =>
    apiClient.get(`/registrations/events/${eventId}/`),

  submit: (data: RegistrationSubmitPayload): Promise<RegistrationSubmitResponse> =>
    apiClient.post('/registrations/', data),

  verify: (token: string): Promise<RegistrationVerifyResponse> =>
    apiClient.get(`/registrations/verify/${encodeURIComponent(token)}/`),
};
