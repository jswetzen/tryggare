import { describe, it, expect } from 'vitest';
import { safeNext, loginUrl } from './returnTo';

describe('safeNext', () => {
  it.each(['/events/e1/setup', '/checkin?x=1#y', '/'])('accepts %s', (p) => {
    expect(safeNext(p)).toBe(p);
  });

  it.each([
    null,
    undefined,
    '',
    'events/e1',
    '//evil.example',
    '/\\evil.example',
    'https://evil.example',
    'javascript:alert(1)',
    '/a\\b',
    '/a\nb',
    ' /x'
  ])('rejects %s', (p) => {
    expect(safeNext(p as string | null)).toBeNull();
  });
});

describe('loginUrl', () => {
  it('encodes a safe next', () => {
    expect(loginUrl('/events/e1/setup')).toBe('/login?next=%2Fevents%2Fe1%2Fsetup');
  });
  it('is plain /login otherwise', () => {
    expect(loginUrl()).toBe('/login');
    expect(loginUrl('//evil')).toBe('/login');
  });
});
