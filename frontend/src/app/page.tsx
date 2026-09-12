'use client';

import * as React from 'react';
import { FormField } from '@/components/FormField';
import { PanelCard } from '@/components/PanelCard';
import { PrimaryButton, SecondaryButton } from '@/components/Buttons';
import { StatusBadge } from '@/components/StatusBadge';
import { TimesheetGrid } from '@/components/TimesheetGrid';
import { IssueDrilldownPanel } from '@/components/IssueDrilldownPanel';
import {
  getTimesheetGrid,
  getIssueDrilldown,
  getExportUrl,
  type TimesheetCell,
  type TimesheetGridResponse,
  type IssueDrilldownResponse,
} from '@/lib/api';

// Default date range: the last 7 days (inclusive), ending today.
function defaultDateRange(): { from: string; to: string } {
  const today = new Date();
  const from = new Date(today);
  from.setDate(from.getDate() - 6);
  const toIso = today.toISOString().slice(0, 10);
  const fromIso = from.toISOString().slice(0, 10);
  return { from: fromIso, to: toIso };
}

function addDaysIso(dateIso: string, days: number): string {
  const date = new Date(`${dateIso}T00:00:00`);
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
}

export default function TimesheetsPage() {
  const initialRange = React.useMemo(defaultDateRange, []);
  const [fromDate, setFromDate] = React.useState(initialRange.from);
  const [toDate, setToDate] = React.useState(initialRange.to);
  const [group, setGroup] = React.useState<'day' | 'week'>('day');

  const [grid, setGrid] = React.useState<TimesheetGridResponse | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const [drilldown, setDrilldown] = React.useState<IssueDrilldownResponse | null>(null);
  const [drilldownLoading, setDrilldownLoading] = React.useState(false);
  const [drilldownError, setDrilldownError] = React.useState<string | null>(null);
  const [drilldownOpen, setDrilldownOpen] = React.useState(false);

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getTimesheetGrid(fromDate, toDate, group)
      .then((response) => {
        if (!cancelled) setGrid(response);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load timesheet grid.');
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [fromDate, toDate, group]);

  function handleCellClick(cell: TimesheetCell) {
    const cellFrom = cell.period_start;
    const cellTo = group === 'week' ? addDaysIso(cell.period_start, 6) : cell.period_start;

    setDrilldownOpen(true);
    setDrilldownLoading(true);
    setDrilldownError(null);
    setDrilldown(null);

    getIssueDrilldown(cell.author_account_id, cellFrom, cellTo)
      .then((response) => setDrilldown(response))
      .catch((err: unknown) => {
        setDrilldownError(
          err instanceof Error ? err.message : 'Failed to load issue drill-down.',
        );
      })
      .finally(() => setDrilldownLoading(false));
  }

  const summary = grid?.summary;

  return (
    <div className="flex flex-col gap-6 p-6">
      <h1 className="text-xl font-semibold text-text-primary">Jira Timesheets</h1>

      <PanelCard>
        <div className="flex flex-wrap items-end gap-4">
          <FormField label="From">
            <input
              type="date"
              value={fromDate}
              onChange={(event) => setFromDate(event.target.value)}
              className="rounded-md border border-border bg-field-bg px-3 py-2 text-sm text-text-primary"
            />
          </FormField>
          <FormField label="To">
            <input
              type="date"
              value={toDate}
              onChange={(event) => setToDate(event.target.value)}
              className="rounded-md border border-border bg-field-bg px-3 py-2 text-sm text-text-primary"
            />
          </FormField>
          <div className="flex gap-2">
            {(['day', 'week'] as const).map((option) => {
              const ToggleButton = group === option ? PrimaryButton : SecondaryButton;
              return (
                <ToggleButton key={option} onClick={() => setGroup(option)}>
                  {option === 'day' ? 'Day' : 'Week'}
                </ToggleButton>
              );
            })}
          </div>
          <div className="flex gap-2">
            <SecondaryButton
              onClick={() => window.open(getExportUrl(fromDate, toDate, group, 'csv'))}
            >
              Export CSV
            </SecondaryButton>
            <SecondaryButton
              onClick={() => window.open(getExportUrl(fromDate, toDate, group, 'xlsx'))}
            >
              Export Excel
            </SecondaryButton>
          </div>
        </div>
      </PanelCard>

      {error ? (
        <PanelCard>
          <div className="flex flex-col gap-2">
            <StatusBadge status="danger">Error</StatusBadge>
            <p className="text-sm text-text-muted">{error}</p>
          </div>
        </PanelCard>
      ) : (
        <>
          {summary ? (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <PanelCard title="Total hours">
                <p className="text-2xl font-semibold text-text-primary">
                  {summary.total_hours.toFixed(1)}
                </p>
              </PanelCard>
              <PanelCard title="Authors">
                <p className="text-2xl font-semibold text-text-primary">
                  {summary.author_count}
                </p>
              </PanelCard>
              <PanelCard title="Issues">
                <p className="text-2xl font-semibold text-text-primary">
                  {summary.issue_count}
                </p>
              </PanelCard>
              <PanelCard title="Avg hours / author">
                <p className="text-2xl font-semibold text-text-primary">
                  {summary.average_hours_per_author.toFixed(1)}
                </p>
              </PanelCard>
            </div>
          ) : null}

          {loading ? (
            <p className="text-sm text-text-muted">Loading...</p>
          ) : (
            <TimesheetGrid cells={grid?.cells ?? []} onCellClick={handleCellClick} />
          )}
        </>
      )}

      {drilldownOpen ? (
        <IssueDrilldownPanel
          data={drilldown}
          loading={drilldownLoading}
          error={drilldownError}
          onClose={() => setDrilldownOpen(false)}
        />
      ) : null}
    </div>
  );
}
