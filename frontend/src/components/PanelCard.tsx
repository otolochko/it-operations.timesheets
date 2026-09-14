import * as React from 'react';

export interface PanelCardProps {
  children: React.ReactNode;
  title?: string;
  className?: string;
}

export function PanelCard({ children, title, className = '' }: PanelCardProps) {
  return (
    <div
      className={`rounded-xl border border-border bg-card p-4 shadow-card md:p-5 ${className}`}
    >
      {title ? (
        <h2 className="mb-4 text-sm font-semibold tracking-tight text-text-primary">{title}</h2>
      ) : null}
      <div className="text-text-primary">{children}</div>
    </div>
  );
}
