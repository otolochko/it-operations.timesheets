import * as React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import TimesheetsPage from './page';
import * as api from '@/lib/api';
import type { TimesheetGridResponse, IssueDrilldownResponse } from '@/lib/api';

vi.mock('@/lib/api', () => ({
  getTimesheetGrid: vi.fn(),
  getIssueDrilldown: vi.fn(),
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
    vi.mocked(api.getTimesheetGrid).mockResolvedValue(gridFixture);
    vi.mocked(api.getIssueDrilldown).mockResolvedValue(drilldownFixture);
  });

  it('renders the grid with correct rows, columns, and hour values', async () => {
    render(<TimesheetsPage />);

    await screen.findByText('Alice');
    expect(screen.getByText('Bob')).toBeInTheDocument();
    expect(screen.getByText('2026-09-05')).toBeInTheDocument();
    expect(screen.getByText('2026-09-06')).toBeInTheDocument();
    expect(screen.getByText('1.0')).toBeInTheDocument(); // Alice 09-05
    expect(screen.getByText('2.0')).toBeInTheDocument(); // Alice 09-06
    expect(screen.getByText('0.5')).toBeInTheDocument(); // Bob 09-05
  });

  it('renders the "No worklogs" message for an empty cells array', async () => {
    vi.mocked(api.getTimesheetGrid).mockResolvedValue({
      ...gridFixture,
      cells: [],
    });

    render(<TimesheetsPage />);

    await waitFor(() => {
      expect(screen.getByText('No worklogs in this range.')).toBeInTheDocument();
    });
  });

  it('renders summary metrics from the fixture response', async () => {
    render(<TimesheetsPage />);

    await screen.findByText('3.5');
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('1.8')).toBeInTheDocument(); // average rounded to 1 decimal
  });

  it('opens the drill-down panel with correct data when a cell is clicked', async () => {
    render(<TimesheetsPage />);

    const aliceCell = await screen.findByText('1.0');
    fireEvent.click(aliceCell);

    await waitFor(() => {
      expect(api.getIssueDrilldown).toHaveBeenCalledWith('acc-1', '2026-09-05', '2026-09-05');
    });

    await screen.findByText('PROJ-1');
    expect(screen.getByText('Fix bug')).toBeInTheDocument();
  });

  it('calls getTimesheetGrid with the updated group when the day/week toggle is switched', async () => {
    render(<TimesheetsPage />);

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
