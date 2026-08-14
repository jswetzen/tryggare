import { redirect } from '@sveltejs/kit';
import type { LayoutLoad } from './$types';
import { PERMISSION, hasPermission } from '$lib/auth/permissions';

/**
 * Was `!user?.is_staff`, which conflated "may configure imports" with "has a
 * Django-admin account". `imports.view_importsource` is what the import API
 * itself now checks (imports/views.py), so a Koordinator — who holds every
 * `imports.*` grant and no admin account — reaches a screen that actually
 * works rather than one whose every request 403s.
 *
 * See routes/reports/+layout.ts for why the denial is a redirect carrying
 * `?denied=…` rather than an error page.
 */
export const load: LayoutLoad = async ({ parent }) => {
  const { user } = await parent();
  if (!hasPermission(user, PERMISSION.viewImportSources)) {
    throw redirect(302, '/?denied=import');
  }
  return {};
};
