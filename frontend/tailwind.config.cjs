/** @type {import('tailwindcss').Config} */
//
// Brand token values below are mirrored from the canonical source of truth at
// src/lib/styles/tokens.css. Keep them in sync — scripts/check-design-tokens.mjs
// fails CI if the brand colors / radii / shadows here drift from tokens.css.
// Colors are written as `oklch(... / <alpha-value>)` so Tailwind opacity
// modifiers (e.g. bg-primary-600/50) keep working.
module.exports = {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      // Semantic Color Tokens — brand palette is sky blue + green (see tokens.css)
      colors: {
        // Primary (brand / main actions) — sky blue.
        // 600 = --brand-primary, 700 = --brand-primary-mid, 50/100 ≈ --brand-primary-tint
        primary: {
          50: 'oklch(0.97 0.02 265 / <alpha-value>)',
          100: 'oklch(0.95 0.04 265 / <alpha-value>)', // --brand-primary-tint
          200: 'oklch(0.88 0.08 265 / <alpha-value>)',
          500: 'oklch(0.62 0.20 265 / <alpha-value>)',
          600: 'oklch(0.56 0.22 265 / <alpha-value>)', // --brand-primary
          700: 'oklch(0.48 0.23 265 / <alpha-value>)', // --brand-primary-mid
          900: 'oklch(0.37 0.15 265 / <alpha-value>)',
        },
        // Neutral (text, borders, backgrounds) — cool ink/surface scale.
        neutral: {
          50: 'oklch(0.99 0.004 240 / <alpha-value>)', // --surface
          100: 'oklch(0.96 0.006 240 / <alpha-value>)', // --surface-2
          200: 'oklch(0.90 0.006 240 / <alpha-value>)', // --ink-line
          300: 'oklch(0.88 0.006 240 / <alpha-value>)', // --ink-line-2
          600: 'oklch(0.50 0.010 240 / <alpha-value>)',
          700: 'oklch(0.37 0.012 240 / <alpha-value>)',
          800: 'oklch(0.27 0.014 240 / <alpha-value>)',
        },
        // Success (check-ins, confirmations) — brand green.
        // 600 = --brand-accent, 700 = --brand-accent-mid
        success: {
          50: 'oklch(0.97 0.03 145 / <alpha-value>)',
          600: 'oklch(0.60 0.17 145 / <alpha-value>)', // --brand-accent
          700: 'oklch(0.50 0.18 145 / <alpha-value>)', // --brand-accent-mid
        },
        // Danger (check-outs, errors, deletions) — red (outside the 2-color brand).
        danger: {
          50: '#fef2f2',
          200: '#fecaca',
          600: '#dc2626',
          700: '#b91c1c',
          800: '#991b1b',
        },
        // Warning (alerts, cautions) — orange.
        warning: {
          50: '#fff7ed',
          600: '#ea580c',
          700: '#c2410c',
        },
        // Info (informational content) — shares the primary blue.
        info: {
          50: 'oklch(0.97 0.02 265 / <alpha-value>)',
          500: 'oklch(0.62 0.20 265 / <alpha-value>)',
        },
      },
      // Typography Scale
      fontSize: {
        // Display sizes
        display: ['2.5rem', { lineHeight: '1.2', fontWeight: '700' }], // 40px
        // Heading sizes (already in Tailwind but documenting semantic usage)
        h1: ['2rem', { lineHeight: '1.3', fontWeight: '700' }], // 32px - PageHeader
        h2: ['1.5rem', { lineHeight: '1.4', fontWeight: '600' }], // 24px
        h3: ['1.25rem', { lineHeight: '1.4', fontWeight: '600' }], // 20px
        h4: ['1.125rem', { lineHeight: '1.5', fontWeight: '600' }], // 18px
        // Body text (use Tailwind defaults: base, sm, xs)
      },
      // Spacing (Tailwind defaults are good, documenting semantic usage)
      spacing: {
        section: '2rem', // 32px - between major sections
        element: '1rem', // 16px - between related elements
        compact: '0.5rem', // 8px - tight spacing
      },
      // Border Radius — brand scale (see tokens.css --radius-*)
      borderRadius: {
        button: '8px', // standard button radius (kit md button)
        input: '8px', // form inputs
        card: '14px', // --radius-md — cards and containers
        sm: '7px', // --radius-sm
        md: '14px', // --radius-md
        lg: '22px', // --radius-lg — feature cards, hero surfaces
        pill: '100px', // --radius-pill
      },
      // Box Shadows — cool ink-toned brand elevation (see tokens.css --shadow-*)
      boxShadow: {
        // elevation-* kept as aliases so existing usages don't break
        'elevation-1': '0 2px 8px oklch(0.14 0.015 240 / 0.07)', // --shadow-xs
        'elevation-2': '0 4px 16px oklch(0.14 0.015 240 / 0.08)', // --shadow-sm
        'elevation-3': '0 8px 28px oklch(0.14 0.015 240 / 0.14)', // --shadow-md
        'elevation-4': '0 16px 40px oklch(0.14 0.015 240 / 0.16)',
        'elevation-5': '0 40px 80px oklch(0.14 0.015 240 / 0.22), 0 12px 24px oklch(0.14 0.015 240 / 0.10)', // --shadow-lg
        // Brand-named shadows
        cta: '0 4px 16px oklch(0.52 0.20 232 / 0.30)', // --shadow-cta
      },
    },
  },
  plugins: [require('@tailwindcss/forms')],
};
