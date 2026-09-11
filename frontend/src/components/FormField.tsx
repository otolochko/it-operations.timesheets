import * as React from 'react';

export interface FormFieldProps {
  label: string;
  children: React.ReactNode;
  error?: string;
  hint?: string;
}

export function FormField({ label, children, error, hint }: FormFieldProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-medium text-text-primary">{label}</label>
      {children}
      {error ? (
        <p className="text-sm text-danger">{error}</p>
      ) : hint ? (
        <p className="text-sm text-text-muted">{hint}</p>
      ) : null}
    </div>
  );
}
