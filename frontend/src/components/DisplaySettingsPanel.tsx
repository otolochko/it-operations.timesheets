'use client';

import * as React from 'react';
import { PanelCard } from '@/components/PanelCard';
import { PrimaryButton, SecondaryButton } from '@/components/Buttons';
import { useHoursFormat, type HoursFormat } from '@/lib/HoursFormatContext';

const OPTIONS: { value: HoursFormat; label: string }[] = [
  { value: 'decimal', label: 'Decimal (6.3)' },
  { value: 'duration', label: 'Hours & minutes (6h 15m)' },
];

export function DisplaySettingsPanel() {
  const { format, setFormat } = useHoursFormat();

  return (
    <PanelCard title="Display settings">
      <div className="flex flex-col gap-2">
        <p className="text-sm text-text-muted">
          How hours are shown throughout the app (stored in this browser only).
        </p>
        <div className="flex gap-2">
          {OPTIONS.map((option) => {
            const ToggleButton = format === option.value ? PrimaryButton : SecondaryButton;
            return (
              <ToggleButton key={option.value} onClick={() => setFormat(option.value)}>
                {option.label}
              </ToggleButton>
            );
          })}
        </div>
      </div>
    </PanelCard>
  );
}
