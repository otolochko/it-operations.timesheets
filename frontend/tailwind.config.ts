import type { Config } from 'tailwindcss';

// Design tokens are stored as full CSS color values (not RGB triplets) in
// globals.css, so we reference them here via `var(--token)` directly rather
// than the `rgb(var(--token) / <alpha-value>)` pattern. This is simpler to
// author and read, at the cost of Tailwind's opacity modifiers (e.g. `bg-accent/50`)
// not working — this app doesn't need per-utility opacity on tokens, so the
// tradeoff is acceptable.
const config: Config = {
  darkMode: ['selector', '[data-theme="dark"]'],
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        accent: 'var(--accent)',
        'accent-hover': 'var(--accent-hover)',
        success: 'var(--success)',
        danger: 'var(--danger)',
        warning: 'var(--warning)',
        bg: 'var(--bg)',
        card: 'var(--card)',
        'field-bg': 'var(--field-bg)',
        border: 'var(--border)',
        'text-primary': 'var(--text-primary)',
        'text-muted': 'var(--text-muted)',
        'surface-raised': 'var(--surface-raised)',
        'surface-overlay': 'var(--surface-overlay)',
        'brand-2': 'var(--brand-2)',
        sidebar: 'var(--sidebar)',
        'sidebar-hover': 'var(--sidebar-hover)',
        'accent-soft': 'var(--accent-soft)',
        // Fixed, always-dark terminal palette used only by the log viewer.
        'log-bg': 'var(--log-bg)',
        'log-text': 'var(--log-text)',
        'log-text-muted': 'var(--log-text-muted)',
        'log-border': 'var(--log-border)',
        'log-accent': 'var(--log-accent)',
      },
      fontFamily: {
        sans: ['var(--font-sans)'],
        mono: ['var(--font-mono)'],
      },
      boxShadow: {
        card: 'var(--shadow-card)',
        accent: 'var(--shadow-accent)',
      },
    },
  },
  plugins: [],
};

export default config;
