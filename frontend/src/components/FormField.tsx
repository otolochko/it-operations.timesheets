import * as React from 'react';

export interface FormFieldProps {
  label: string;
  children: React.ReactNode;
  error?: string;
  hint?: string;
}

export function FormField({ label, children, error, hint }: FormFieldProps) {
  const generatedId = React.useId();
  const control = React.isValidElement<{ id?: string }>(children) ? children : null;
  const controlId = control?.props.id ?? generatedId;

  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={controlId} className="text-sm font-medium text-text-primary">
        {label}
      </label>
      {control ? React.cloneElement(control, { id: controlId }) : children}
      {error ? (
        <p className="text-sm text-danger">{error}</p>
      ) : hint ? (
        <p className="text-sm text-text-muted">{hint}</p>
      ) : null}
    </div>
  );
}
