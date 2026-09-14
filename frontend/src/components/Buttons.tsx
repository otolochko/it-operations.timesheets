'use client';

import * as React from 'react';

type ButtonProps = React.ComponentPropsWithoutRef<'button'>;

export function PrimaryButton({ className = '', children, ...props }: ButtonProps) {
  return (
    <button
      className={`rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white shadow-accent transition-colors hover:bg-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-card disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function SecondaryButton({ className = '', children, ...props }: ButtonProps) {
  return (
    <button
      className={`rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium text-text-primary transition-colors hover:bg-surface-raised focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-card disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function SuccessButton({ className = '', children, ...props }: ButtonProps) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-lg bg-success-surface px-4 py-2 text-sm font-medium text-success-contrast transition-colors hover:bg-success-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success focus-visible:ring-offset-2 focus-visible:ring-offset-card disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function DangerButton({ className = '', children, ...props }: ButtonProps) {
  return (
    <button
      className={`rounded-lg bg-danger px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-danger focus-visible:ring-offset-2 focus-visible:ring-offset-card disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
