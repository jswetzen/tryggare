import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  kit: {
    adapter: adapter({
      pages: 'build',
      assets: 'build',
      fallback: 'index.html',  // SPA fallback
      precompress: false,
      strict: false  // Allow non-prerendered pages (required for SPA mode)
    }),
    alias: {
      $lib: 'src/lib'
    },
    prerender: {
      handleHttpError: 'warn',  // Don't fail on 404s during prerender (like missing favicon)
      handleMissingId: 'warn',
      entries: ['/__fallback']  // Only prerender the fallback page
    }
  },
  preprocess: vitePreprocess(),
  compilerOptions: {}
};

export default config;
