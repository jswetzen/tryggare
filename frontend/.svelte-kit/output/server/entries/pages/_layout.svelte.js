import "clsx";
import { r as registerLocaleLoader, i as init, g as getLocaleFromNavigator } from "../../chunks/runtime.js";
import { s as store_get, a as attr_class, b as attr, u as unsubscribe_stores, c as stringify } from "../../chunks/index2.js";
import { p as page } from "../../chunks/stores.js";
import { V as escape_html } from "../../chunks/context.js";
import { g as goto } from "../../chunks/client.js";
registerLocaleLoader("en", () => import("../../chunks/en.js"));
registerLocaleLoader("sv", () => import("../../chunks/sv.js"));
init({
  fallbackLocale: "en",
  initialLocale: getLocaleFromNavigator()
});
function SessionIndicator($$renderer, $$props) {
  let { eventName, sessionName, sessionTime, onChangeSession } = $$props;
  $$renderer.push(`<div class="bg-slate-50 border border-slate-300 rounded px-3 py-2 mb-4 flex flex-wrap justify-between items-center gap-2 text-sm"><div class="text-slate-600"><span class="font-semibold text-blue-900">Event:</span> ${escape_html(eventName)} • <span class="font-semibold text-blue-900 ml-1">Session:</span> ${escape_html(sessionName)} (${escape_html(sessionTime)})</div> `);
  if (onChangeSession) {
    $$renderer.push("<!--[-->");
    $$renderer.push(`<button class="text-blue-600 font-semibold hover:underline">Change Session</button>`);
  } else {
    $$renderer.push("<!--[!-->");
  }
  $$renderer.push(`<!--]--></div>`);
}
function TopNav($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    let {
      userName = "User",
      currentEvent,
      currentSession,
      sessionTime,
      onLogout,
      onChangeSession
    } = $$props;
    let mobileMenuOpen = false;
    let currentPath = store_get($$store_subs ??= {}, "$page", page).url.pathname;
    function isActive(path) {
      return currentPath === path;
    }
    $$renderer2.push(`<nav class="bg-white border-b-2 border-slate-300 shadow-sm"><div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8"><div class="flex justify-between items-center h-16"><div class="flex items-center"><h1 class="text-xl font-bold text-blue-900">Check-In System</h1></div> <div class="hidden md:flex items-center space-x-6"><a href="/checkin"${attr_class(`px-4 py-2 rounded-md font-semibold transition-colors ${stringify(isActive("/checkin") ? "bg-blue-600 text-white" : "text-slate-700 hover:bg-slate-100")}`)}>Check-In</a> <a href="/checkout"${attr_class(`px-4 py-2 rounded-md font-semibold transition-colors ${stringify(isActive("/checkout") ? "bg-blue-600 text-white" : "text-slate-700 hover:bg-slate-100")}`)}>Check-Out</a> <div class="border-l border-slate-300 pl-6 ml-2 flex items-center space-x-4"><span class="text-sm text-slate-600">Welcome, <span class="font-semibold text-blue-900">${escape_html(userName)}</span></span> `);
    if (onLogout) {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<button class="text-sm text-red-600 font-semibold hover:underline">Logout</button>`);
    } else {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--></div></div> <div class="md:hidden"><button class="inline-flex items-center justify-center p-2 rounded-md text-slate-700 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500"${attr("aria-expanded", mobileMenuOpen)}><span class="sr-only">Open main menu</span> `);
    {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>`);
    }
    $$renderer2.push(`<!--]--></button></div></div> `);
    if (currentEvent && currentSession && sessionTime) {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<div class="py-2">`);
      SessionIndicator($$renderer2, {
        eventName: currentEvent,
        sessionName: currentSession,
        sessionTime,
        onChangeSession
      });
      $$renderer2.push(`<!----></div>`);
    } else {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--></div> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--></nav>`);
    if ($$store_subs) unsubscribe_stores($$store_subs);
  });
}
function _layout($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { data, children } = $$props;
    async function handleLogout() {
      await fetch("/logout", { method: "POST" });
      goto();
    }
    if (data.user) {
      $$renderer2.push("<!--[-->");
      TopNav($$renderer2, { userName: data.user.username, onLogout: handleLogout });
    } else {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> <main class="min-h-screen bg-slate-100 p-5">`);
    children($$renderer2);
    $$renderer2.push(`<!----></main>`);
  });
}
export {
  _layout as default
};
