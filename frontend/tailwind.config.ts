import type { Config } from 'tailwindcss'
import animate from 'tailwindcss-animate'

/**
 * Every colour resolves to a CSS variable declared in src/styles/theme.css.
 * Components must never hardcode a hex value, add a token here instead.
 *
 * Brand source of truth (OptiStratixAI palette):
 *   butter-cream #F6DFA6 | soft-vanilla #FFF4D8 | ink-black  #171717
 *   warm-gray    #A89F94 | burnt-honey  #C9822B
 */
const config: Config = {
  darkMode: ['class', '[data-theme="dark"]'],
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    container: {
      center: true,
      padding: { DEFAULT: '1.25rem', lg: '2rem' },
      screens: { '2xl': '1320px' },
    },
    extend: {
      colors: {
        // --- raw brand tokens (use sparingly; prefer the semantic ones below) ---
        brand: {
          'butter-cream': 'hsl(var(--butter-cream) / <alpha-value>)',
          'soft-vanilla': 'hsl(var(--soft-vanilla) / <alpha-value>)',
          'ink-black': 'hsl(var(--ink-black) / <alpha-value>)',
          'warm-gray': 'hsl(var(--warm-gray) / <alpha-value>)',
          'burnt-honey': 'hsl(var(--burnt-honey) / <alpha-value>)',
        },
        // --- semantic tokens (theme-aware: these flip between light and dark) ---
        background: 'hsl(var(--background) / <alpha-value>)',
        foreground: 'hsl(var(--foreground) / <alpha-value>)',
        card: {
          DEFAULT: 'hsl(var(--card) / <alpha-value>)',
          foreground: 'hsl(var(--card-foreground) / <alpha-value>)',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover) / <alpha-value>)',
          foreground: 'hsl(var(--popover-foreground) / <alpha-value>)',
        },
        primary: {
          DEFAULT: 'hsl(var(--primary) / <alpha-value>)',
          foreground: 'hsl(var(--primary-foreground) / <alpha-value>)',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary) / <alpha-value>)',
          foreground: 'hsl(var(--secondary-foreground) / <alpha-value>)',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted) / <alpha-value>)',
          foreground: 'hsl(var(--muted-foreground) / <alpha-value>)',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent) / <alpha-value>)',
          foreground: 'hsl(var(--accent-foreground) / <alpha-value>)',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive) / <alpha-value>)',
          foreground: 'hsl(var(--destructive-foreground) / <alpha-value>)',
        },
        success: {
          DEFAULT: 'hsl(var(--success) / <alpha-value>)',
          foreground: 'hsl(var(--success-foreground) / <alpha-value>)',
        },
        warning: {
          DEFAULT: 'hsl(var(--warning) / <alpha-value>)',
          foreground: 'hsl(var(--warning-foreground) / <alpha-value>)',
        },
        border: 'hsl(var(--border) / <alpha-value>)',
        input: 'hsl(var(--input) / <alpha-value>)',
        ring: 'hsl(var(--ring) / <alpha-value>)',
        // --- 9-stage pipeline accents (deck colour coding, harmonised to the palette) ---
        stage: {
          1: 'hsl(var(--stage-1) / <alpha-value>)',
          2: 'hsl(var(--stage-2) / <alpha-value>)',
          3: 'hsl(var(--stage-3) / <alpha-value>)',
          4: 'hsl(var(--stage-4) / <alpha-value>)',
          5: 'hsl(var(--stage-5) / <alpha-value>)',
          6: 'hsl(var(--stage-6) / <alpha-value>)',
          7: 'hsl(var(--stage-7) / <alpha-value>)',
          8: 'hsl(var(--stage-8) / <alpha-value>)',
          9: 'hsl(var(--stage-9) / <alpha-value>)',
        },
      },
      fontFamily: {
        // Swappable: change the variable in theme.css, not these lines.
        display: ['var(--font-display)', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        sans: ['var(--font-body)', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['var(--font-mono)', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
      boxShadow: {
        glass: '0 8px 32px -8px hsl(var(--shadow-color) / 0.36)',
        'glass-lg': '0 24px 64px -16px hsl(var(--shadow-color) / 0.44)',
        glow: '0 0 0 1px hsl(var(--primary) / 0.28), 0 0 32px -4px hsl(var(--primary) / 0.34)',
      },
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' },
        },
        'pulse-ring': {
          '0%': { transform: 'scale(0.92)', opacity: '0.7' },
          '70%': { transform: 'scale(1.3)', opacity: '0' },
          '100%': { transform: 'scale(1.3)', opacity: '0' },
        },
        shimmer: {
          '100%': { transform: 'translateX(100%)' },
        },
        'awaiting-glow': {
          '0%, 100%': { opacity: '0.4' },
          '50%': { opacity: '1' },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
        'pulse-ring': 'pulse-ring 2.2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        shimmer: 'shimmer 1.8s infinite',
        'awaiting-glow': 'awaiting-glow 1.8s ease-in-out infinite',
      },
    },
  },
  plugins: [animate],
}

export default config
