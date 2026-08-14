import { describe, it, expect } from 'vitest';
import {
  PERMISSION,
  canEditFamilyHealthInfo,
  hasPermission,
  type SessionUser
} from './permissions';

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

describe('hasPermission', () => {
  it('is true for a permission the user holds', () => {
    expect(hasPermission(user([PERMISSION.viewReports]), PERMISSION.viewReports)).toBe(true);
  });

  it('is false for one they do not', () => {
    expect(hasPermission(user(['families.view_family']), PERMISSION.viewReports)).toBe(false);
  });

  it('is false for an anonymous or unknown user', () => {
    expect(hasPermission(null, PERMISSION.viewReports)).toBe(false);
    expect(hasPermission(undefined, PERMISSION.viewReports)).toBe(false);
  });

  it('ignores is_staff entirely', () => {
    // The whole point of the increment: an admin account is not an app-tier
    // grant, and an app-tier grant is not an admin account.
    expect(hasPermission(user([], { is_staff: true }), PERMISSION.viewReports)).toBe(false);
  });

  it('ignores role names, including ones it has never heard of', () => {
    const composed = user([PERMISSION.viewReports], { roles: ['Kassör'] });
    expect(hasPermission(composed, PERMISSION.viewReports)).toBe(true);
    const namedButUngranted = user([], { roles: ['Koordinator'] });
    expect(hasPermission(namedButUngranted, PERMISSION.viewReports)).toBe(false);
  });
});

describe('canEditFamilyHealthInfo', () => {
  it('needs both child and parent change grants', () => {
    expect(
      canEditFamilyHealthInfo(user([PERMISSION.changeChild, PERMISSION.changeParent]))
    ).toBe(true);
    expect(canEditFamilyHealthInfo(user([PERMISSION.changeChild]))).toBe(false);
    expect(canEditFamilyHealthInfo(user([PERMISSION.changeParent]))).toBe(false);
  });

  it('is false for a volunteer, who reads families but changes none', () => {
    expect(
      canEditFamilyHealthInfo(
        user(['families.view_family', 'families.view_child', 'families.view_parent'])
      )
    ).toBe(false);
  });
});
