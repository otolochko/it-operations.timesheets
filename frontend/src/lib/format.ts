export function formatHours(seconds: number): string {
  return (seconds / 3600).toFixed(1);
}

export function formatDuration(seconds: number): string {
  const totalMinutes = Math.round(seconds / 60);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  if (hours === 0) return `${minutes}m`;
  if (minutes === 0) return `${hours}h`;
  return `${hours}h ${minutes}m`;
}

export function formatSecondsWithMode(
  seconds: number,
  mode: 'decimal' | 'duration',
): string {
  return mode === 'duration' ? formatDuration(seconds) : formatHours(seconds);
}
