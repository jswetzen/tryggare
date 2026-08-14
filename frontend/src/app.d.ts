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
  }
}

export {};
