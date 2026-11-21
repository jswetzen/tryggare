import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import { assistantApi } from '$lib/api/assistantService';
import { describeUnavailable, setupRedirectUrl } from '$lib/assistant/helpers';

/**
 * The URL people use for the assistant. It owns eligibility, then hands over
 * to the register page, which re-verifies on its own (this is convenience,
 * never the gate). Login does not return here yet: /login always lands on
 * /checkin, so a signed-out visitor opens the link again afterwards.
 */
export const load: PageLoad = async ({ params }) => {
  try {
    await assistantApi.getConversation(params.eventId);
  } catch (err) {
    const unavailable = describeUnavailable(err);
    if (unavailable.kind === 'unauthenticated') throw redirect(302, '/login');
    return { unavailable };
  }
  throw redirect(302, setupRedirectUrl(params.eventId));
};
