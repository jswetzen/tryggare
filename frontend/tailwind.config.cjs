/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  theme: {
    extend: {
      // Semantic Color Tokens
      colors: {
        // Primary colors (brand/main actions) - mapped from blue
        primary: {
          50: '#eff6ff',   // blue-50
          100: '#dbeafe',  // blue-100
          200: '#bfdbfe',  // blue-200
          500: '#3b82f6',  // blue-500
          600: '#2563eb',  // blue-600
          700: '#1d4ed8',  // blue-700
          900: '#1e3a8a',  // blue-900
        },
        // Neutral colors (text, borders, backgrounds) - mapped from slate/gray
        neutral: {
          50: '#f8fafc',   // slate-50
          100: '#f1f5f9',  // slate-100
          200: '#e2e8f0',  // slate-200
          300: '#cbd5e1',  // slate-300
          600: '#475569',  // slate-600
          700: '#334155',  // slate-700
          800: '#1e293b',  // slate-800
        },
        // Success colors (check-ins, confirmations) - mapped from green
        success: {
          50: '#f0fdf4',   // green-50
          600: '#16a34a',  // green-600
          700: '#15803d',  // green-700
        },
        // Danger colors (check-outs, errors, deletions) - mapped from red
        danger: {
          50: '#fef2f2',   // red-50
          200: '#fecaca',  // red-200
          600: '#dc2626',  // red-600
          700: '#b91c1c',  // red-700
          800: '#991b1b',  // red-800
        },
        // Warning colors (alerts, cautions) - mapped from orange
        warning: {
          50: '#fff7ed',   // orange-50
          600: '#ea580c',  // orange-600
          700: '#c2410c',  // orange-700
        },
        // Info colors (informational content) - lighter blue
        info: {
          50: '#eff6ff',   // blue-50
          500: '#3b82f6',  // blue-500
        },
      },
      // Typography Scale
      fontSize: {
        // Display sizes
        'display': ['2.5rem', { lineHeight: '1.2', fontWeight: '700' }],  // 40px
        // Heading sizes (already in Tailwind but documenting semantic usage)
        'h1': ['2rem', { lineHeight: '1.3', fontWeight: '700' }],          // 32px - PageHeader
        'h2': ['1.5rem', { lineHeight: '1.4', fontWeight: '600' }],        // 24px
        'h3': ['1.25rem', { lineHeight: '1.4', fontWeight: '600' }],       // 20px
        'h4': ['1.125rem', { lineHeight: '1.5', fontWeight: '600' }],      // 18px
        // Body text (use Tailwind defaults: base, sm, xs)
      },
      // Spacing (Tailwind defaults are good, documenting semantic usage)
      spacing: {
        'section': '2rem',      // 32px - between major sections
        'element': '1rem',      // 16px - between related elements
        'compact': '0.5rem',    // 8px - tight spacing
      },
      // Border Radius
      borderRadius: {
        'button': '0.375rem',   // 6px - standard button radius
        'card': '0.5rem',       // 8px - cards and containers
        'input': '0.375rem',    // 6px - form inputs
      },
      // Box Shadows (elevation system)
      boxShadow: {
        'elevation-1': '0 1px 2px 0 rgb(0 0 0 / 0.05)',                    // Subtle - cards
        'elevation-2': '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',  // Default - elevated cards
        'elevation-3': '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',  // Medium - dropdowns
        'elevation-4': '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',  // High - modals
        'elevation-5': '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',  // Highest - important modals
      },
    }
  },
  plugins: [require('@tailwindcss/forms')]
};
