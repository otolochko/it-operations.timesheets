'use client';

import * as React from 'react';
import { SyncStatusPanel } from '@/components/SyncStatusPanel';
import { SyncScheduleForm } from '@/components/SyncScheduleForm';
import { DisplaySettingsPanel } from '@/components/DisplaySettingsPanel';

export default function SyncSettingsPage() {
  return (
    <div className="flex flex-col gap-6 p-6">
      <h1 className="text-lg font-semibold text-text-primary">Sync settings</h1>
      <SyncStatusPanel />
      <SyncScheduleForm />
      <DisplaySettingsPanel />
    </div>
  );
}
