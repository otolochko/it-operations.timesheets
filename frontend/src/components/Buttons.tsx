'use client';

import * as React from 'react';

type ButtonProps = React.ComponentPropsWithoutRef<'button'>;

export function PrimaryButton({ className = '', children, ...props }: ButtonProps) {
  return (
    <button
      className={`rounded-md bg-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function SecondaryButton({ className = '', children, ...props }: ButtonProps) {
  return (
    <button
      className={`rounded-md border border-border bg-transparent px-4 py-2 text-sm font-medium text-text-primary transition-colors hover:bg-surface-raised disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function DangerButton({ className = '', children, ...props }: ButtonProps) {
  return (
    <button
      className={`rounded-md bg-danger px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
