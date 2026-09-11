import * as React from 'react';

export interface PanelCardProps {
  children: React.ReactNode;
  title?: string;
  className?: string;
}

export function PanelCard({ children, title, className = '' }: PanelCardProps) {
  return (
    <div
      className={`rounded-lg border border-border bg-card p-4 shadow-sm ${className}`}
    >
      {title ? (
        <h2 className="mb-3 text-sm font-semibold text-text-primary">{title}</h2>
      ) : null}
      <div className="text-text-primary">{children}</div>
    </div>
  );
}
