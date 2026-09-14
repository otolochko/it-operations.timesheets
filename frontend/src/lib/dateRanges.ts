// Quick date-range presets. Weeks start on Monday (ISO week), matching the
// backend's date_trunc('week', ...) aggregation.

function toIso(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function startOfWeek(date: Date): Date {
  const result = new Date(date);
  const day = result.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  result.setDate(result.getDate() + diff);
  return result;
}

export function getThisWeekRange(): { from: string; to: string } {
  const from = startOfWeek(new Date());
  const to = new Date(from);
  to.setDate(to.getDate() + 6);
  return { from: toIso(from), to: toIso(to) };
}

export function getPreviousWeekRange(): { from: string; to: string } {
  const thisWeekFrom = startOfWeek(new Date());
  const from = new Date(thisWeekFrom);
  from.setDate(from.getDate() - 7);
  const to = new Date(from);
  to.setDate(to.getDate() + 6);
  return { from: toIso(from), to: toIso(to) };
}

export function getThisMonthRange(): { from: string; to: string } {
  const now = new Date();
  const from = new Date(now.getFullYear(), now.getMonth(), 1);
  const to = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  return { from: toIso(from), to: toIso(to) };
}

export function getPreviousMonthRange(): { from: string; to: string } {
  const now = new Date();
  const from = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  const to = new Date(now.getFullYear(), now.getMonth(), 0);
  return { from: toIso(from), to: toIso(to) };
}
