/**
 * /reports had no guard at all before this increment — any authenticated user
 * who typed the URL got the event's whole financial picture. These are the
 * tests that would have caught that.
 *
 * Named guard.test.ts, not +layout.test.ts: SvelteKit reserves `+`-prefixed
 * filenames project-wide and a colocated one breaks `npm run check` across
 * unrelated files.
 */
import { describe, it, expect } from 'vitest';
import { load as loadReports } from './+layout';
import { load as loadImport } from '../import/+layout';
import { PERMISSION, type SessionUser } from '$lib/auth/permissions';

function user(permissions: string[], overrides: Partial<SessionUser> = {}): SessionUser {
  return {
    id: 'u1',
    username: 'u1',
    name: 'U One',
    is_staff: false,
    is_superuser: false,
    roles: [],
    permissions,
    ...overrides
  };
}

/** The guards read only `user`; the rest of LayoutLoad's event is unused. */
function event(u: SessionUser | null) {
  return { parent: async () => ({ user: u }) } as never;
}

/**
 * Both guards read the same one field and differ only in their generated
 * route-id types, so one caller serves both.
 */
type Guard = (event: never) => unknown;

async function redirectFrom(load: Guard, u: SessionUser | null) {
  try {
    await load(event(u));
    return null;
  } catch (thrown) {
    return thrown as { status: number; location: string };
  }
}

describe('/reports guard', () => {
  it('lets a holder of reports.view_eventreport through', async () => {
    expect(await redirectFrom(loadReports, user([PERMISSION.viewReports]))).toBeNull();
  });

  it('redirects a volunteer home, saying which screen was refused', async () => {
    const redirect = await redirectFrom(loadReports, user(['families.view_family']));
    expect(redirect?.status).toBe(302);
    expect(redirect?.location).toBe('/?denied=reports');
  });

  it('redirects an anonymous caller rather than rendering the page', async () => {
    expect((await redirectFrom(loadReports, null))?.status).toBe(302);
  });

  it('does not let is_staff alone through', async () => {
    // is_staff means "can open Django admin" and nothing else. A staff account
    // without the report grant has no business on this screen.
    const redirect = await redirectFrom(loadReports, user([], { is_staff: true }));
    expect(redirect?.location).toBe('/?denied=reports');
  });

  it('honours a permission granted through a group this frontend never heard of', async () => {
    const composed = user([PERMISSION.viewReports], { roles: ['Kassör'] });
    expect(await redirectFrom(loadReports, composed)).toBeNull();
  });
});

describe('/import guard', () => {
  it('lets a coordinator through on imports.view_importsource, without is_staff', async () => {
    const coordinator = user([PERMISSION.viewImportSources], { roles: ['Koordinator'] });
    expect(await redirectFrom(loadImport, coordinator)).toBeNull();
  });

  it('redirects a volunteer home', async () => {
    const redirect = await redirectFrom(loadImport, user(['families.view_family']));
    expect(redirect?.location).toBe('/?denied=import');
  });

  it('no longer lets a bare is_staff account through', async () => {
    const redirect = await redirectFrom(loadImport, user([], { is_staff: true }));
    expect(redirect?.location).toBe('/?denied=import');
  });
});
