import { describe, it, expect } from 'vitest';
import { formatDuration } from './format';

describe('formatDuration', () => {
  it('formats zero seconds as 0m', () => {
    expect(formatDuration(0)).toBe('0m');
  });

  it('formats exact hours without minutes', () => {
    expect(formatDuration(6 * 3600)).toBe('6h');
  });

  it('formats hours with minutes', () => {
    expect(formatDuration(6 * 3600 + 15 * 60)).toBe('6h 15m');
  });

  it('formats sub-hour durations as minutes only', () => {
    expect(formatDuration(45 * 60)).toBe('45m');
  });

  it('rounds to the nearest minute', () => {
    expect(formatDuration(6 * 3600 + 90)).toBe('6h 2m');
  });
});
