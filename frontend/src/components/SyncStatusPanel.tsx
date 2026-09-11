'use client';

import * as React from 'react';
import { PanelCard } from '@/components/PanelCard';
import { PrimaryButton } from '@/components/Buttons';
import { StatusBadge } from '@/components/StatusBadge';
import { LogViewer } from '@/components/LogViewer';
import {
  getSyncStatus,
  triggerSync,
  type SyncRunSummary,
  type SyncStatusResponse,
} from '@/lib/api';

const POLL_INTERVAL_MS = 2000;

function formatTimestamp(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleString();
}

function badgeForStatus(status: SyncRunSummary['status']): 'info' | 'success' | 'danger' {
  if (status === 'success') return 'success';
  if (status === 'failed') return 'danger';
  return 'info';
}

export function SyncStatusPanel() {
  const [status, setStatus] = React.useState<SyncStatusResponse | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [triggering, setTriggering] = React.useState(false);

  const fetchStatus = React.useCallback(async () => {
    try {
      const result = await getSyncStatus();
      setStatus(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sync status.');
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  React.useEffect(() => {
    if (!status?.is_running) return;
    const interval = setInterval(() => {
      fetchStatus();
    }, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [status?.is_running, fetchStatus]);

  async function handleSyncNow() {
    setTriggering(true);
    try {
      await triggerSync();
      await fetchStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to trigger sync.');
    } finally {
      setTriggering(false);
    }
  }

  const isRunning = Boolean(status?.is_running);
  const latestRun = status?.latest_run ?? null;

  return (
    <PanelCard title="Sync status">
      {loading ? (
        <p className="text-sm text-text-muted">Loading...</p>
      ) : (
        <div className="flex flex-col gap-4">
          {error ? <p className="text-sm text-danger">{error}</p> : null}

          <div className="flex items-center gap-3">
            {latestRun ? (
              <StatusBadge status={badgeForStatus(latestRun.status)}>{latestRun.status}</StatusBadge>
            ) : (
              <StatusBadge status="info">Never synced</StatusBadge>
            )}
            <PrimaryButton onClick={handleSyncNow} disabled={isRunning || triggering}>
              {isRunning ? 'Sync in progress...' : 'Sync now'}
            </PrimaryButton>
          </div>

          {latestRun ? (
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm text-text-primary">
              <span className="text-text-muted">Started</span>
              <span>{formatTimestamp(latestRun.started_at)}</span>
              <span className="text-text-muted">Finished</span>
              <span>{formatTimestamp(latestRun.finished_at)}</span>
              <span className="text-text-muted">Worklogs upserted</span>
              <span>{latestRun.worklogs_upserted}</span>
              <span className="text-text-muted">Worklogs deleted</span>
              <span>{latestRun.worklogs_deleted}</span>
              {latestRun.status === 'failed' && latestRun.error ? (
                <>
                  <span className="text-text-muted">Error</span>
                  <span className="text-danger">{latestRun.error}</span>
                </>
              ) : null}
            </div>
          ) : (
            <p className="text-sm text-text-muted">No sync runs yet. Trigger one to get started.</p>
          )}

          <LogViewer logText={latestRun?.log_text} />
        </div>
      )}
    </PanelCard>
  );
}
