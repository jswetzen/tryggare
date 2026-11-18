/// <reference types="@sveltejs/kit" />

// See https://kit.svelte.dev/docs/types#app
// for information about these interfaces
import type { SessionUser } from '$lib/auth/permissions';

declare global {
  namespace App {
    interface Locals {
      // Shape from GET /api/auth/check/ — see $lib/auth/permissions for why
      // is_staff no longer decides anything but the Django-admin link.
      user: SessionUser | null;
    }
    interface PageState {
      // Set via pushState on a successful guest-registration submit (see
      // register/[eventId]/+page.svelte::submitPayload) so the confirmation
      // screen is its own history entry — Back returns to the still-filled
      // form instead of skipping past the whole page to whatever was behind
      // it (registration dev-cycle round 4, increment 8, 2026-09-29).
      registrationSubmitted?: boolean;
    }
  }
}

export {};
