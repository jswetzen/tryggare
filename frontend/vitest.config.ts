import { defineConfig } from 'vitest/config';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import path from 'path';

// Separate Vitest config that doesn't use SvelteKit plugin
// This allows tests to run without SvelteKit's SSR configuration
export default defineConfig({
  plugins: [
    svelte({
      hot: false
    })
  ],
  resolve: {
    alias: {
      $lib: path.resolve('./src/lib'),
      $app: path.resolve('./src/__mocks__/$app')
    },
    conditions: ['browser']
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/setupTests.ts'],
    include: ['src/**/*.{test,spec}.{js,ts}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      exclude: ['node_modules/', 'src/setupTests.ts', 'src/__mocks__/**']
    }
  }
});
