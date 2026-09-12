import * as React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { SyncScheduleForm } from './SyncScheduleForm';
import * as api from '@/lib/api';

vi.mock('@/lib/api', () => ({
  getSyncSchedule: vi.fn(),
  updateSyncSchedule: vi.fn(),
}));

const mockedApi = vi.mocked(api);

describe('SyncScheduleForm', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('pre-fills the form from getSyncSchedule and saves edited values', async () => {
    mockedApi.getSyncSchedule.mockResolvedValue({
      cron_expression: '0 * * * *',
      project_keys: ['ABC', 'DEF'],
      jql_filter: null,
      updated_at: '2026-09-01T00:00:00Z',
    });
    mockedApi.updateSyncSchedule.mockResolvedValue({
      cron_expression: '0 0 * * *',
      project_keys: ['ABC'],
      jql_filter: null,
      updated_at: '2026-09-11T00:00:00Z',
    });

    render(<SyncScheduleForm />);

    const cronInput = await screen.findByDisplayValue('0 * * * *');
    const keysInput = screen.getByDisplayValue('ABC, DEF');

    fireEvent.change(cronInput, { target: { value: '0 0 * * *' } });
    fireEvent.change(keysInput, { target: { value: 'ABC' } });

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /save schedule/i }));
    });

    expect(mockedApi.updateSyncSchedule).toHaveBeenCalledWith({
      cron_expression: '0 0 * * *',
      project_keys: ['ABC'],
      jql_filter: '',
    });

    await waitFor(() => expect(screen.getByText('Saved')).toBeInTheDocument());
  });

  it('disables project keys and saves jql_filter when a JQL filter is entered', async () => {
    mockedApi.getSyncSchedule.mockResolvedValue({
      cron_expression: '0 * * * *',
      project_keys: ['ABC'],
      jql_filter: null,
      updated_at: '2026-09-01T00:00:00Z',
    });
    mockedApi.updateSyncSchedule.mockResolvedValue({
      cron_expression: '0 * * * *',
      project_keys: ['ABC'],
      jql_filter: 'labels = keep',
      updated_at: '2026-09-11T00:00:00Z',
    });

    render(<SyncScheduleForm />);

    const keysInput = await screen.findByDisplayValue('ABC');
    const jqlInput = screen.getByLabelText(/jql filter/i);

    fireEvent.change(jqlInput, { target: { value: 'labels = keep' } });

    expect(keysInput).toBeDisabled();

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /save schedule/i }));
    });

    expect(mockedApi.updateSyncSchedule).toHaveBeenCalledWith({
      cron_expression: '0 * * * *',
      project_keys: ['ABC'],
      jql_filter: 'labels = keep',
    });
  });

  it('shows an inline error when updateSyncSchedule is rejected', async () => {
    mockedApi.getSyncSchedule.mockResolvedValue({
      cron_expression: '0 * * * *',
      project_keys: [],
      jql_filter: null,
      updated_at: '2026-09-01T00:00:00Z',
    });
    mockedApi.updateSyncSchedule.mockRejectedValue(
      new Error('Request to /api/sync/schedule failed with 400: {"detail": "Invalid cron expression"}'),
    );

    render(<SyncScheduleForm />);

    await screen.findByDisplayValue('0 * * * *');

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /save schedule/i }));
    });

    await waitFor(() =>
      expect(screen.getByText(/invalid cron expression/i)).toBeInTheDocument(),
    );
  });
});
