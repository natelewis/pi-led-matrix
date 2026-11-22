import type { HTMLAttributes, ReactNode } from 'react';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  elevated?: boolean;
}

export function Card({ elevated = false, className = '', children, ...rest }: CardProps) {
  return (
    <div
      className={`rounded-2xl border border-slate-800/90 ${
        elevated ? 'bg-surface-850 shadow-xl shadow-black/30' : 'bg-surface-900/90'
      } ${className}`}
      {...rest}
    >
      {children}
    </div>
  );
}

export interface CardHeaderProps {
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
}

export function CardHeader({
  title,
  description,
  action,
  className = '',
}: CardHeaderProps) {
  return (
    <div
      className={`flex flex-wrap items-start justify-between gap-3 border-b border-slate-800/80 px-5 py-4 ${className}`}
    >
      <div className="min-w-0">
        <h3 className="text-sm font-semibold tracking-tight text-slate-100">{title}</h3>
        {description && <p className="mt-0.5 text-xs text-slate-400">{description}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

export function CardContent({
  className = '',
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return <div className={`p-5 ${className}`}>{children}</div>;
}

export function CardFooter({
  className = '',
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <div
      className={`flex items-center justify-end gap-2 border-t border-slate-800/80 px-5 py-3.5 ${className}`}
    >
      {children}
    </div>
  );
}
