// This page is only used during build to generate the SPA fallback HTML
// It doesn't need auth and should always render successfully
export const prerender = true;

export const load = async () => {
  return {};
};
