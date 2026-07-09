import { apiClient } from './client';
import type {
  PromoCodeValidation,
  RegistrationEventInfo,
  RegistrationPaymentStatusResponse,
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

  // Read-only preview — never locks/reserves the code, just tells the form
  // whether it's currently usable, what it discounts, and which is_hidden
  // ticket types it unlocks. The real, authoritative redemption happens
  // again from scratch inside submit().
  validatePromoCode: (eventId: string, code: string): Promise<PromoCodeValidation> =>
    apiClient.post('/registrations/validate-promo-code/', { event: eventId, code }),

  verify: (token: string): Promise<RegistrationVerifyResponse> =>
    apiClient.get(`/registrations/verify/${encodeURIComponent(token)}/`),

  // Recovery path for a guardian who navigated away from the verify response
  // before paying — verify_registration's token is single-use, so this is
  // the only way back in.
  checkPaymentStatus: (
    referenceCode: string,
    contactEmail: string
  ): Promise<RegistrationPaymentStatusResponse> =>
    apiClient.post('/registrations/payment-status/', {
      reference_code: referenceCode,
      contact_email: contactEmail,
    }),
};
