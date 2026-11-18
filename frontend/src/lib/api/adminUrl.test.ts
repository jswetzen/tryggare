import { describe, it, expect } from 'vitest';
import { registrationAdminUrl } from './adminUrl';

describe('registrationAdminUrl', () => {
  it('points at the registration change page on the backend origin', () => {
    expect(registrationAdminUrl('r1')).toMatch(/\/admin\/registrations\/registration\/r1\/change\/$/);
    expect(registrationAdminUrl('r1')).not.toContain('/api/');
  });
});
