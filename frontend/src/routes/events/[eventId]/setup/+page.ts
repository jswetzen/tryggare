import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import { loginUrl } from '$lib/auth/returnTo';
import { assistantApi } from '$lib/api/assistantService';
import { describeUnavailable, setupRedirectUrl } from '$lib/assistant/helpers';

/**
 * The URL people use for the assistant. It owns eligibility, then hands over
 * to the register page, which re-verifies on its own (this is convenience,
 * never the gate). A signed-out visitor goes to /login?next=, which returns here.
 */
export const load: PageLoad = async ({ params, url }) => {
  try {
    await assistantApi.getConversation(params.eventId);
  } catch (err) {
    const unavailable = describeUnavailable(err);
    if (unavailable.kind === 'unauthenticated') throw redirect(302, loginUrl(url.pathname));
    return { unavailable };
  }
  throw redirect(302, setupRedirectUrl(params.eventId));
};
