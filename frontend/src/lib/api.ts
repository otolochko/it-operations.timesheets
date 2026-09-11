const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

export interface TimesheetCell {
  author_account_id: string;
  author_display_name: string;
  period_start: string;
  total_seconds: number;
}

export interface TimesheetSummary {
  total_hours: number;
  author_count: number;
  issue_count: number;
  average_hours_per_author: number;
}

export interface TimesheetGridResponse {
  from_date: string;
  to_date: string;
  group: 'day' | 'week';
  cells: TimesheetCell[];
  summary: TimesheetSummary;
}

export interface IssueWorklogEntry {
  issue_id: string;
  issue_key: string;
  issue_summary: string;
  total_seconds: number;
  worklog_count: number;
}

export interface IssueDrilldownResponse {
  author_account_id: string;
  author_display_name: string | null;
  from_date: string;
  to_date: string;
  issues: IssueWorklogEntry[];
}

export interface SyncRunSummary {
  id: number;
  started_at: string;
  finished_at: string | null;
  status: string;
  worklogs_upserted: number;
  worklogs_deleted: number;
  error: string | null;
}

export interface SyncStatusResponse {
  latest_run: SyncRunSummary | null;
  is_running: boolean;
}

export interface SyncTriggerResponse {
  run_id: number;
  status: string;
}

export interface SyncScheduleResponse {
  cron_expression: string;
  project_keys: string[];
  updated_at: string;
}

export interface SyncScheduleUpdateRequest {
  cron_expression: string;
  project_keys?: string[];
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
    cache: 'no-store',
  });

  if (!response.ok) {
    const body = await response.text().catch(() => '');
    throw new Error(`Request to ${path} failed with ${response.status}: ${body}`);
  }

  return response.json() as Promise<T>;
}

export function getTimesheetGrid(
  fromDate: string,
  toDate: string,
  group: 'day' | 'week',
): Promise<TimesheetGridResponse> {
  const params = new URLSearchParams({ from: fromDate, to: toDate, group });
  return request<TimesheetGridResponse>(`/api/timesheets?${params.toString()}`);
}

export function getIssueDrilldown(
  author: string,
  fromDate: string,
  toDate: string,
): Promise<IssueDrilldownResponse> {
  const params = new URLSearchParams({ author, from: fromDate, to: toDate });
  return request<IssueDrilldownResponse>(`/api/timesheets/issues?${params.toString()}`);
}

export function getSyncStatus(): Promise<SyncStatusResponse> {
  return request<SyncStatusResponse>('/api/sync/status');
}

export function triggerSync(): Promise<SyncTriggerResponse> {
  return request<SyncTriggerResponse>('/api/sync/worklogs', { method: 'POST' });
}

export function getSyncSchedule(): Promise<SyncScheduleResponse> {
  return request<SyncScheduleResponse>('/api/sync/schedule');
}

export function updateSyncSchedule(
  body: SyncScheduleUpdateRequest,
): Promise<SyncScheduleResponse> {
  return request<SyncScheduleResponse>('/api/sync/schedule', {
    method: 'PUT',
    body: JSON.stringify(body),
  });
}
