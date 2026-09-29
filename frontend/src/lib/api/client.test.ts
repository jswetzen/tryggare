import { describe, expect, it } from 'vitest';
import { extractFieldError, extractGroupError, extractRowFieldError } from './client';

// The three shapes the registration endpoint uses for parent errors (all
// HTTP 400, none carrying a `code`).
const shapeA = { parents: ['Children need an adult guardian.'] };
const shapeB = { parents: [{}, { phone: ['This field may not be blank.'] }] };
const shapeD = { parents: { '0': ['Extras can only be added for an adult with a ticket.'] } };

describe('extractGroupError (shape a)', () => {
  it('reads a flat list of strings under the group key', () => {
    expect(extractGroupError(shapeA, 'parents')).toBe('Children need an adult guardian.');
  });

  it('does not mistake the per-row shapes for a group error', () => {
    expect(extractGroupError(shapeB, 'parents')).toBeNull();
    expect(extractGroupError(shapeD, 'parents')).toBeNull();
  });

  it('is null for missing groups and non-object bodies', () => {
    expect(extractGroupError({ children: ['x'] }, 'parents')).toBeNull();
    expect(extractGroupError(null, 'parents')).toBeNull();
    expect(extractGroupError('nope', 'parents')).toBeNull();
  });
});

describe('extractRowFieldError (shape b)', () => {
  it('reads one field of one row by payload position', () => {
    expect(extractRowFieldError(shapeB, 'parents', 1, 'phone')).toBe('This field may not be blank.');
  });

  it('is null for rows that were fine, other fields, and other shapes', () => {
    expect(extractRowFieldError(shapeB, 'parents', 0, 'phone')).toBeNull();
    expect(extractRowFieldError(shapeB, 'parents', 1, 'email')).toBeNull();
    expect(extractRowFieldError(shapeB, 'parents', 5, 'phone')).toBeNull();
    expect(extractRowFieldError(shapeA, 'parents', 0, 'phone')).toBeNull();
    expect(extractRowFieldError(shapeD, 'parents', 0, 'phone')).toBeNull();
  });

  it('accepts a bare string field error too', () => {
    expect(extractRowFieldError({ parents: [{ phone: 'bad' }] }, 'parents', 0, 'phone')).toBe('bad');
  });
});

describe('extractFieldError (shape d) still works alongside the new shapes', () => {
  it('reads the index-keyed shape', () => {
    expect(extractFieldError(shapeD, 'parents', 0)).toBe(
      'Extras can only be added for an adult with a ticket.'
    );
    expect(extractFieldError(shapeD, 'parents', 1)).toBeNull();
  });

  it('does not misread shape a or b as a row error', () => {
    expect(extractFieldError(shapeA, 'parents', 0)).toBeNull();
    expect(extractFieldError(shapeB, 'parents', 1)).toBeNull();
  });
});
