import { c as create_ssr_component, e as each } from "../../chunks/ssr.js";
import { e as escape } from "../../chunks/escape.js";
const Page = create_ssr_component(($$result, $$props, $$bindings, slots) => {
  const checklist = [
    "Django backend served by Daphne",
    "PostgreSQL + Valkey services via Docker Compose",
    "SvelteKit + Tailwind starter with i18n-ready plumbing",
    "REST + realtime hooks planned for check-in/out flows"
  ];
  return `${$$result.head += `<!-- HEAD_svelte-1ltfx37_START -->${$$result.title = `<title>Check-ins Migration Preview</title>`, ""}<meta name="description" content="Django + SvelteKit reboot placeholder"><!-- HEAD_svelte-1ltfx37_END -->`, ""} <main><div class="card"><div class="badge" data-svelte-h="svelte-nuyn7t">Django + SvelteKit Migration</div> <h1 data-svelte-h="svelte-rtcn32">Welcome to the refreshed frontend</h1> <p data-svelte-h="svelte-1mtg93a">This SvelteKit shell is ready to connect to the new Django REST + Channels backend. Configure your
      environment variables and start iterating on check-in, ticketing, and QR flows.</p> <ul>${each(checklist, (item) => {
    return `<li>• ${escape(item)}</li>`;
  })}</ul></div></main>`;
});
export {
  Page as default
};
