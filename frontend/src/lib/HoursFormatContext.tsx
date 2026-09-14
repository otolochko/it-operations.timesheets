'use client';

import * as React from 'react';

export type HoursFormat = 'decimal' | 'duration';

const STORAGE_KEY = 'timesheets:hoursFormat';

interface HoursFormatContextValue {
  format: HoursFormat;
  setFormat: (format: HoursFormat) => void;
}

const HoursFormatContext = React.createContext<HoursFormatContextValue | null>(null);

export function HoursFormatProvider({ children }: { children: React.ReactNode }) {
  const [format, setFormatState] = React.useState<HoursFormat>('decimal');

  React.useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === 'decimal' || stored === 'duration') {
      setFormatState(stored);
    }
  }, []);

  const setFormat = React.useCallback((next: HoursFormat) => {
    setFormatState(next);
    window.localStorage.setItem(STORAGE_KEY, next);
  }, []);

  const value = React.useMemo(() => ({ format, setFormat }), [format, setFormat]);

  return <HoursFormatContext.Provider value={value}>{children}</HoursFormatContext.Provider>;
}

export function useHoursFormat(): HoursFormatContextValue {
  const context = React.useContext(HoursFormatContext);
  if (!context) {
    throw new Error('useHoursFormat must be used within a HoursFormatProvider');
  }
  return context;
}
