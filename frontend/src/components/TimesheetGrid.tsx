import * as React from 'react';
import { PanelCard } from './PanelCard';
import type { TimesheetCell } from '@/lib/api';
import { formatSecondsWithMode } from '@/lib/format';
import { useHoursFormat } from '@/lib/HoursFormatContext';

export interface TimesheetGridProps {
  cells: TimesheetCell[];
  onCellClick: (cell: TimesheetCell) => void;
}

export function TimesheetGrid({ cells, onCellClick }: TimesheetGridProps) {
  const { format } = useHoursFormat();

  if (cells.length === 0) {
    return (
      <PanelCard>
        <p className="text-sm text-text-muted">No worklogs in this range.</p>
      </PanelCard>
    );
  }

  const periods = Array.from(new Set(cells.map((cell) => cell.period_start))).sort();

  const authors = Array.from(
    new Map(
      cells.map((cell) => [cell.author_account_id, cell.author_display_name]),
    ).entries(),
  ).sort((a, b) => a[1].localeCompare(b[1]));

  const cellByKey = new Map<string, TimesheetCell>();
  for (const cell of cells) {
    cellByKey.set(`${cell.author_account_id}|${cell.period_start}`, cell);
  }

  const periodTotals = new Map<string, number>();
  let grandTotal = 0;
  for (const cell of cells) {
    periodTotals.set(cell.period_start, (periodTotals.get(cell.period_start) ?? 0) + cell.total_seconds);
    grandTotal += cell.total_seconds;
  }

  return (
    <PanelCard>
      <div className="overflow-x-auto">
        <table className="w-full min-w-max text-left text-sm">
          <thead className="bg-surface-raised">
            <tr>
              <th className="border-b border-border px-3 py-2 font-medium text-text-muted">
                Author
              </th>
              {periods.map((period) => (
                <th
                  key={period}
                  className="border-b border-border px-3 py-2 font-medium text-text-muted"
                >
                  {period}
                </th>
              ))}
              <th className="border-b border-border px-3 py-2 font-medium text-text-muted">
                Total
              </th>
            </tr>
          </thead>
          <tbody>
            {authors.map(([accountId, displayName]) => {
              const rowTotal = periods.reduce(
                (sum, period) => sum + (cellByKey.get(`${accountId}|${period}`)?.total_seconds ?? 0),
                0,
              );
              return (
                <tr key={accountId} className="transition-colors hover:bg-surface-raised">
                  <td className="border-b border-border px-3 py-2 text-text-primary">
                    {displayName}
                  </td>
                  {periods.map((period) => {
                    const cell = cellByKey.get(`${accountId}|${period}`);
                    return (
                      <td key={period} className="border-b border-border px-3 py-2">
                        {cell ? (
                          <button
                            type="button"
                            onClick={() => onCellClick(cell)}
                            className="text-accent hover:underline"
                          >
                            {formatSecondsWithMode(cell.total_seconds, format)}
                          </button>
                        ) : (
                          <span className="text-text-muted">-</span>
                        )}
                      </td>
                    );
                  })}
                  <td className="border-b border-border px-3 py-2 font-medium text-text-primary">
                    {formatSecondsWithMode(rowTotal, format)}
                  </td>
                </tr>
              );
            })}
            <tr className="bg-surface-raised font-medium text-text-primary">
              <td className="px-3 py-2">Total</td>
              {periods.map((period) => (
                <td key={period} className="px-3 py-2">
                  {formatSecondsWithMode(periodTotals.get(period) ?? 0, format)}
                </td>
              ))}
              <td className="px-3 py-2">{formatSecondsWithMode(grandTotal, format)}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </PanelCard>
  );
}
