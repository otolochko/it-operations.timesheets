import * as React from 'react';

export interface StatusBadgeProps {
  status: 'info' | 'success' | 'danger';
  children: React.ReactNode;
}

const statusClasses: Record<StatusBadgeProps['status'], string> = {
  info: 'bg-surface-raised text-accent border-accent',
  success: 'bg-surface-raised text-success border-success',
  danger: 'bg-surface-raised text-danger border-danger',
};

export function StatusBadge({ status, children }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${statusClasses[status]}`}
    >
      {children}
    </span>
  );
}
