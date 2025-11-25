/// <reference types="@sveltejs/kit" />

// See https://kit.svelte.dev/docs/types#app
// for information about these interfaces
declare global {
  namespace App {
    interface Locals {
      user: {
        id: string;
        username: string;
        name: string;
      } | null;
    }
  }
}

export {};
