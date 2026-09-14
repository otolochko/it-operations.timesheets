'use client';

import * as React from 'react';
import { SyncStatusPanel } from '@/components/SyncStatusPanel';
import { SyncScheduleForm } from '@/components/SyncScheduleForm';
import { DisplaySettingsPanel } from '@/components/DisplaySettingsPanel';

export default function SyncSettingsPage() {
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6 p-4 md:p-8">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight text-text-primary">Sync settings</h1>
        <p className="mt-1 text-sm text-text-muted">
          Monitor Jira imports and manage the automatic sync schedule.
        </p>
      </header>
      <SyncStatusPanel />
      <SyncScheduleForm />
      <DisplaySettingsPanel />
    </div>
  );
}
