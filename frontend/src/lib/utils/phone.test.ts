import { describe, it, expect } from 'vitest';
import { isValidPhone, normalizePhone } from './phone';

describe('isValidPhone', () => {
  it('treats empty / whitespace input as valid (phone is optional)', () => {
    expect(isValidPhone('')).toBe(true);
    expect(isValidPhone('   ')).toBe(true);
  });

  it('accepts common Swedish formats', () => {
    expect(isValidPhone('070-123 45 67')).toBe(true);
    expect(isValidPhone('0701234567')).toBe(true);
    expect(isValidPhone('+46 70 123 45 67')).toBe(true);
    expect(isValidPhone('(08) 123 456')).toBe(true);
  });

  it('rejects input with letters or stray text', () => {
    expect(isValidPhone('call me')).toBe(false);
    expect(isValidPhone('070-ABC')).toBe(false);
    expect(isValidPhone('n/a')).toBe(false);
  });

  it('rejects too few or too many digits', () => {
    expect(isValidPhone('12')).toBe(false);
    expect(isValidPhone('12345')).toBe(false);
    expect(isValidPhone('1234567890123456')).toBe(false);
  });
});

describe('normalizePhone', () => {
  it('strips formatting but keeps a leading +', () => {
    expect(normalizePhone('070-123 45 67')).toBe('0701234567');
    expect(normalizePhone('+46 (70) 123 45 67')).toBe('+46701234567');
  });
});
