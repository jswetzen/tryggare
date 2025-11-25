/**
 * Root layout server load function
 * Passes user data from server hook to all pages
 */

export const load = async ({ locals }: { locals: App.Locals }) => {
  console.log('Layout server load, locals.user:', locals.user);

  return {
    user: locals.user,
  };
};
