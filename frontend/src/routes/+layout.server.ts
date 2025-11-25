/**
 * Root layout server load function
 * Passes user data from server hook to all pages
 */

export const load = async ({ locals }: { locals: App.Locals }) => {
  return {
    user: locals.user,
  };
};
