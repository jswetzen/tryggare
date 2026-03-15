import { redirect } from '@sveltejs/kit';
import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ parent }) => {
  const { user } = await parent();
  if (!user?.is_staff) {
    throw redirect(302, '/');
  }
  return {};
};
