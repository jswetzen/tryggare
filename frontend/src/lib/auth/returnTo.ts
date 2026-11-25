/**
 * Post-login return target. Only same-origin absolute paths are honoured, so
 * `?next=` cannot be turned into an open redirect: a single leading `/`, and
 * no `//`, `/\` (browsers treat both as protocol-relative), scheme or control chars.
 */
export function safeNext(raw: string | null | undefined): string | null {
  if (!raw || raw[0] !== '/' || raw[1] === '/' || raw[1] === '\\') return null;
  // eslint-disable-next-line no-control-regex
  if (/[\u0000-\u001f\u007f\\]/.test(raw)) return null;
  try {
    const base = 'http://x.invalid';
    return new URL(raw, base).origin === base ? raw : null;
  } catch {
    return null;
  }
}

/** `/login`, carrying where to come back to when that target is safe. */
export function loginUrl(next?: string | null): string {
  const safe = safeNext(next);
  return safe ? `/login?next=${encodeURIComponent(safe)}` : '/login';
}
