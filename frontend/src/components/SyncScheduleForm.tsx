'use client';

import * as React from 'react';
import { PanelCard } from '@/components/PanelCard';
import { FormField } from '@/components/FormField';
import { PrimaryButton } from '@/components/Buttons';
import { StatusBadge } from '@/components/StatusBadge';
import { getSyncSchedule, updateSyncSchedule } from '@/lib/api';

function parseProjectKeys(value: string): string[] {
  return value
    .split(',')
    .map((key) => key.trim())
    .filter((key) => key.length > 0);
}

export function SyncScheduleForm() {
  const [cronExpression, setCronExpression] = React.useState('');
  const [projectKeysInput, setProjectKeysInput] = React.useState('');
  const [jqlFilterInput, setJqlFilterInput] = React.useState('');
  const [loading, setLoading] = React.useState(true);
  const [loadError, setLoadError] = React.useState<string | null>(null);
  const [saveError, setSaveError] = React.useState<string | null>(null);
  const [saved, setSaved] = React.useState(false);
  const [saving, setSaving] = React.useState(false);

  const jqlActive = jqlFilterInput.trim().length > 0;

  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const schedule = await getSyncSchedule();
        if (cancelled) return;
        setCronExpression(schedule.cron_expression);
        setProjectKeysInput(schedule.project_keys.join(', '));
        setJqlFilterInput(schedule.jql_filter ?? '');
      } catch (err) {
        if (cancelled) return;
        setLoadError(err instanceof Error ? err.message : 'Failed to load sync schedule.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSave() {
    setSaving(true);
    setSaveError(null);
    setSaved(false);
    try {
      const updated = await updateSyncSchedule({
        cron_expression: cronExpression,
        project_keys: parseProjectKeys(projectKeysInput),
        jql_filter: jqlFilterInput.trim(),
      });
      setCronExpression(updated.cron_expression);
      setProjectKeysInput(updated.project_keys.join(', '));
      setJqlFilterInput(updated.jql_filter ?? '');
      setSaved(true);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Failed to save sync schedule.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <PanelCard title="Sync schedule">
      {loading ? (
        <p className="text-sm text-text-muted">Loading...</p>
      ) : loadError ? (
        <p className="text-sm text-danger">{loadError}</p>
      ) : (
        <div className="flex flex-col gap-4">
          <FormField
            label="Cron expression"
            hint="Standard 5-field cron syntax, e.g. `0 * * * *` for hourly"
            error={saveError ?? undefined}
          >
            <input
              type="text"
              value={cronExpression}
              onChange={(e) => setCronExpression(e.target.value)}
              className="rounded-md border border-border bg-field-bg px-3 py-2 text-sm text-text-primary"
            />
          </FormField>

          <FormField
            label="Project keys"
            hint={
              jqlActive
                ? 'Ignored while a JQL filter is set below.'
                : 'Comma-separated Jira project keys'
            }
          >
            <input
              type="text"
              value={projectKeysInput}
              onChange={(e) => setProjectKeysInput(e.target.value)}
              disabled={jqlActive}
              className="rounded-md border border-border bg-field-bg px-3 py-2 text-sm text-text-primary disabled:opacity-50"
            />
          </FormField>

          <FormField
            label="JQL filter"
            hint="Optional JQL clause; when set, it replaces the project keys above entirely."
          >
            <textarea
              aria-label="JQL filter"
              rows={2}
              value={jqlFilterInput}
              onChange={(e) => setJqlFilterInput(e.target.value)}
              className="rounded-md border border-border bg-field-bg px-3 py-2 text-sm text-text-primary"
            />
          </FormField>

          <div className="flex items-center gap-3">
            <PrimaryButton onClick={handleSave} disabled={saving}>
              {saving ? 'Saving...' : 'Save schedule'}
            </PrimaryButton>
            {saved ? <StatusBadge status="success">Saved</StatusBadge> : null}
          </div>
        </div>
      )}
    </PanelCard>
  );
}
