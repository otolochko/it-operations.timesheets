// Mirrors the CSS custom properties defined in `src/app/globals.css`, for
// any JS-side use (e.g. handing a color to a charting library).

export const tokens = {
  accent: 'var(--accent)',
  accentHover: 'var(--accent-hover)',
  success: 'var(--success)',
  successSurface: 'var(--success-surface)',
  successSurfaceHover: 'var(--success-surface-hover)',
  successContrast: 'var(--success-contrast)',
  danger: 'var(--danger)',
  warning: 'var(--warning)',
  bg: 'var(--bg)',
  card: 'var(--card)',
  fieldBg: 'var(--field-bg)',
  border: 'var(--border)',
  textPrimary: 'var(--text-primary)',
  textMuted: 'var(--text-muted)',
  surfaceRaised: 'var(--surface-raised)',
  surfaceOverlay: 'var(--surface-overlay)',
  brand2: 'var(--brand-2)',
  sidebar: 'var(--sidebar)',
  sidebarHover: 'var(--sidebar-hover)',
  accentSoft: 'var(--accent-soft)',
  chart1: 'var(--chart-1)',
  chart2: 'var(--chart-2)',
  chart3: 'var(--chart-3)',
  chart4: 'var(--chart-4)',
  chart5: 'var(--chart-5)',
  chart6: 'var(--chart-6)',
  chartOther: 'var(--chart-other)',
} as const;

// Fixed, always-dark terminal palette used ONLY by the LogViewer component.
// Keep separate from `tokens` — never mix into the main app palette.
export const logTokens = {
  logBg: 'var(--log-bg)',
  logText: 'var(--log-text)',
  logTextMuted: 'var(--log-text-muted)',
  logBorder: 'var(--log-border)',
  logAccent: 'var(--log-accent)',
} as const;
