export type TimesheetGroup = 'day' | 'week';

export interface TimesheetViewState {
  fromDate: string;
  toDate: string;
  group: TimesheetGroup;
  selectedAuthorIds: string[] | null;
}

export const TIMESHEET_VIEW_STORAGE_KEY = 'jira-timesheets-view';

const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

function isDate(value: unknown): value is string {
  return typeof value === 'string' && DATE_PATTERN.test(value);
}

function isGroup(value: unknown): value is TimesheetGroup {
  return value === 'day' || value === 'week';
}

function parseStoredState(fallback: TimesheetViewState): TimesheetViewState {
  try {
    const rawState = window.localStorage.getItem(TIMESHEET_VIEW_STORAGE_KEY);
    if (!rawState) return fallback;

    const parsed = JSON.parse(rawState) as Partial<TimesheetViewState>;
    return {
      fromDate: isDate(parsed.fromDate) ? parsed.fromDate : fallback.fromDate,
      toDate: isDate(parsed.toDate) ? parsed.toDate : fallback.toDate,
      group: isGroup(parsed.group) ? parsed.group : fallback.group,
      selectedAuthorIds:
        parsed.selectedAuthorIds === null ||
        (Array.isArray(parsed.selectedAuthorIds) &&
          parsed.selectedAuthorIds.every((value) => typeof value === 'string'))
          ? parsed.selectedAuthorIds
          : fallback.selectedAuthorIds,
    };
  } catch {
    return fallback;
  }
}

export function loadTimesheetViewState(fallback: TimesheetViewState): TimesheetViewState {
  const storedState = parseStoredState(fallback);
  const params = new URLSearchParams(window.location.search);

  const fromDate = params.get('from');
  const toDate = params.get('to');
  const group = params.get('group');
  const authorsMode = params.get('authors');

  return {
    fromDate: isDate(fromDate) ? fromDate : storedState.fromDate,
    toDate: isDate(toDate) ? toDate : storedState.toDate,
    group: isGroup(group) ? group : storedState.group,
    selectedAuthorIds:
      authorsMode === 'all'
        ? null
        : authorsMode === 'custom'
          ? params.getAll('author')
          : storedState.selectedAuthorIds,
  };
}

export function saveTimesheetViewState(state: TimesheetViewState) {
  try {
    window.localStorage.setItem(TIMESHEET_VIEW_STORAGE_KEY, JSON.stringify(state));
  } catch {
    // URL persistence still works when browser storage is unavailable.
  }

  const params = new URLSearchParams(window.location.search);
  params.set('from', state.fromDate);
  params.set('to', state.toDate);
  params.set('group', state.group);
  params.set('authors', state.selectedAuthorIds === null ? 'all' : 'custom');
  params.delete('author');
  state.selectedAuthorIds?.forEach((accountId) => params.append('author', accountId));

  const query = params.toString();
  window.history.replaceState(
    window.history.state,
    '',
    `${window.location.pathname}${query ? `?${query}` : ''}${window.location.hash}`,
  );
}
