import { e as escape_html } from "../../chunks/escaping.js";
import "clsx";
function _layout($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { data, children } = $$props;
    if (data.user) {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<nav class="bg-gray-800 text-white p-4"><div class="container mx-auto flex justify-between items-center"><div><a href="/" class="text-xl font-bold">Check-In System</a></div> <div class="flex items-center gap-4"><span>Welcome, ${escape_html(data.user.username)}</span> <a href="/checkin" class="hover:text-gray-300">Check-In</a> <a href="/checkout" class="hover:text-gray-300">Check-Out</a> <a href="/logout" class="hover:text-gray-300">Logout</a></div></div></nav>`);
    } else {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> <main class="container mx-auto p-4">`);
    children($$renderer2);
    $$renderer2.push(`<!----></main>`);
  });
}
export {
  _layout as default
};
