#!/usr/bin/env node
/**
 * Design-token drift guard.
 *
 * The brand token layer has two app-side representations:
 *   - src/lib/styles/tokens.css  (canonical :root custom properties)
 *   - tailwind.config.cjs         (mirrored values so utilities resolve to brand)
 *
 * Every mirrored value in tailwind.config.cjs is annotated with a trailing
 * `// --token-name` comment naming the tokens.css variable it must equal. This
 * script reads both files as text (no require → runs without node_modules) and
 * fails if any annotated Tailwind value drifts from its tokens.css source.
 *
 * Run: node scripts/check-design-tokens.mjs   (npm run check:tokens)
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const tokensPath = resolve(here, '../src/lib/styles/tokens.css');
const configPath = resolve(here, '../tailwind.config.cjs');

const tokensSrc = readFileSync(tokensPath, 'utf8');
const configSrc = readFileSync(configPath, 'utf8');

// Tailwind writes `oklch(... / <alpha-value>)` so opacity modifiers work; the
// canonical token omits the alpha. Normalise that away, plus whitespace, before
// comparing. The `/ 0.30` inside a shadow is left intact (not an <alpha-value>).
const norm = (s) =>
  s
    .replace(/\s*\/\s*<alpha-value>/g, '')
    .replace(/\s+/g, ' ')
    .trim();

// Build map of --token -> value from tokens.css ([^;] also spans newlines, so
// multi-line shadows are captured whole).
const tokens = new Map();
for (const m of tokensSrc.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) {
  tokens.set(m[1], norm(m[2]));
}

// Find every `key: 'value', // --token` line in the Tailwind config.
const checks = [];
for (const m of configSrc.matchAll(/'([^']*)'\s*,?\s*\/\/\s*(--[\w-]+)/g)) {
  checks.push({ value: norm(m[1]), token: m[2] });
}

if (checks.length === 0) {
  console.error('check-design-tokens: found no `// --token` annotations in tailwind.config.cjs — guard would be a no-op.');
  process.exit(1);
}

const failures = [];
for (const { value, token } of checks) {
  if (!tokens.has(token)) {
    failures.push(`  ${token}: referenced in tailwind.config.cjs but not defined in tokens.css`);
    continue;
  }
  const expected = tokens.get(token);
  if (value !== expected) {
    failures.push(`  ${token}:\n      tokens.css      = ${expected}\n      tailwind.config = ${value}`);
  }
}

if (failures.length > 0) {
  console.error(`✗ Design tokens out of sync between tokens.css and tailwind.config.cjs:\n${failures.join('\n')}`);
  console.error('\nFix: make the annotated value in tailwind.config.cjs match its tokens.css source (or update both).');
  process.exit(1);
}

console.log(`✓ Design tokens in sync (${checks.length} mirrored values checked against tokens.css).`);
