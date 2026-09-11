import * as React from 'react';
import { PanelCard } from './PanelCard';
import { SecondaryButton } from './Buttons';
import { StatusBadge } from './StatusBadge';
import type { IssueDrilldownResponse } from '@/lib/api';
import { formatHours } from '@/lib/format';

export interface IssueDrilldownPanelProps {
  data: IssueDrilldownResponse | null;
  loading: boolean;
  error: string | null;
  onClose: () => void;
}

export function IssueDrilldownPanel({
  data,
  loading,
  error,
  onClose,
}: IssueDrilldownPanelProps) {
  return (
    <PanelCard title="Issue drill-down">
      <div className="flex flex-col gap-3">
        {loading ? (
          <p className="text-sm text-text-muted">Loading...</p>
        ) : error ? (
          <div className="flex flex-col gap-2">
            <StatusBadge status="danger">Error</StatusBadge>
            <p className="text-sm text-text-muted">{error}</p>
          </div>
        ) : data ? (
          <>
            <p className="text-sm text-text-muted">
              {data.author_display_name ?? data.author_account_id} &middot; {data.from_date}{' '}
              to {data.to_date}
            </p>
            {data.issues.length === 0 ? (
              <p className="text-sm text-text-muted">No issues found for this period.</p>
            ) : (
              <table className="w-full text-left text-sm">
                <thead>
                  <tr>
                    <th className="border-b border-border px-2 py-1 font-medium text-text-muted">
                      Issue
                    </th>
                    <th className="border-b border-border px-2 py-1 font-medium text-text-muted">
                      Summary
                    </th>
                    <th className="border-b border-border px-2 py-1 font-medium text-text-muted">
                      Hours
                    </th>
                    <th className="border-b border-border px-2 py-1 font-medium text-text-muted">
                      Worklogs
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {data.issues.map((issue) => (
                    <tr key={issue.issue_id}>
                      <td className="border-b border-border px-2 py-1 text-text-primary">
                        {issue.issue_key}
                      </td>
                      <td className="border-b border-border px-2 py-1 text-text-primary">
                        {issue.issue_summary}
                      </td>
                      <td className="border-b border-border px-2 py-1 text-text-primary">
                        {formatHours(issue.total_seconds)}
                      </td>
                      <td className="border-b border-border px-2 py-1 text-text-primary">
                        {issue.worklog_count}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </>
        ) : null}
        <div>
          <SecondaryButton onClick={onClose}>Close</SecondaryButton>
        </div>
      </div>
    </PanelCard>
  );
}
