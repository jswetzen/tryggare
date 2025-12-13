import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [sveltekit()],
  server: {
    port: 5173
  },
  build: {
    sourcemap: false  // Disable source maps in production builds
  }
});
