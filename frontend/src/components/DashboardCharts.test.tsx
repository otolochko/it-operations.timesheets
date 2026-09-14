import * as React from 'react';
import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { DashboardCharts } from '@/components/DashboardCharts';
import { HoursFormatProvider } from '@/lib/HoursFormatContext';
import type { TimesheetCell } from '@/lib/api';

const cells: TimesheetCell[] = [
  {
    author_account_id: 'acc-1',
    author_display_name: 'Alice',
    period_start: '2026-09-05',
    total_seconds: 3600,
  },
  {
    author_account_id: 'acc-1',
    author_display_name: 'Alice',
    period_start: '2026-09-06',
    total_seconds: 7200,
  },
  {
    author_account_id: 'acc-2',
    author_display_name: 'Bob',
    period_start: '2026-09-05',
    total_seconds: 1800,
  },
];

function renderCharts(chartCells = cells) {
  return render(
    <HoursFormatProvider>
      <DashboardCharts cells={chartCells} />
    </HoursFormatProvider>,
  );
}

describe('DashboardCharts', () => {
  it('renders a stacked trend and author ranking from timesheet cells', () => {
    renderCharts();

    expect(screen.getByText('Logged time trend')).toBeInTheDocument();
    expect(
      screen.getByRole('img', { name: 'Logged time by period and author' }),
    ).toBeInTheDocument();
    expect(screen.getByText('Hours by author')).toBeInTheDocument();
    expect(screen.getByRole('meter', { name: 'Alice: 3.0' })).toBeInTheDocument();
    expect(screen.getByRole('meter', { name: 'Bob: 0.5' })).toBeInTheDocument();
  });

  it('groups lower-ranked authors into Others in the stacked chart', () => {
    const manyAuthors = Array.from({ length: 7 }, (_, index) => ({
      author_account_id: `acc-${index}`,
      author_display_name: `Author ${index}`,
      period_start: '2026-09-05',
      total_seconds: (8 - index) * 3600,
    }));

    renderCharts(manyAuthors);

    expect(screen.getByText('Others (1)')).toBeInTheDocument();
  });
});
