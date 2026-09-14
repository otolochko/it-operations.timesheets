# Frontend Architecture

Directory layout, UI components, theming system, navigation, and API client integration for the Next.js frontend application.

## Directory Structure

All frontend source files reside in `frontend/src/`:

```
frontend/src/
├── app/
│   ├── globals.css                # CSS custom properties, theme tokens, fixed log palette
│   ├── layout.tsx                 # Root layout with DM Sans & IBM Plex Mono fonts and NavSidebar
│   ├── page.tsx                   # Timesheets dashboard page (filters, summary tiles, grid)
│   ├── page.test.tsx              # Unit tests for Timesheets page
│   └── sync/
│       └── page.tsx               # Sync, schedule, and display settings page
├── components/
│   ├── Buttons.tsx                # PrimaryButton, SecondaryButton, DangerButton
│   ├── DisplaySettingsPanel.tsx    # Browser-local hours display format controls
│   ├── FormField.tsx              # Form field container with label, hint, and error display
│   ├── IssueDrilldownPanel.tsx    # Modal panel displaying issue-level worklog breakdowns
│   ├── LogViewer.tsx              # Auto-following dark terminal panel using --log-* tokens
│   ├── LogViewer.test.tsx         # Unit test for latest-line auto-scroll
│   ├── NavSidebar.tsx             # Left sidebar with active link highlighting
│   ├── PanelCard.tsx              # Styled container card with optional title
│   ├── StatusBadge.tsx            # Pill status indicator badge ('info', 'success', 'danger')
│   ├── SyncScheduleForm.tsx       # Form for editing cron expression and project key filters
│   ├── SyncScheduleForm.test.tsx  # Unit tests for sync schedule form
│   ├── SyncStatusPanel.tsx        # Last-run status display, polling hook, and trigger button
│   ├── SyncStatusPanel.test.tsx   # Unit tests for sync status panel
│   ├── ThemeToggle.tsx            # Persisted light/dark theme switch in the sidebar
│   ├── ThemeToggle.test.tsx       # Unit tests for theme switching and persistence
│   └── TimesheetGrid.tsx          # Author x period hours table with interactive drilldown cells
└── lib/
    ├── api.ts                     # Typed fetch client for backend REST API endpoints
    ├── dateRanges.ts              # Calendar week and month range helpers
    ├── format.ts                  # Decimal and duration hours formatting helpers
    ├── HoursFormatContext.tsx     # Browser-local hours display preference
    ├── ThemeContext.tsx           # Theme state and DOM attribute synchronization
    ├── timesheetViewState.ts      # Persisted dashboard filters and URL synchronization
    └── theme/
        ├── constants.ts           # Shared local-storage key for pre-render theme setup
        └── tokens.ts              # JavaScript export of theme token CSS variables
```

## Theming and Design Tokens

The application uses an attribute-based theme system defined in `frontend/src/app/globals.css`.

### Main Application Tokens

Tokens are declared on `:root` and overridden under `:root[data-theme='dark']`. Tailwind CSS maps these variables to utility classes in `frontend/tailwind.config.ts` via `var(--token)`.

| Token | Light Value | Dark Value (`[data-theme='dark']`) | Utility Prefix |
|---|---|---|---|
| `--accent` | `#2563eb` | `#3b82f6` | `bg-accent`, `text-accent`, `border-accent` |
| `--accent-hover` | `#1d4ed8` | `#60a5fa` | `hover:bg-accent-hover` |
| `--success` | `#16a34a` | `#22c55e` | `text-success`, `bg-success` |
| `--danger` | `#dc2626` | `#f87171` | `text-danger`, `bg-danger` |
| `--warning` | `#d97706` | `#fbbf24` | `text-warning`, `bg-warning` |
| `--bg` | `#f8fafc` | `#0b1220` | `bg-bg` |
| `--card` | `#ffffff` | `#131c2e` | `bg-card` |
| `--field-bg` | `#ffffff` | `#0f1829` | `bg-field-bg` |
| `--border` | `#e2e8f0` | `#253045` | `border-border` |
| `--text-primary` | `#0f172a` | `#e2e8f0` | `text-text-primary` |
| `--text-muted` | `#64748b` | `#94a3b8` | `text-text-muted` |
| `--surface-raised` | `#f1f5f9` | `#182338` | `bg-surface-raised` |
| `--surface-overlay` | `#ffffff` | `#1a2540` | `bg-surface-overlay` |
| `--brand-2` | `#7c3aed` | `#a78bfa` | `text-brand-2` |
| `--sidebar` | `#ffffff` | `#0f1829` | `bg-sidebar` |
| `--sidebar-hover` | `#f1f5f9` | `#182338` | `bg-sidebar-hover` |
| `--accent-soft` | `#eff6ff` | `#172c4e` | `bg-accent-soft` |

`frontend/src/app/layout.tsx` resolves the stored theme before the first render, falling back
to the operating-system preference. `ThemeProvider` keeps `data-theme`, `color-scheme`, and
the `jira-timesheets-theme` browser storage value synchronized after a theme change.

### Fixed Log Viewer Tokens

The log viewer requires a fixed, always-dark terminal appearance. These tokens are declared on `:root` and do not shift across themes:

- `--log-bg`: `#0a0e14`
- `--log-text`: `#d1d5db`
- `--log-text-muted`: `#6b7280`
- `--log-border`: `#1f2937`
- `--log-accent`: `#22d3ee`

**Never** reuse `--log-*` tokens in other UI components. They are strictly confined to `globals.css`, `tailwind.config.ts`, `tokens.ts`, and `LogViewer.tsx`.

**Never** author raw hex or rgb color literals directly in `.tsx` files; all styles must use Tailwind classes linked to CSS custom properties.

## Component Library

| Component | Path | Responsibility |
|---|---|---|
| `PrimaryButton`, `SecondaryButton`, `DangerButton` | `frontend/src/components/Buttons.tsx` | Standardized button variants with loading/disabled styling. |
| `FormField` | `frontend/src/components/FormField.tsx` | Form input wrapper providing label, hint text, and error text. |
| `PanelCard` | `frontend/src/components/PanelCard.tsx` | White/dark card container with optional header title. |
| `StatusBadge` | `frontend/src/components/StatusBadge.tsx` | Pill status badge styled by `'info'`, `'success'`, or `'danger'`. |
| `NavSidebar` | `frontend/src/components/NavSidebar.tsx` | Left-hand navigation menu with active route detection. |
| `LogViewer` | `frontend/src/components/LogViewer.tsx` | Terminal log viewer that scrolls to the latest line whenever polling supplies new text. |
| `TimesheetGrid` | `frontend/src/components/TimesheetGrid.tsx` | Author x period hours table with interactive clickable cells. |
| `IssueDrilldownPanel` | `frontend/src/components/IssueDrilldownPanel.tsx` | Modal panel showing issue key, summary, hours, and worklog counts. |
| `SyncStatusPanel` | `frontend/src/components/SyncStatusPanel.tsx` | Status tile showing last run details, trigger button, and 2s poller. |
| `SyncScheduleForm` | `frontend/src/components/SyncScheduleForm.tsx` | Form for editing cron expressions and project keys with validation. |
| `ThemeToggle` | `frontend/src/components/ThemeToggle.tsx` | Accessible persisted light/dark theme switch. |

## Navigation Registration

Navigation items are defined in `frontend/src/components/NavSidebar.tsx`:

```typescript
const links = [
  { href: '/', label: 'Timesheets', icon: TimesheetIcon },
  { href: '/sync', label: 'Sync settings', icon: SyncIcon },
];
```

The active route is identified using Next.js `usePathname()` to apply a filled active state. The
sidebar is sticky and spans the viewport; it collapses to an icon rail below the `md` breakpoint.

## Dashboard State Persistence

`frontend/src/lib/timesheetViewState.ts` persists the date range, day/week grouping, and author
selection in `localStorage`. The same state is mirrored to the `from`, `to`, `group`, `authors`,
and repeated `author` URL parameters. URL values take precedence over browser storage so a copied
dashboard URL reproduces the same view; browser storage restores the view after navigating away
through a sidebar link that does not carry those parameters.

## API Client Integration

All backend communication passes through `frontend/src/lib/api.ts`:

- **Base URL**: Defaults to `process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'`.
- **Cache Policy**: All requests use `cache: 'no-store'` to guarantee fresh data.
- **Client Functions**:
  - `getTimesheetGrid(fromDate, toDate, group)`: Calls `GET /api/timesheets`.
  - `getExportUrl(fromDate, toDate, group, format, dataset?)`: Constructs download URL for `GET /api/timesheets/export` (triggered via `window.open()`).
  - `getIssueDrilldown(author, fromDate, toDate)`: Calls `GET /api/timesheets/issues`.
  - `getSyncStatus()`: Calls `GET /api/sync/status`.
  - `triggerSync()`: Calls `POST /api/sync/worklogs`.
  - `getSyncSchedule()`: Calls `GET /api/sync/schedule`.
  - `updateSyncSchedule(body)`: Calls `PUT /api/sync/schedule`.

## Test Configuration

Frontend tests run via Vitest (`npm run test`):

- **Environment**: `jsdom` via `@testing-library/react`.
- **JSX Transform**: `vitest.config.ts` configures `esbuild.jsx: 'automatic'` to support JSX elements in components like `LogViewer.tsx` that omit explicit React imports.
- **Path Aliases**: `@/` maps to `./src/`.

For feature workflows using these components, see [`features.md`](features.md).
