// Which session the desk is working in, remembered across reloads.
//
// /checkin and /checkout both used to open on sessions[0] every time, so a volunteer who ran
// session B had to re-pick it after every reload (and after every session_started /
// session_ended push, which re-runs the session load). The choice is remembered per browser in
// localStorage, under one key shared by both pages: a desk that checks children in for session B
// checks them out of session B.
//
// localStorage is a convenience, never a requirement: it throws in private windows, with blocked
// site data and in some embedded views, and the saved id can name a session that has since ended.
// Every access is wrapped, and anything unusable falls back to sessions[0].

const STORAGE_KEY = 'tryggare.selectedSessionId';

export function readSavedSessionId(): string | null {
  try {
    const id = localStorage.getItem(STORAGE_KEY);
    return typeof id === 'string' && id ? id : null;
  } catch {
    return null;
  }
}

export function saveSessionId(id: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, id);
  } catch {
    // Not remembering is fine; the page still works with the in-memory choice.
  }
}

/** The remembered session if it is still active, else the first one (null for an empty list). */
export function pickSession<T extends { id: string }>(sessions: T[]): T | null {
  if (sessions.length === 0) return null;
  const saved = readSavedSessionId();
  return (saved && sessions.find((s) => s.id === saved)) || sessions[0];
}
