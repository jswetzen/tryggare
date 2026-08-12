#!/usr/bin/env python3
"""Drive a real browser against the running app, one command per invocation.

Built for the frontend-dev-cycle persona testers: an agent that knows nothing
about this codebase can explore the UI through this script alone, the way a
first-time user would. Every command talks to ONE long-lived Chrome instance,
so state (session, half-filled forms, scroll position) survives across calls.

    scripts/ux_probe.py start                      # launch the browser once
    scripts/ux_probe.py goto http://localhost:5173/register/2
    scripts/ux_probe.py read                       # what a user can see
    scripts/ux_probe.py click "Fortsätt"
    scripts/ux_probe.py fill "E-post" nisse@example.com
    scripts/ux_probe.py shot /tmp/step1.png
    scripts/ux_probe.py stop

Selectors are the words a user would point at — visible text, or a field's
label/placeholder. CSS selectors work too (prefix `css:`) but reaching for one
is usually a sign the UI lacks an accessible name, which is itself a finding.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
except ImportError:
    sys.exit(
        "selenium is not importable here. Run via the backend venv:\n"
        "  cd backend && uv run python ../scripts/ux_probe.py <command>"
    )

PORT = int(os.getenv("UX_PROBE_PORT", "9222"))
PROFILE = Path(os.getenv("UX_PROBE_PROFILE", "/tmp/ux-probe-profile"))
PIDFILE = PROFILE / "chrome.pid"
CHROME = os.getenv("UX_PROBE_CHROME", "google-chrome")

# Wide enough to see desktop layout; the `mobile` command switches to a phone.
DESKTOP = (1280, 900)
MOBILE = (390, 844)


def _connect():
    """Attach to the already-running Chrome rather than starting a new one."""
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{PORT}")
    try:
        return webdriver.Chrome(options=opts)
    except Exception as exc:
        sys.exit(f"Could not attach to Chrome on port {PORT}. Run `start` first.\n{exc}")


def cmd_start(args):
    if PIDFILE.exists():
        try:
            os.kill(int(PIDFILE.read_text()), 0)
            print(f"Already running on port {PORT}.")
            return
        except (OSError, ValueError):
            PIDFILE.unlink(missing_ok=True)

    PROFILE.mkdir(parents=True, exist_ok=True)
    headed = "--headed" in args
    argv = [
        CHROME,
        f"--remote-debugging-port={PORT}",
        f"--user-data-dir={PROFILE}",
        f"--window-size={DESKTOP[0]},{DESKTOP[1]}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-features=Translate",
    ]
    if not headed:
        argv.append("--headless=new")

    proc = subprocess.Popen(
        argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True
    )
    PIDFILE.write_text(str(proc.pid))

    for _ in range(40):
        time.sleep(0.25)
        try:
            _connect().quit()
            break
        except SystemExit:
            continue
    print(f"Chrome up on port {PORT} ({'headed' if headed else 'headless'}).")


def cmd_stop(args):
    if PIDFILE.exists():
        try:
            os.kill(int(PIDFILE.read_text()), 15)
        except (OSError, ValueError):
            pass
        PIDFILE.unlink(missing_ok=True)
    print("Stopped.")


def cmd_goto(args):
    d = _connect()
    d.get(args[0])
    time.sleep(1.0)  # SvelteKit client-side nav + fetch
    print(f"{d.title} — {d.current_url}")


def _find(d, selector):
    """Locate an element the way a user identifies it: by what they can see."""
    if selector.startswith("css:"):
        return d.find_element(By.CSS_SELECTOR, selector[4:])

    esc = selector.replace('"', '\\"')
    strategies = [
        # visible text on a clickable thing
        (
            By.XPATH,
            f'//button[contains(normalize-space(.), "{esc}")]'
            f' | //a[contains(normalize-space(.), "{esc}")]'
            f' | //*[@role="button"][contains(normalize-space(.), "{esc}")]'
            f' | //summary[contains(normalize-space(.), "{esc}")]',
        ),
        # a field named by its label
        (
            By.XPATH,
            f'//label[contains(normalize-space(.), "{esc}")]//input'
            f' | //label[contains(normalize-space(.), "{esc}")]//select'
            f' | //label[contains(normalize-space(.), "{esc}")]//textarea',
        ),
        # a field named by placeholder / aria-label / name
        (
            By.XPATH,
            f'//input[contains(@placeholder, "{esc}")]'
            f' | //textarea[contains(@placeholder, "{esc}")]'
            f' | //*[contains(@aria-label, "{esc}")]'
            f' | //input[@name="{esc}"] | //select[@name="{esc}"]',
        ),
        # label pointing at a field by id
        (By.XPATH, f'//label[contains(normalize-space(.), "{esc}")]'),
        # anything else carrying the text
        (By.XPATH, f'//*[contains(normalize-space(text()), "{esc}")]'),
    ]
    for how, what in strategies:
        for el in d.find_elements(how, what):
            if el.is_displayed():
                if how == By.XPATH and el.tag_name == "label":
                    target = el.get_attribute("for")
                    if target:
                        found = d.find_elements(By.ID, target)
                        if found:
                            return found[0]
                return el
    raise SystemExit(
        f'Nothing visible matches "{selector}".\n'
        "If a real user could see it but this cannot find it, that is a finding: "
        "the control likely has no accessible name. Run `read` to see what IS exposed."
    )


def cmd_click(args):
    d = _connect()
    el = _find(d, args[0])
    d.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    time.sleep(0.2)
    try:
        el.click()
    except Exception:
        d.execute_script("arguments[0].click();", el)
    time.sleep(0.8)
    print(f"Clicked {args[0]!r} — now at {d.current_url}")


def cmd_fill(args):
    d = _connect()
    el = _find(d, args[0])
    value = args[1] if len(args) > 1 else ""
    d.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    if el.tag_name == "select":
        from selenium.webdriver.support.ui import Select

        Select(el).select_by_visible_text(value)
    else:
        el.clear()
        el.send_keys(value)
        # Svelte binds on input events; send_keys fires them, but blur commits.
        el.send_keys(Keys.TAB)
    time.sleep(0.4)
    print(f"Filled {args[0]!r} with {value!r}")


def cmd_read(args):
    """Print what a user can actually see, not the DOM."""
    d = _connect()
    payload = d.execute_script("""
        const vis = el => {
            const s = getComputedStyle(el);
            if (s.display === 'none' || s.visibility === 'hidden' || s.opacity === '0')
                return false;
            const r = el.getBoundingClientRect();
            return r.width > 0 && r.height > 0;
        };
        const out = {headings: [], text: [], fields: [], actions: [], errors: []};
        for (const el of document.querySelectorAll('h1,h2,h3,h4,legend')) {
            if (vis(el)) out.headings.push(el.tagName + ': ' + el.innerText.trim());
        }
        for (const el of document.querySelectorAll('input,select,textarea')) {
            if (!vis(el)) continue;
            let name = el.labels && el.labels.length ? el.labels[0].innerText.trim() : '';
            name = name || el.getAttribute('aria-label') || el.placeholder || el.name || '(unnamed)';
            out.fields.push({
                label: name, type: el.type || el.tagName.toLowerCase(),
                value: el.type === 'checkbox' || el.type === 'radio'
                    ? (el.checked ? 'checked' : 'unchecked') : el.value,
                required: el.required, disabled: el.disabled,
            });
        }
        for (const el of document.querySelectorAll('button,a,[role=button]')) {
            if (!vis(el)) continue;
            const t = el.innerText.trim() || el.getAttribute('aria-label') || '';
            if (t) out.actions.push({label: t, disabled: !!el.disabled});
        }
        for (const el of document.querySelectorAll('[role=alert],.error,[class*=error],[class*=danger]')) {
            if (vis(el) && el.innerText.trim()) out.errors.push(el.innerText.trim());
        }
        out.text = document.body.innerText.split('\\n')
            .map(s => s.trim()).filter(Boolean).slice(0, 120);
        return out;
    """)
    print(f"URL: {d.current_url}\nTITLE: {d.title}\n")
    for key in ("headings", "fields", "actions", "errors"):
        if payload[key]:
            print(f"--- {key.upper()} ---")
            for item in payload[key]:
                print(f"  {json.dumps(item, ensure_ascii=False) if isinstance(item, dict) else item}")
            print()
    print("--- VISIBLE TEXT ---")
    for line in payload["text"]:
        print(f"  {line}")


def cmd_shot(args):
    d = _connect()
    path = args[0] if args else "/tmp/ux-probe.png"
    d.save_screenshot(path)
    print(f"Saved {path}")


def cmd_mobile(args):
    d = _connect()
    d.set_window_size(*MOBILE)
    time.sleep(0.5)
    print(f"Viewport now {MOBILE[0]}x{MOBILE[1]} (phone).")


def cmd_desktop(args):
    d = _connect()
    d.set_window_size(*DESKTOP)
    time.sleep(0.5)
    print(f"Viewport now {DESKTOP[0]}x{DESKTOP[1]}.")


def cmd_back(args):
    d = _connect()
    d.back()
    time.sleep(0.8)
    print(f"Back — now at {d.current_url}")


def cmd_console(args):
    """Browser console errors — a user never sees these, but they explain breakage."""
    d = _connect()
    try:
        logs = d.get_log("browser")
    except Exception:
        print("Console log unavailable on this connection.")
        return
    for entry in logs[-40:]:
        print(f"{entry['level']}: {entry['message'][:400]}")


COMMANDS = {
    "start": cmd_start, "stop": cmd_stop, "goto": cmd_goto, "click": cmd_click,
    "fill": cmd_fill, "read": cmd_read, "shot": cmd_shot, "mobile": cmd_mobile,
    "desktop": cmd_desktop, "back": cmd_back, "console": cmd_console,
}


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        print(f"Commands: {', '.join(COMMANDS)}")
        sys.exit(1)
    COMMANDS[sys.argv[1]](sys.argv[2:])
