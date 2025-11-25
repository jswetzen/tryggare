import { h as head, e as ensure_array_like } from "../../chunks/index2.js";
import { V as escape_html } from "../../chunks/context.js";
function _page($$renderer) {
  const checklist = [
    "Django backend served by Daphne",
    "PostgreSQL + Valkey services via Docker Compose",
    "SvelteKit + Tailwind starter with i18n-ready plumbing",
    "REST + realtime hooks planned for check-in/out flows"
  ];
  head("1uha8ag", $$renderer, ($$renderer2) => {
    $$renderer2.title(($$renderer3) => {
      $$renderer3.push(`<title>Check-ins Migration Preview</title>`);
    });
    $$renderer2.push(`<meta name="description" content="Django + SvelteKit reboot placeholder"/>`);
  });
  $$renderer.push(`<main><div class="card"><div class="badge">Django + SvelteKit Migration</div> <h1>Welcome to the refreshed frontend</h1> <p>This SvelteKit shell is ready to connect to the new Django REST + Channels backend. Configure your
      environment variables and start iterating on check-in, ticketing, and QR flows.</p> <ul><!--[-->`);
  const each_array = ensure_array_like(checklist);
  for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
    let item = each_array[$$index];
    $$renderer.push(`<li>• ${escape_html(item)}</li>`);
  }
  $$renderer.push(`<!--]--></ul></div></main>`);
}
export {
  _page as default
};
