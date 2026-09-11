import * as React from 'react';
import { PanelCard } from './PanelCard';
import type { TimesheetCell } from '@/lib/api';
import { formatHours } from '@/lib/format';

export interface TimesheetGridProps {
  cells: TimesheetCell[];
  onCellClick: (cell: TimesheetCell) => void;
}

export function TimesheetGrid({ cells, onCellClick }: TimesheetGridProps) {
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

  return (
    <PanelCard>
      <div className="overflow-x-auto">
        <table className="w-full min-w-max text-left text-sm">
          <thead>
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
            </tr>
          </thead>
          <tbody>
            {authors.map(([accountId, displayName]) => (
              <tr key={accountId}>
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
                          {formatHours(cell.total_seconds)}
                        </button>
                      ) : (
                        <span className="text-text-muted">-</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </PanelCard>
  );
}
