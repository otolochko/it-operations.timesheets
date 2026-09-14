import * as React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import TimesheetsPage from './page';
import * as api from '@/lib/api';
import type { TimesheetGridResponse, IssueDrilldownResponse } from '@/lib/api';
import { HoursFormatProvider } from '@/lib/HoursFormatContext';

function renderPage() {
  return render(
    <HoursFormatProvider>
      <TimesheetsPage />
    </HoursFormatProvider>,
  );
}

vi.mock('@/lib/api', () => ({
  getTimesheetGrid: vi.fn(),
  getIssueDrilldown: vi.fn(),
  getExportUrl: vi.fn(),
}));

const gridFixture: TimesheetGridResponse = {
  from_date: '2026-09-05',
  to_date: '2026-09-06',
  group: 'day',
  cells: [
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
  ],
  summary: {
    total_hours: 3.5,
    author_count: 2,
    issue_count: 3,
    average_hours_per_author: 1.75,
  },
};

const drilldownFixture: IssueDrilldownResponse = {
  author_account_id: 'acc-1',
  author_display_name: 'Alice',
  from_date: '2026-09-05',
  to_date: '2026-09-05',
  issues: [
    {
      issue_id: '101',
      issue_key: 'PROJ-1',
      issue_summary: 'Fix bug',
      total_seconds: 3600,
      worklog_count: 2,
    },
  ],
};

describe('TimesheetsPage', () => {
  beforeEach(() => {
    vi.mocked(api.getTimesheetGrid).mockReset();
    vi.mocked(api.getIssueDrilldown).mockReset();
    vi.mocked(api.getExportUrl).mockReset();
    vi.mocked(api.getTimesheetGrid).mockResolvedValue(gridFixture);
    vi.mocked(api.getIssueDrilldown).mockResolvedValue(drilldownFixture);
    vi.mocked(api.getExportUrl).mockReturnValue('http://api.test/export');
  });

  it('renders the grid with correct rows, columns, and hour values', async () => {
    renderPage();

    await screen.findByText('Alice');
    expect(screen.getByText('Bob')).toBeInTheDocument();
    expect(screen.getByText('2026-09-05')).toBeInTheDocument();
    expect(screen.getByText('2026-09-06')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '1.0' })).toBeInTheDocument(); // Alice 09-05
    expect(screen.getByRole('button', { name: '2.0' })).toBeInTheDocument(); // Alice 09-06
    expect(screen.getByRole('button', { name: '0.5' })).toBeInTheDocument(); // Bob 09-05
  });

  it('renders the "No worklogs" message for an empty cells array', async () => {
    vi.mocked(api.getTimesheetGrid).mockResolvedValue({
      ...gridFixture,
      cells: [],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('No worklogs in this range.')).toBeInTheDocument();
    });
  });

  it('renders summary metrics from the fixture response', async () => {
    renderPage();

    // Appears 3 times: Total hours card, Selected hours card, and the grid's grand total cell.
    await waitFor(() => {
      expect(screen.getAllByText('3.5')).toHaveLength(3);
    });
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('1.8')).toBeInTheDocument(); // average rounded to 1 decimal
  });

  it('opens the drill-down panel with correct data when a cell is clicked', async () => {
    renderPage();

    const aliceCell = await screen.findByText('1.0');
    fireEvent.click(aliceCell);

    await waitFor(() => {
      expect(api.getIssueDrilldown).toHaveBeenCalledWith('acc-1', '2026-09-05', '2026-09-05');
    });

    await screen.findByText('PROJ-1');
    expect(screen.getByText('Fix bug')).toBeInTheDocument();
  });

  it('Export Excel exports the current range and grouping', async () => {
    const open = vi.fn();
    vi.stubGlobal('open', open);

    renderPage();
    await screen.findByText('Alice');

    fireEvent.click(screen.getByRole('button', { name: 'Export Excel' }));

    expect(api.getExportUrl).toHaveBeenCalledWith(
      expect.any(String),
      expect.any(String),
      'day',
      'xlsx',
    );
    expect(open).toHaveBeenCalledWith('http://api.test/export');

    vi.unstubAllGlobals();
  });

  it('exports with the week grouping after the toggle is switched', async () => {
    const open = vi.fn();
    vi.stubGlobal('open', open);

    renderPage();
    await screen.findByText('Alice');

    fireEvent.click(screen.getByRole('button', { name: 'Week' }));
    fireEvent.click(screen.getByRole('button', { name: 'Export Excel' }));

    expect(api.getExportUrl).toHaveBeenLastCalledWith(
      expect.any(String),
      expect.any(String),
      'week',
      'xlsx',
    );

    vi.unstubAllGlobals();
  });

  it('shows an error message instead of crashing when the initial grid fetch fails', async () => {
    vi.mocked(api.getTimesheetGrid).mockReset();
    vi.mocked(api.getTimesheetGrid).mockRejectedValue(new Error('Network down'));

    renderPage();

    await screen.findByText('Network down');
    expect(screen.getByText('Error')).toBeInTheDocument();
  });

  it('calls getTimesheetGrid with the updated group when the day/week toggle is switched', async () => {
    renderPage();

    await waitFor(() => {
      expect(api.getTimesheetGrid).toHaveBeenCalled();
    });

    const weekButton = screen.getByRole('button', { name: 'Week' });
    fireEvent.click(weekButton);

    await waitFor(() => {
      const calls = vi.mocked(api.getTimesheetGrid).mock.calls;
      expect(calls.some((call) => call[2] === 'week')).toBe(true);
    });
  });
});
