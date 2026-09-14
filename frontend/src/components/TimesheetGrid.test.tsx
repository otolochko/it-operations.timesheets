import * as React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { TimesheetGrid } from './TimesheetGrid';
import { HoursFormatProvider } from '@/lib/HoursFormatContext';
import type { TimesheetCell } from '@/lib/api';

const cells: TimesheetCell[] = [
  { author_account_id: 'acc-1', author_display_name: 'Alice', period_start: '2026-09-05', total_seconds: 3600 },
  { author_account_id: 'acc-1', author_display_name: 'Alice', period_start: '2026-09-06', total_seconds: 7200 },
  { author_account_id: 'acc-2', author_display_name: 'Bob', period_start: '2026-09-05', total_seconds: 1800 },
];

function renderGrid(subset: TimesheetCell[]) {
  return render(
    <HoursFormatProvider>
      <TimesheetGrid cells={subset} onCellClick={vi.fn()} />
    </HoursFormatProvider>,
  );
}

describe('TimesheetGrid subtotals', () => {
  it('renders a Total column per author row', () => {
    renderGrid(cells);
    expect(screen.getByText('3.0')).toBeInTheDocument(); // Alice row total: 1.0 + 2.0
    // Bob has a single period, so his cell value and row total are both 0.5.
    expect(screen.getAllByText('0.5')).toHaveLength(2);
  });

  it('renders a Total row per period column and a grand total', () => {
    renderGrid(cells);
    expect(screen.getByText('1.5')).toBeInTheDocument(); // 09-05 total: Alice 1.0 + Bob 0.5
    expect(screen.getAllByText('2.0').length).toBeGreaterThanOrEqual(2); // Alice 09-06 cell + 09-06 column total
    expect(screen.getByText('3.5')).toBeInTheDocument(); // grand total
  });

  it('recomputes subtotals when only a subset of authors is passed in', () => {
    renderGrid(cells.filter((cell) => cell.author_account_id === 'acc-1'));
    expect(screen.queryByText('Bob')).not.toBeInTheDocument();
    // Alice's row total and the grand total both equal 3.0 now that Bob is excluded.
    expect(screen.getAllByText('3.0')).toHaveLength(2);
  });
});
