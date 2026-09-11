import * as React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { SyncStatusPanel } from './SyncStatusPanel';
import * as api from '@/lib/api';

vi.mock('@/lib/api', () => ({
  getSyncStatus: vi.fn(),
  triggerSync: vi.fn(),
}));

const mockedApi = vi.mocked(api);

describe('SyncStatusPanel', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('shows a never-synced state when latest_run is null', async () => {
    mockedApi.getSyncStatus.mockResolvedValue({ latest_run: null, is_running: false });

    render(<SyncStatusPanel />);

    await waitFor(() => expect(screen.getByText('Never synced')).toBeInTheDocument());
    expect(screen.getByText(/no sync runs yet/i)).toBeInTheDocument();
  });

  it('shows badge and counts for a completed run', async () => {
    mockedApi.getSyncStatus.mockResolvedValue({
      latest_run: {
        id: 1,
        started_at: '2026-09-11T10:00:00Z',
        finished_at: '2026-09-11T10:05:00Z',
        status: 'success',
        worklogs_upserted: 42,
        worklogs_deleted: 3,
        error: null,
        log_text: null,
      },
      is_running: false,
    });

    render(<SyncStatusPanel />);

    await waitFor(() => expect(screen.getByText('success')).toBeInTheDocument());
    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('shows error message and danger badge for a failed run', async () => {
    mockedApi.getSyncStatus.mockResolvedValue({
      latest_run: {
        id: 2,
        started_at: '2026-09-11T10:00:00Z',
        finished_at: '2026-09-11T10:05:00Z',
        status: 'failed',
        worklogs_upserted: 0,
        worklogs_deleted: 0,
        error: 'Jira API timeout',
        log_text: 'Run failed: Jira API timeout',
      },
      is_running: false,
    });

    render(<SyncStatusPanel />);

    await waitFor(() => expect(screen.getByText('failed')).toBeInTheDocument());
    expect(screen.getByText('Jira API timeout')).toBeInTheDocument();
  });

  it('triggers sync, disables the button while running, and re-enables when polling shows completion', async () => {
    vi.useFakeTimers();

    mockedApi.getSyncStatus
      .mockResolvedValueOnce({ latest_run: null, is_running: false })
      .mockResolvedValueOnce({
        latest_run: {
          id: 3,
          started_at: '2026-09-11T10:00:00Z',
          finished_at: null,
          status: 'running',
          worklogs_upserted: 0,
          worklogs_deleted: 0,
          error: null,
          log_text: 'Sync started',
        },
        is_running: true,
      })
      .mockResolvedValueOnce({
        latest_run: {
          id: 3,
          started_at: '2026-09-11T10:00:00Z',
          finished_at: '2026-09-11T10:02:00Z',
          status: 'success',
          worklogs_upserted: 5,
          worklogs_deleted: 0,
          error: null,
          log_text: 'Sync completed successfully',
        },
        is_running: false,
      });
    mockedApi.triggerSync.mockResolvedValue({ run_id: 3, status: 'running' });

    await act(async () => {
      render(<SyncStatusPanel />);
    });

    expect(screen.getByText('Never synced')).toBeInTheDocument();

    const button = screen.getByRole('button', { name: /sync now/i });
    await act(async () => {
      fireEvent.click(button);
    });

    expect(mockedApi.triggerSync).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('button', { name: /sync in progress/i })).toBeDisabled();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });

    expect(screen.getByRole('button', { name: /sync now/i })).not.toBeDisabled();
    expect(mockedApi.getSyncStatus).toHaveBeenCalledTimes(3);
  });
});
