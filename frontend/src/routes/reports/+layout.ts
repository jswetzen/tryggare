import { redirect } from '@sveltejs/kit';
import type { LayoutLoad } from './$types';
import { PERMISSION, hasPermission } from '$lib/auth/permissions';

/**
 * /reports had no guard at all: any authenticated user who typed the URL got
 * the whole event's financial and attendance picture. The nav link was hidden
 * from non-staff, which is not the same thing as the route being closed.
 *
 * `reports.view_eventreport` is the string the backend's own report endpoints
 * check (see config/permissions.py), so this guard and the API agree by
 * construction — including when an operator moves the permission onto a group
 * this frontend has never heard of.
 *
 * Unauthorised users are redirected home with `?denied=reports` rather than
 * shown a 403 page. Two reasons: an error page invites "what am I missing?",
 * while landing on the screens you *can* use answers it; and this is the shape
 * /import already had, so the app has one behaviour for "not for you" instead
 * of two. The query param is what turns the previously silent bounce into an
 * explanation — see routes/+page.svelte.
 *
 * This is a layout, not a page, guard so a future /reports/<id> is covered the
 * day it is added rather than the day someone remembers.
 */
export const load: LayoutLoad = async ({ parent }) => {
  const { user } = await parent();
  if (!hasPermission(user, PERMISSION.viewReports)) {
    throw redirect(302, '/?denied=reports');
  }
  return {};
};
