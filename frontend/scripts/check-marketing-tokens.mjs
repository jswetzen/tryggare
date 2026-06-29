#!/usr/bin/env node
/**
 * Marketing-token drift guard.
 *
 * The brand token layer lives in two places that must stay identical:
 *   - frontend/src/lib/styles/tokens.css   (canonical :root custom properties — app)
 *   - colors_and_type.css                  (the copy the marketing site links, at
 *                                            the ROOT of the gh-pages branch)
 *
 * The two files differ only in header/inline comments, so a raw checksum would
 * give false failures. This guard instead parses the `--name: value;`
 * declarations out of both files (no require → runs without node_modules) and
 * fails if any token is missing from either side or has a drifting value.
 *
 * The marketing file lives on gh-pages, not on the branch under test, so it is
 * supplied one of two ways:
 *   - explicit path as argv[2] (used in CI:
 *       git show origin/gh-pages:colors_and_type.css > /tmp/marketing-tokens.css)
 *   - otherwise auto-fetched via `git show origin/gh-pages:colors_and_type.css`
 *     so a developer can run it locally with no arguments.
 *
 * Run: node frontend/scripts/check-marketing-tokens.mjs [path-to-marketing.css]
 *      (npm run check:marketing-tokens, from the frontend/ dir)
 */
import { readFileSync } from 'node:fs';
import { execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const canonicalPath = resolve(here, '../src/lib/styles/tokens.css');

// Load the canonical app tokens.
let canonicalSrc;
try {
  canonicalSrc = readFileSync(canonicalPath, 'utf8');
} catch (err) {
  console.error(`check-marketing-tokens: cannot read canonical tokens at ${canonicalPath}: ${err.message}`);
  process.exit(1);
}

// Load the marketing tokens: explicit path argument, else `git show` from
// gh-pages so a local run needs no arguments.
const marketingArg = process.argv[2];
let marketingSrc;
let marketingSource;
if (marketingArg) {
  marketingSource = marketingArg;
  try {
    marketingSrc = readFileSync(marketingArg, 'utf8');
  } catch (err) {
    console.error(`check-marketing-tokens: cannot read marketing tokens at ${marketingArg}: ${err.message}`);
    process.exit(1);
  }
} else {
  marketingSource = 'origin/gh-pages:colors_and_type.css';
  try {
    marketingSrc = execSync('git show origin/gh-pages:colors_and_type.css', { encoding: 'utf8' });
  } catch (err) {
    console.error('check-marketing-tokens: no marketing file argument given and could not read it from git.');
    console.error('  Tried: git show origin/gh-pages:colors_and_type.css');
    console.error(`  Error: ${err.message}`);
    console.error('  Pass a path as the first argument, or run `git fetch origin gh-pages --depth=1` first.');
    process.exit(1);
  }
}

// Normalise whitespace before comparing. These files carry no `<alpha-value>`
// placeholder, so (unlike check-design-tokens.mjs) there is nothing to strip.
const norm = (s) => s.replace(/\s+/g, ' ').trim();

// Build a map of --token -> value. `[^;]` also spans newlines, so multi-line
// shadow values are captured whole.
const parse = (src) => {
  const map = new Map();
  for (const m of src.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) {
    map.set(m[1], norm(m[2]));
  }
  return map;
};

const canonical = parse(canonicalSrc);
const marketing = parse(marketingSrc);

// Guard against a silent no-op (e.g. a path that points at the wrong file).
if (canonical.size === 0) {
  console.error(`check-marketing-tokens: parsed 0 declarations from canonical ${canonicalPath} — guard would be a no-op.`);
  process.exit(1);
}
if (marketing.size === 0) {
  console.error(`check-marketing-tokens: parsed 0 declarations from marketing ${marketingSource} — guard would be a no-op.`);
  process.exit(1);
}

const failures = [];

// Every canonical token must exist in marketing with an equal value.
for (const [token, expected] of canonical) {
  if (!marketing.has(token)) {
    failures.push(`  ${token}: in canonical tokens.css but missing from marketing ${marketingSource}`);
    continue;
  }
  const actual = marketing.get(token);
  if (actual !== expected) {
    failures.push(`  ${token}:\n      tokens.css (canonical) = ${expected}\n      marketing             = ${actual}`);
  }
}

// And every marketing token must exist in canonical (catches extras/drift the
// other direction).
for (const token of marketing.keys()) {
  if (!canonical.has(token)) {
    failures.push(`  ${token}: in marketing ${marketingSource} but missing from canonical tokens.css`);
  }
}

if (failures.length > 0) {
  console.error(`✗ Marketing tokens out of sync with canonical tokens.css:\n${failures.join('\n')}`);
  console.error('\nFix: update colors_and_type.css on gh-pages (or tokens.css) so the declarations match.');
  process.exit(1);
}

console.log(`✓ Marketing tokens match canonical (${canonical.size} declarations).`);
