import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  getThisWeekRange,
  getPreviousWeekRange,
  getThisMonthRange,
  getPreviousMonthRange,
} from './dateRanges';

describe('dateRanges', () => {
  beforeEach(() => {
    // Wednesday, 2026-09-16
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 8, 16, 10, 0, 0));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('getThisWeekRange returns Monday through Sunday of the current week', () => {
    expect(getThisWeekRange()).toEqual({ from: '2026-09-14', to: '2026-09-20' });
  });

  it('getPreviousWeekRange returns the prior Monday through Sunday', () => {
    expect(getPreviousWeekRange()).toEqual({ from: '2026-09-07', to: '2026-09-13' });
  });

  it('getThisMonthRange returns the first through last day of the current month', () => {
    expect(getThisMonthRange()).toEqual({ from: '2026-09-01', to: '2026-09-30' });
  });

  it('getPreviousMonthRange returns the first through last day of the prior month', () => {
    expect(getPreviousMonthRange()).toEqual({ from: '2026-08-01', to: '2026-08-31' });
  });

  it('getThisWeekRange treats Sunday as the last day of the week, not the first', () => {
    vi.setSystemTime(new Date(2026, 8, 20, 10, 0, 0));
    expect(getThisWeekRange()).toEqual({ from: '2026-09-14', to: '2026-09-20' });
  });
});
