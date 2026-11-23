import type { ReactNode } from 'react';

export interface FieldProps {
  label: string;
  htmlFor?: string;
  description?: string;
  error?: string;
  rightSlot?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function Field({
  label,
  htmlFor,
  description,
  error,
  rightSlot,
  children,
  className = '',
}: FieldProps) {
  return (
    <div className={`space-y-1.5 ${className}`}>
      <div className="flex items-center justify-between gap-2">
        <label
          htmlFor={htmlFor}
          className="text-xs font-medium tracking-wide text-slate-200"
        >
          {label}
        </label>
        {rightSlot}
      </div>
      {children}
      {error ? (
        <p className="text-xs text-rose-400">{error}</p>
      ) : (
        description && <p className="text-xs text-slate-400">{description}</p>
      )}
    </div>
  );
}
