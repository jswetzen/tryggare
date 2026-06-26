/**
 * Phone number validation and normalization helpers.
 *
 * Validation is intentionally lenient: we accept the formats Swedish staff
 * actually type (national `070-123 45 67`, international `+46 70 123 45 67`,
 * with spaces, dashes or parentheses) and only reject input that clearly is
 * not a phone number. The goal is to catch typos and stray text, not to
 * enforce a single canonical format.
 */

/** Strip everything except digits and a single leading `+`. */
export function normalizePhone(input: string): string {
  const trimmed = input.trim();
  const hasPlus = trimmed.startsWith('+');
  const digits = trimmed.replace(/\D/g, '');
  return hasPlus ? `+${digits}` : digits;
}

/**
 * Returns true if the (non-empty) input looks like a usable phone number.
 * Empty input is considered valid here — phone is optional; callers decide
 * whether a value is required.
 */
export function isValidPhone(input: string): boolean {
  const value = input.trim();
  if (value === '') return true;

  // Only digits, spaces, dashes, parentheses, dots and an optional leading +.
  if (!/^\+?[\d\s\-().]+$/.test(value)) return false;

  // Reasonable digit count: national numbers are ~8-10, international up to 15
  // per E.164. Require at least 6 to reject obvious junk like "12".
  const digitCount = value.replace(/\D/g, '').length;
  return digitCount >= 6 && digitCount <= 15;
}
